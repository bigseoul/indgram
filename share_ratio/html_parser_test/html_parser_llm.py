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


class ShareholderInfo(BaseModel):
    name: str = Field(description="주주명 또는 주체명")
    share_ratio: float = Field(
        description="지분율 (단위: %, 100%인 경우 100.0으로 표기)"
    )
    description: Optional[str] = Field(
        None, description="추가 설명 (예: 특수관계자 포함 여부 등)"
    )


class CorporateOverview(BaseModel):
    company_name: str = Field(description="회사명")
    foundation_date: Optional[str] = Field(None, description="설립일")
    major_shareholders: List[ShareholderInfo] = Field(
        description="주요 주주 및 지분율 정보"
    )


def extract_share_ratio_with_llm(context_data: str) -> CorporateOverview:
    """Gemini를 사용하여 추출된 증거 데이터에서 지분율 정보를 구조화함"""
    # 2026년 가용 모델인 gemini-3-flash-preview 사용
    model_name = "models/gemini-3-flash-preview"
    print(f"Using model: {model_name}", flush=True)
    model = genai.GenerativeModel(model_name)

    prompt = f"""
    당신은 기업 공시 분석 전문가입니다. 아래 제공된 [증거 데이터]를 분석하여 회사명, 설립일, 주요 주주의 지분율 정보를 추출하십시오.

    [주의 사항]
    - 지분율이 '전부', '100%', '전량' 등으로 표현된 경우 100.0으로 해석하십시오.
    - 보통주와 우선주가 나뉘어 있다면 합산하지 말고 '보통주' 기준으로 우선 추출하십시오.

    [증거 데이터]
    {context_data}

    반드시 아래 JSON 스키마를 따르는 JSON 형식으로만 응답하세요:
    {{
        "company_name": "회사명",
        "foundation_date": "YYYY-MM-DD 또는 null",
        "major_shareholders": [
            {{
                "name": "주주명",
                "share_ratio": float (단위: %),
                "description": "추가 맥락 및 메모 또는 null"
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

        return CorporateOverview.model_validate_json(text)
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
