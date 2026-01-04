import os
import sys
from pathlib import Path
from typing import List

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google import genai

# 분리된 추출 모듈 임포트
from html_extractor_v4 import extract_evidence_blocks
from pydantic import BaseModel, ConfigDict, Field

# .env 파일 로드
load_dotenv()

MODEL_NAME = "gemini-2.0-flash-lite"
SAMPLE = "투믹스홀딩스.html"


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
    model_name = MODEL_NAME

    prompt = f"""
기업 지분 분석 전문가로서 [Context] 내의 모든 데이터 블록([DATA-GENERAL-HTML], [DATA-TABLE-HTML])을 샅샅이 분석하여 지분 구조를 JSON으로 추출하라. 

[Core Rules]
1. 전수 조사(Exhaustive Search):
   - 문서 내 '일반사항', '종속기업 현황', '관계기업 현황', '지분법적용투자', '매도가능자산' 등 지분율(%)이 명시된 모든 테이블과 텍스트를 분석하여 단 하나의 기업도 누락하지 마라.
   - 채권(대출, 담보, CB/BW 등) 관계는 절대 제외.
2. 의미 중심 매칭 (Semantic Mapping):
   - colspan/rowspan을 고려하여 '당기(말)' 지분율을 추출하라. 
   - 컬럼 순서나 명칭이 다르더라도 문맥을 해석하여 '기업명/성명'과 '지분율'을 정확히 매칭할 것.
   - 동일 Entity 중복 등장 시 '당기말' 보통주 지분율 하나만 남김.
3. 명칭 정제(Normalization):
   - 반드시 제거: '(주)', '(주 )', '주식회사', '(유)', '(유한)', '유한회사', '(재)', '재단법인' 등 모든 국문 법인격 기호.
   - 반드시 제거: '(*1)', '(주1)', '*1', '주1' 등 모든 형태의 주석 번호 및 기호.
   - 예: "㈜기업명(*1)" -> "기업명", "사명 주식회사" -> "사명"
4. 수치 형식: 지분율은 float(숫자)로 기재.

[Context]
{context_data}

[Output Format]
JSON only. No additional text.
{{
  "major_shareholders": [{{ "nm": "str", "trmend_posesn_stock_qota_rt": float }}],
  "investments": [{{ "inv_prm": "str", "trmend_blce_qota_rt": float }}]
}}"""

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )

        if not response or not response.text:
            print("Error: Received empty response from Gemini", flush=True)
            return None

        text = response.text
        # JSON 문자열 추출 (Markdown fence 대응)
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        return CorporateStructure.model_validate_json(text)
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
