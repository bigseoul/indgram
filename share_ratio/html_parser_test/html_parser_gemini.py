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
    model_name = "models/gemini-2.5-flash"
    model = genai.GenerativeModel(model_name)

    prompt = f"""
너는 기업 지분 구조 및 타법인 출자 현황 분석 전문가다.
주어진 데이터에서 오직 '자본(Equity) 관계'인 지분 보유 현황만을 추출한다.
회계 기준 해석이나 재무적 판단은 하지 않는다.

[필수 추출 및 제외 규칙]
1. 포함 대상: '주식'을 소유하고 있으며 '지분율(%)'이 명확히 제시된 관계만 추출한다.
2. 제외 대상: 대출, 대여금, 미수금, 사채(CB/BW 등), 담보 제공 등 '채권(Debt)' 관계는 절대 포함하지 않는다.
3. 행 제외 규칙: 데이터 표에 포함된 '합계', '소계', 'Total' 행은 데이터로 추출하지 않는다.
4. 기준 시점: '전기' 또는 '비교' 정보는 무시하고, '당기(당기말)' 기준 정보만 추출한다.
5. 수치 해석 및 형식:
   - 우선주 또는 종류주식이 별도로 존재하더라도, 본 추출에서는 보통주 기준 지분율만 사용한다.
   - 지분율이 '전부', '100%', '전량'으로 표기된 경우 100.0으로 기재한다.
   - 모든 ownership_ratio는 float 형식의 숫자로 기재하며, 따옴표("")를 사용하지 않는다.
6. 지분율 숫자가 명확히 제시되지 않은 항목은 제외한다.
7. 최대주주는 제공된 데이터에 포함된 주주 전원을 의미한다.
8. 제공된 증거 데이터 범위를 벗어난 정보는 절대 추가하지 않는다.
9. 회사명(corp_name)은 증거 데이터에 명시적으로 등장한 회사명만 사용하며 추정하지 않는다.
10. 기준일(as_of_date)이 증거 데이터에 명시되지 않은 경우 null로 기재한다.

[증거 데이터]
{context_data}

반드시 아래 JSON 스키마를 따르는 JSON 형식으로만 응답하라.
설명, 해석, 서술 문장은 절대 포함하지 말 것.

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
    source_file = Path(__file__).resolve().parent / "sample" / "sample.html"

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

        json_output = result.model_dump_json(indent=2, ensure_ascii=False)
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
