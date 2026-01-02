import os
import sys
from pathlib import Path
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from html_extractor import extract_evidence_blocks
from pydantic import BaseModel, Field

load_dotenv()

MODEL_NAME = "gpt-4o-mini"

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
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    if response.status_code != 200:
        print(f"OpenAI API error: {response.status_code} {response.text}")
        response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]["content"]


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
      "ownership_ratio": float
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
        text = _post_chat_completion(prompt)
        if not text:
            print("Error: Received empty response from OpenAI", flush=True)
            return None

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        return CorporateStructure.model_validate_json(text)
    except Exception as e:
        print(f"LLM 처리 중 오류 발생: {e}", flush=True)
        raise


def main():
    source_file = Path(__file__).resolve().parent / "kpartners.html"

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
        print("\n--- Final Structured Result ---", flush=True)
        print(result.model_dump_json(indent=2, ensure_ascii=False), flush=True)
    except Exception as e:
        print(f"Main loop error: {e}", flush=True)


if __name__ == "__main__":
    main()
