import os
import sys
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from html_extractor_v4 import extract_evidence_blocks
from pydantic import BaseModel, ConfigDict, Field

load_dotenv()

MODEL_NAME = "gpt-5-mini-2025-08-07"
SAMPLE = "투믹스홀딩스.html"

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY not found in .env file.")
    sys.exit(1)


def _post_chat_completion(prompt: str) -> str:
    model = MODEL_NAME
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 1.0,
        "response_format": {"type": "json_object"},
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    if response.status_code != 200:
        print(f"OpenAI API error: {response.status_code} {response.text}")
        response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]["content"]


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
    prompt = f"""
기업 지분 분석 전문가로서 [Context] 내의 모든 데이터 블록([DATA-GENERAL-HTML], [DATA-TABLE-HTML])을 샅샅이 분석하여 지분 구조를 JSON으로 추출하라. 

[Core Rules]
1. 전수 조사(Exhaustive Search):
   - 문서 내 모든 지분율(%) 데이터를 분석하여 누락 없이 추출하라.
   - 채권(대출, 담보, CB/BW 등) 관계는 절대 제외.
2. 섹션 기반 분류 (Section-based Classification):
   - [Section: ...] 정보를 활용하여 데이터의 성격을 판별하라.
   - '회사의 개요', '일반사항' 섹션(또는 이와 유사한 도입부 섹션)에 초입에 등장하는 지분은 본 회사의 주주인 'major_shareholders'로 분류하라.
   - 그 외의 섹션(투자, 증권 등)은 섹션 제목뿐만 아니라 표의 헤더(예: 피투자회사, 발행회사 vs 주주명)와 문맥을 분석하여 주주인지 투자처(investments)인지 신중히 판별하라.
3. 의미 중심 매칭 (Semantic Mapping):
   - colspan/rowspan을 고려하여 '당기(말)' 지분율을 추출하라. 
   - 컬럼 순서나 명칭이 다르더라도 문맥을 해석하여 '기업명/성명'과 '지분율'을 정확히 매칭할 것.
   - 동일 Entity 중복 등장 시 '당기말' 보통주 지분율 하나만 남김.
4. 명칭 정제(Normalization):
   - 반드시 제거: '(주)', '(주 )', '주식회사', '(유)', '(유한)', '유한회사', '(재)', '재단법인' 등 모든 국문 법인격 기호.
   - 반드시 제거: '(*1)', '(주1)', '*1', '주1' 등 모든 형태의 주석 번호 및 기호.
   - 예: "㈜기업명(*1)" -> "기업명", "사명 주식회사" -> "사명"
5. 수치 형식: 지분율은 float(숫자)로 기재. (단위 % 생략)

[Context]
{context_data}

[Output Format]
JSON only. No additional text.
{{
  "major_shareholders": [{{ "nm": "str", "trmend_posesn_stock_qota_rt": float }}],
  "investments": [{{ "inv_prm": "str", "trmend_blce_qota_rt": float }}]
}}"""

    try:
        text = _post_chat_completion(prompt)
        if not text:
            print("Error: Received empty response from OpenAI", flush=True)
            return None

        # 디버깅을 위해 원본 응답 출력
        print(f"\n[DEBUG] Raw LLM Response:\n{text}\n", flush=True)

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        return CorporateStructure.model_validate_json(text)
    except Exception as e:
        print(f"LLM 처리 중 오류 발생: {e}", flush=True)
        raise


def main():
    source_file = Path(__file__).resolve().parent / "sample" / SAMPLE

    if not source_file.exists():
        print(f"Error: {source_file} 파일을 찾을 수 없습니다.")
        return

    print(f"Reading file: {source_file}", flush=True)
    html_content = source_file.read_text(encoding="utf-8")

    print("Extracting evidence blocks from HTML...", flush=True)
    soup = BeautifulSoup(html_content, "html.parser")
    context_data = extract_evidence_blocks(soup)
    print(f"Extracted context length: {len(context_data)} chars", flush=True)

    if not context_data.strip():
        print("관련된 정보를 찾지 못했습니다.")
        return

    print("Sending to LLM for structured analysis...", flush=True)
    try:
        result = extract_share_ratio_with_llm(context_data)

        json_output = result.model_dump_json(
            indent=2, ensure_ascii=False, by_alias=True
        )
        print("\n--- Final Structured Result ---", flush=True)
        print(json_output, flush=True)

        # 파일 저장
        output_file = source_file.parent / "result_gpt.json"
        output_file.write_text(json_output, encoding="utf-8")
        print(f"\n[INFO] Result saved to: {output_file}", flush=True)

    except Exception as e:
        print(f"Main loop error: {e}", flush=True)


if __name__ == "__main__":
    main()
