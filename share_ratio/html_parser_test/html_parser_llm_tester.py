import sys
from pathlib import Path

# 현재 디렉토리를 path에 추가하여 임포트 가능하게 설정
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

import html_parser_chatgpt
import html_parser_gemini


def main():
    print("=" * 50)
    print("LLM HTML Parser 종합 테스트 시작")
    print("=" * 50)

    # 1. Gemini 테스트
    print("\n[1/2] Gemini 모델 테스트 중...")
    try:
        html_parser_gemini.main()
        print("\n[SUCCESS] Gemini 테스트 완료 (결과: result_gemini.json)")
    except Exception as e:
        print(f"\n[ERROR] Gemini 테스트 중 오류 발생: {e}")

    print("\n" + "-" * 30 + "\n")

    # 2. ChatGPT 테스트
    print("[2/2] ChatGPT (GPT-4o-mini) 모델 테스트 중...")
    try:
        html_parser_chatgpt.main()
        print("\n[SUCCESS] ChatGPT 테스트 완료 (결과: result_gpt.json)")
    except Exception as e:
        print(f"\n[ERROR] ChatGPT 테스트 중 오류 발생: {e}")

    print("\n" + "=" * 50)
    print("모든 LLM 테스트가 종료되었습니다.")
    print("=" * 50)


if __name__ == "__main__":
    main()
