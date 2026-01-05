import os
import sys
from pathlib import Path
from typing import List

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai

# 분리된 추출 모듈 임포트
from html_extractor_v6 import extract_evidence_blocks
from pydantic import BaseModel, ConfigDict, Field

# .env 파일 로드
load_dotenv()

MODEL_NAME = "gemini-2.5-flash-lite"
SAMPLE = "인스파이어인티그레이티드리조트.html"


# Gemini API 설정
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GOOGLE_API_KEY or GEMINI_API_KEY not found in .env file.")
    sys.exit(1)

client = genai.Client(api_key=api_key)


class ShareholderItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    shareholder: str = Field(alias="nm", description="주주명 또는 주체명")
    ownership_ratio: float = Field(
        alias="trmend_posesn_stock_qota_rt", description="지분율 (단위: %)"
    )


class InvestmentItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    investee: str = Field(alias="inv_prm", description="피투자회사명")
    ownership_ratio: float = Field(
        alias="trmend_blce_qota_rt", description="지분율 (단위: %)"
    )


class CorporateStructure(BaseModel):
    major_shareholders: List[ShareholderItem] = Field(
        description="최대주주 및 주요 주주 현황"
    )
    investments: List[InvestmentItem] = Field(description="타법인 출자 현황")


def extract_share_ratio_with_llm(context_data: str) -> CorporateStructure:
    """Gemini를 사용하여 추출된 증거 데이터에서 지분 구조를 분석함"""
    system_instruction = """기업 지분 분석 전문가로서 제공된 [Context]를 분석하여 지분 구조를 JSON으로 추출하라. 

[Compresion Mapping] (Token Reduction)
- Tags: <t>=table, <r>=tr, <d>=td, <h>=th, <v>=div, <s>=span, <p>=p
- Attributes: c=colspan, r=rowspan
- Markers: [TBL]=Table block, [TXT]=Text block, [S: ...]=Section title, [C]=Preceding Context, [T]=Main Table
- Meta: [META] C=Company, U=Unit, D=Date

[Core Rules]
1. 전수 조사(Exhaustive Search):
   - 문서 내 모든 지분율(%) 데이터를 분석하여 누락 없이 추출하라.
   - 채권(대출, 담보, CB/BW 등) 관계는 절대 제외.
2. 섹션 기반 분류 (Section-based Classification):
   - [S: ...] 정보를 활용하여 데이터의 성격을 판별하라.
   - '회사의 개요', '일반사항' 섹션(또는 이와 유사한 도입부 섹션)에 초입에 등장하는 지분은 본 회사의 주주인 'major_shareholders'로 분류하라.
   - 그 외의 섹션(투자, 증권 등)은 섹션 제목뿐만 아니라 표의 헤더(예: 피투자회사, 발행회사 vs 주주명)와 문맥을 분석하여 주주인지 투자처(investments)인지 신중히 판별하라.
3. 의미 중심 매칭 (Semantic Mapping):
   - c(colspan)/r(rowspan)을 고려하여 '당기(말)' 지분율을 추출하라. 
   - 컬럼 순서나 명칭이 다르더라도 문맥을 해석하여 '기업명/성명'과 '지분율'을 정확히 매칭할 것.
   - 동일 Entity 중복 등장 시 '당기말' 보통주 지분율 하나만 남김.
4. 명칭 정제(Normalization):
   - 반드시 제거: '(주)', '(주 )', '주식회사', '(유)', '(유한)', '유한회사', '(재)', '재단법인' 등 모든 국문 법인격 기호.
   - 반드시 제거: '(*1)', '(주1)', '*1', '주1' 등 모든 형태의 주석 번호 및 기호.
   - 원문 유지(Exact Extraction): 주주명 및 기업명은 [Context] 본문에 기재된 원문 그대로를 추출하되, 자의적인 생략이나 수정을 금지함.
   - 단일 항목 유지(No Splitting): '대표이사와 그 특수관계인'과 같이 본문에 하나의 주체로 묶여서 설명된 경우, 절대 여러 항목으로 분리하지 말 것.
   - 조사 제거(No Particles): 성명/사명 뒤에 붙는 조사('은/는/이/가', '의' 등)는 반드시 제거하고 명사형태만 추출하라. 
5. 수치 형식: 지분율은 float(숫자)로 기재. (단위 % 생략)"""

    user_prompt = f"[Context]\n{context_data}"

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_prompt,
            config={
                "system_instruction": system_instruction,
                "response_mime_type": "application/json",
                "response_schema": CorporateStructure,
            },
        )

        if not response or not response.text:
            print("Error: Received empty response from Gemini", flush=True)
            return None

        # response_schema를 사용하므로 직접 파싱 가능
        return CorporateStructure.model_validate_json(response.text)
    except Exception as e:
        print(f"LLM 처리 중 오류 발생: {e}", flush=True)
        raise


def main():
    # 파일 경로 설정
    source_file = Path(__file__).resolve().parent / "sample" / SAMPLE

    if not source_file.exists():
        print(f"Error: {source_file} 파일을 찾을 수 없습니다.")
        return

    print(f"Reading file: {source_file}", flush=True)
    html_content = source_file.read_text(encoding="utf-8")

    # 1. 실제 데이터 추출 모듈 사용
    print("Extracting evidence blocks from HTML...", flush=True)
    soup = BeautifulSoup(html_content, "html.parser")
    context_data = extract_evidence_blocks(soup)
    print(f"Extracted context length: {len(context_data)} chars", flush=True)

    if not context_data.strip():
        print("관련된 정보를 찾지 못했습니다.")
        return

    # 2. LLM 처리
    print("Sending to LLM for structured analysis...", flush=True)
    try:
        result = extract_share_ratio_with_llm(context_data)

        json_output = result.model_dump_json(
            indent=2, ensure_ascii=False, by_alias=True
        )
        print("\n--- Final Structured Result ---", flush=True)
        print(json_output, flush=True)

        # 파일 저장
        output_file = source_file.parent / "result_gemini.json"
        output_file.write_text(json_output, encoding="utf-8")
        print(f"\n[INFO] Result saved to: {output_file}", flush=True)

    except Exception as e:
        print(f"Main loop error: {e}", flush=True)


if __name__ == "__main__":
    main()
