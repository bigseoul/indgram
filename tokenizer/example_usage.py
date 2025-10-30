"""
tiktoken을 사용한 토큰 카운터 사용 예제

이 예제는 token_counter.py 모듈의 기본 사용법을 보여줍니다.
"""

from token_counter import (
    count_tokens_from_directory,
    count_tokens_from_file,
    count_tokens_from_text,
    print_token_analysis,
)


def example_text_token_count():
    """텍스트에서 직접 토큰 수 계산 예제"""
    print("=" * 50)
    print("📝 텍스트 토큰 계산 예제")
    print("=" * 50)

    # 한글 텍스트 예제
    korean_text = """
    주성엔지니어링은 반도체 및 디스플레이 제조 장비를 생산하는 회사입니다.
    1993년에 설립되어 지속적인 기술 개발과 혁신을 통해 성장해왔습니다.
    """

    # 영어 텍스트 예제
    english_text = """
    JUSUNG Engineering is a company that manufactures semiconductor and display equipment.
    Founded in 1993, the company has grown through continuous technological development and innovation.
    """

    # HTML 텍스트 예제
    html_text = """
    <html>
    <head><title>주성엔지니어링</title></head>
    <body>
        <h1>주성엔지니어링 주식회사</h1>
        <p>반도체 제조 장비 전문 기업</p>
        <table>
            <tr><td>설립년도</td><td>1993</td></tr>
            <tr><td>업종</td><td>반도체 장비</td></tr>
        </table>
    </body>
    </html>
    """

    # 각 텍스트의 토큰 수 계산
    texts = [
        ("한글 텍스트", korean_text),
        ("영어 텍스트", english_text),
        ("HTML 텍스트", html_text),
    ]

    for name, text in texts:
        token_count = count_tokens_from_text(text.strip())
        char_count = len(text.strip())
        print(f"\n📄 {name}:")
        print(f"   문자 수: {char_count:,}")
        print(f"   토큰 수: {token_count:,}")
        print(f"   토큰/문자 비율: {token_count / char_count:.4f}")


def example_file_token_count():
    """파일에서 토큰 수 계산 예제"""
    print("\n" + "=" * 50)
    print("📁 파일 토큰 계산 예제")
    print("=" * 50)

    # 주성엔지니어링.html 파일 분석
    html_file = "주성엔지니어링.html"
    try:
        result = count_tokens_from_file(html_file)
        print_token_analysis(result)

        # 추가 분석 정보
        if result["status"] == "success":
            file_size_kb = result["file_size_bytes"] / 1024
            estimated_cost_gpt4 = (
                result["token_count"] * 0.03 / 1000
            )  # GPT-4 input cost
            estimated_cost_gpt35 = (
                result["token_count"] * 0.001 / 1000
            )  # GPT-3.5 input cost

            print("\n💰 예상 API 비용 (USD):")
            print(f"   GPT-4: ${estimated_cost_gpt4:.6f}")
            print(f"   GPT-3.5-turbo: ${estimated_cost_gpt35:.6f}")

            print("\n📊 추가 통계:")
            print(f"   파일 크기: {file_size_kb:.1f} KB")
            print(
                f"   압축률 추정: {result['token_count'] / result['character_count']:.4f}"
            )

    except Exception as e:
        print(f"❌ 파일을 찾을 수 없습니다: {e}")


def example_directory_token_count():
    """디렉토리 전체 토큰 수 계산 예제"""
    print("\n" + "=" * 50)
    print("📂 디렉토리 토큰 계산 예제")
    print("=" * 50)

    # 현재 디렉토리의 모든 HTML 파일 분석
    results = count_tokens_from_directory(".", [".html"])

    if results:
        total_tokens = 0
        total_files = 0

        for result in results:
            print_token_analysis(result)
            if result["status"] == "success":
                total_tokens += result["token_count"]
                total_files += 1

        if total_files > 0:
            print("\n🎯 전체 요약:")
            print(f"   총 {total_files}개 파일")
            print(f"   총 {total_tokens:,} 토큰")
            print(f"   평균 {total_tokens // total_files:,} 토큰/파일")
    else:
        print("📭 분석할 HTML 파일이 없습니다.")


def example_model_comparison():
    """다양한 모델에서의 토큰 수 비교 예제"""
    print("\n" + "=" * 50)
    print("🔄 모델별 토큰 수 비교 예제")
    print("=" * 50)

    sample_text = """
    주성엔지니어링(주)은 반도체 및 디스플레이 제조 장비를 개발·생산하는 전문기업입니다.
    1993년 설립 이래 지속적인 연구개발을 통해 세계 최고 수준의 기술력을 확보하고 있습니다.
    특히 CVD(Chemical Vapor Deposition) 장비 분야에서 세계적인 경쟁력을 보유하고 있습니다.
    """

    models = ["gpt-4", "gpt-3.5-turbo"]

    print(f"📝 분석 텍스트: {len(sample_text)} 문자")
    print("-" * 50)

    for model in models:
        try:
            token_count = count_tokens_from_text(sample_text, model)
            print(f"🤖 {model:15}: {token_count:,} 토큰")
        except Exception as e:
            print(f"❌ {model:15}: 오류 - {e}")


if __name__ == "__main__":
    print("🚀 tiktoken 토큰 카운터 예제 실행")

    # 1. 텍스트 토큰 계산
    example_text_token_count()

    # 2. 파일 토큰 계산
    example_file_token_count()

    # 3. 디렉토리 토큰 계산
    example_directory_token_count()

    # 4. 모델별 비교
    example_model_comparison()

    print("\n" + "=" * 50)
    print("✅ 모든 예제 완료!")
    print("=" * 50)
