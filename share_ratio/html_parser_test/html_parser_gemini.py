import os
import sys
from pathlib import Path
from typing import List, Optional

import google.generativeai as genai
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 분리된 추출 모듈 임포트
from html_extractor import extract_evidence_blocks
from pydantic import BaseModel, Field

# .env 파일 로드
load_dotenv()

# Gemini API 설정
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GOOGLE_API_KEY or GEMINI_API_KEY not found in .env file.")
    sys.exit(1)

genai.configure(api_key=api_key)


class ShareholderItem(BaseModel):
    shareholder: str = Field(description="주주명 또는 주체명")
    ownership_ratio: float = Field(description="지분율 (단위: %)")


class InvestmentItem(BaseModel):
    investee: str = Field(description="피투자회사명")
    ownership_ratio: float = Field(description="지분율 (단위: %)")


class CorporateStructure(BaseModel):
    corp_name: str = Field(description="대상 회사명")
    as_of_date: Optional[str] = Field(None, description="기준일 (YYYY-MM-DD)")
    major_shareholders: List[ShareholderItem] = Field(
        description="최대주주 및 주요 주주 현황"
    )
    investments: List[InvestmentItem] = Field(description="타법인 출자 현황")


def extract_share_ratio_with_llm(context_data: str) -> CorporateStructure:
    """Gemini를 사용하여 추출된 증거 데이터에서 지분 구조를 분석함"""
    # model_name = "models/gemini-3-flash-preview"
    model_name = "models/gemini-2.5-flash-lite"
    model = genai.GenerativeModel(model_name)

    prompt = f"""
너는 기업 지분 구조를 분석하는 전문가다.
회계 처리나 재무 기준 해석은 하지 않는다.
주어진 데이터에 포함된 지분율 관계만을 기반으로
지배 구조를 명확하고 간결하게 요약한다.
추측이나 외부 정보는 사용하지 않는다.
전기말 또는 비교 정보는 포함되어 있지 않다. 
당기 또는 당기말 기준으로 정보를 추출한다.

[증거 데이터]
{context_data}

위 데이터를 기반으로 다음을 수행하라.

1. 해당 회사의 최대주주와 지분율을 명확히 정리하라.
2. 해당 회사가 지분을 보유한 회사들과 각 지분율을 나열하라.

주의사항:
- 지분율 숫자를 반드시 포함할 것
- 회계 용어 사용 금지
- 추정이나 가능성 표현 금지
- 제공된 데이터 범위를 벗어나지 말 것
- 지분율이 '전부', '100%', '전량' 등으로 표현된 경우 100.0으로 해석할 것

반드시 아래 JSON 스키마를 따르는 JSON 형식으로만 응답하세요:
{{
  "corp_name": "대상 회사명",
  "as_of_date": "YYYY-MM-DD 또는 null",
  "major_shareholders": [
    {{
      "shareholder": "주주명",
      "ownership_ratio": float,
    }}
  ],
  "investments": [
    {{
      "investee": "피투자회사명",
      "ownership_ratio": float
    }}
  ]
}}
"""

    try:
        response = model.generate_content(prompt)

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
    source_file = Path(__file__).resolve().parent / "kpartners.html"

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
        print("\n--- Final Structured Result ---", flush=True)
        print(result.model_dump_json(indent=2, ensure_ascii=False), flush=True)
    except Exception as e:
        print(f"Main loop error: {e}", flush=True)


if __name__ == "__main__":
    main()
