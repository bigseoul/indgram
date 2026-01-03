import os
import sys
from pathlib import Path
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from html_extractor import extract_evidence_blocks
from pydantic import BaseModel, ConfigDict, Field

load_dotenv()

MODEL_NAME = "gpt-4o"

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
    corp_name: Optional[str] = Field(None, description="대상 회사명")
    as_of_date: Optional[str] = Field(None, description="기준일 (YYYY-MM-DD)")
    major_shareholders: List[ShareholderItem] = Field(
        description="최대주주 및 주요 주주 현황"
    )
    investments: List[InvestmentItem] = Field(description="타법인 출자 현황")


def extract_share_ratio_with_llm(context_data: str) -> CorporateStructure:
    prompt = f"""
너는 기업 지분 구조 및 타법인 출자 현황 분석 전문가다.
주어진 데이터에서 오직 '자본(Equity) 관계'인 지분 보유 현황만을 추출한다.
회계 기준 해석이나 재무적 판단은 하지 않는다.

[필수 추출 및 제외 규칙]
1. 포함 대상: '주식'을 소유하고 있으며 '지분율(%)'이 명확히 제시된 모든 관계를 추출한다. 데이터의 여러 섹션(지분법적용투자주식, 매도가능금융자산, 기타비유동금융자산 등)에 흩어져 있을 수 있으니 빠짐없이 찾아야 한다.
2. 제외 대상: 대출, 대여금, 미수금, 사채(CB/BW 등), 담보 제공 등 '채권(Debt)' 관계는 절대 포함하지 않는다.
3. 행 제외 규칙: 데이터 표에 포함된 '합계', '소계', 'Total', '기타' 행은 데이터로 추출하지 않는다.
4. 기준 시점: '전기' 또는 '비교' 정보는 무시하고, 오직 '당기(당기말)' 기준 정보만 추출한다.
5. 수치 해석 및 형식:
   - 우선주 또는 종류주식이 별도로 존재하더라도, 본 추출에서는 보통주 기준 지분율만 사용한다.
   - 지분율이 '전부', '100%', '전량'으로 표기된 경우 100.0으로 기재한다.
   - 모든 ownership_ratio는 float 형식의 숫자로 기재하며, 따옴표("")를 사용하지 않는다.
6. 지분율 숫자가 명확히 제시되지 않은 항목은 제외한다.
7. 최대주주는 제공된 데이터에 포함된 주주 전원을 의미한다.
8. 제공된 증거 데이터 범위를 벗어난 정보는 절대 추가하지 않는다.
9. 회사명(corp_name)은 증거 데이터에 명시적으로 등장한 회사명만 사용하며 추정하지 않는다.
10. 기준일(as_of_date)이 증거 데이터에 명시되지 않은 경우 null로 기재한다.
11. 명칭 정제(Normalization):
    - 반드시 제거할 것: '(주)', '(주 )', '주식회사', '(유)', '유한회사', '(재)', '재단법인', '(*1)', '(주1)', '*1', '주1' 등 모든 형태의 한국어 기업 형태 기호와 주석 번호.
    - 예시: "(주)지엔코" -> "지엔코", "주식회사 큐로홀딩스" -> "큐로홀딩스", "필리에라(*1)" -> "필리에라", " (주) 크레오에스지" -> "크레오에스지"
    - 유지할 것: English corporate suffixes like 'Co.', 'Inc.', 'Ltd.'.
    - 가공 규칙: 외국어 명칭 내 쉼표(,) 뒤에 공백이 없는 경우 공백을 하나 추가한다(예: "Inferrex,Ltd." -> "Inferrex, Ltd."). 원문에 기재된 문자, 기호 등을 임의로 수정하거나 삭제하지 말고 원문의 의미를 최대한 유지한다.
12. 중복 제거 및 단일화: 동일한 주주(nm) 또는 피투자회사(inv_prm)가 데이터 내 여러 번 등장하는 경우, 중복하여 리스트에 넣지 않는다. 특히 '당기말'과 '전기말' 정보가 모두 제공된 경우, 반드시 '당기말' 지분율 하나만 남긴다. 만약 동일 회사에 대해 지분율이 미세하게 다른 항목들이 있다면, 보통주 지분율이나 가장 상세하게 기술된 섹션의 값을 우선하여 하나만 추출한다.

[필드 규칙]
1. shareholder (주주명)는 'nm' 필드를 사용한다.
2. major_shareholders의 ownership_ratio (지분율)는 'trmend_posesn_stock_qota_rt' 필드를 사용한다.
3. investee (피투자회사명)는 'inv_prm' 필드를 사용한다.
4. investments의 ownership_ratio (지분율)는 'trmend_blce_qota_rt' 필드를 사용한다.

[증거 데이터]
{context_data}

반드시 아래 JSON 스키마를 따르는 JSON 형식으로만 응답하라.
설명, 해석, 서술 문장은 절대 포함하지 말 것.

{{
  "major_shareholders": [
    {{
      "nm": "주주명",
      "trmend_posesn_stock_qota_rt": float
    }}
  ],
  "investments": [
    {{
      "inv_prm": "피투자회사명",
      "trmend_blce_qota_rt": float
    }}
  ]
}}
"""

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
    source_file = Path(__file__).resolve().parent / "sample" / "sample.html"

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
