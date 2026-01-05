import sys
from pathlib import Path

import html_parser_chatgpt
import html_parser_gemini
from bs4 import BeautifulSoup
from html_extractor_v6 import extract_evidence_blocks

# 현재 디렉토리를 path에 추가하여 임포트 가능하게 설정
SAMPLE = "코원.html"

current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))


def print_comparison_table(gemini_res, gpt_res):
    """Gemini와 ChatGPT의 결과를 나란히 출력하는 함수"""
    print("\n" + "=" * 110)
    print(f"{'항목':<20} | {'Gemini':<40} | {'ChatGPT':<40}")
    print("-" * 110)

    print("-" * 110)

    print("-" * 110)
    print(f"{'[주요 주주]':<20}")

    # 주주 명단 합치기 (중복 제거)
    all_shareholders = sorted(
        list(
            set(
                [s.shareholder for s in gemini_res.major_shareholders]
                + [s.shareholder for s in gpt_res.major_shareholders]
            )
        )
    )

    gemini_sh_map = {
        s.shareholder: s.ownership_ratio for s in gemini_res.major_shareholders
    }
    gpt_sh_map = {s.shareholder: s.ownership_ratio for s in gpt_res.major_shareholders}

    for sh in all_shareholders:
        g_val = f"{gemini_sh_map.get(sh, '-'):>5} %" if sh in gemini_sh_map else "N/A"
        o_val = f"{gpt_sh_map.get(sh, '-'):>5} %" if sh in gpt_sh_map else "N/A"
        match = "✅" if g_val == o_val else "❌"
        # 이름이 길면 줄바꿈 대신 적절히 보여줌
        sh_display = sh if len(sh) <= 20 else sh[:17] + "..."
        print(f"{sh_display:<20} | {g_val:<40} | {o_val:<40} {match}")

    print("-" * 110)
    print(f"{'[타법인 출자]':<20}")

    # 투자 명단 합치기
    all_investees = sorted(
        list(
            set(
                [i.investee for i in gemini_res.investments]
                + [i.investee for i in gpt_res.investments]
            )
        )
    )

    gemini_inv_map = {i.investee: i.ownership_ratio for i in gemini_res.investments}
    gpt_inv_map = {i.investee: i.ownership_ratio for i in gpt_res.investments}

    if not all_investees:
        print(f"{'계':<20} | {'없음':<40} | {'없음':<40} ✅")
    else:
        for inv in all_investees:
            g_val = (
                f"{gemini_inv_map.get(inv, '-'):>5} %"
                if inv in gemini_inv_map
                else "N/A"
            )
            o_val = f"{gpt_inv_map.get(inv, '-'):>5} %" if inv in gpt_inv_map else "N/A"
            match = "✅" if g_val == o_val else "❌"
            inv_display = inv if len(inv) <= 20 else inv[:17] + "..."
            print(f"{inv_display:<20} | {g_val:<40} | {o_val:<40} {match}")

    print("=" * 110 + "\n")


def main():
    source_file = current_dir / "sample" / SAMPLE
    if not source_file.exists():
        print(f"Error: {source_file} 파일을 찾을 수 없습니다.")
        return

    print(f"Reading file: {source_file}")
    html_content = source_file.read_text(encoding="utf-8")

    print("Extracting context once...")
    soup = BeautifulSoup(html_content, "html.parser")
    context_data = extract_evidence_blocks(soup)
    print(f"Context length: {len(context_data)} characters")

    gemini_result = None
    gpt_result = None

    # 1. Gemini
    print("\n[1/2] Gemini 분석 요청 중...")
    try:
        gemini_result = html_parser_gemini.extract_share_ratio_with_llm(context_data)
        # 파일 저장 (기존 기능 유지)
        res_json = gemini_result.model_dump_json(indent=2, ensure_ascii=False)
        (source_file.parent / "result_gemini.json").write_text(
            res_json, encoding="utf-8"
        )
    except Exception as e:
        print(f"Gemini 오류: {e}")

    # 2. ChatGPT
    print("[2/2] ChatGPT 분석 요청 중...")
    try:
        gpt_result = html_parser_chatgpt.extract_share_ratio_with_llm(context_data)
        # 파일 저장 (기존 기능 유지)
        res_json = gpt_result.model_dump_json(indent=2, ensure_ascii=False)
        (source_file.parent / "result_gpt.json").write_text(res_json, encoding="utf-8")
    except Exception as e:
        print(f"ChatGPT 오류: {e}")

    # 3. 비교 출력
    if gemini_result and gpt_result:
        print_comparison_table(gemini_result, gpt_result)
        print("테스트 완료: sample/ 폴더에 개별 JSON 파일이 저장되었습니다.")
    else:
        print(
            "\n[FAIL] 두 모델 중 하나 이상의 분석이 실패하여 비교를 수행할 수 없습니다."
        )


if __name__ == "__main__":
    main()
