import argparse
import os
from pathlib import Path
from typing import Dict, List

import tiktoken


def get_encoding(model_name: str = "gpt-4") -> tiktoken.Encoding:
    """
    tiktoken 인코딩 객체를 반환합니다.

    Args:
        model_name: 사용할 모델명 (기본값: "gpt-4")

    Returns:
        tiktoken.Encoding: 인코딩 객체
    """
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        # 모델명이 존재하지 않는 경우 기본 인코딩 사용
        encoding = tiktoken.get_encoding("cl100k_base")

    return encoding


def count_tokens_from_text(text: str, model_name: str = "gpt-4") -> int:
    """
    텍스트의 토큰 수를 계산합니다.

    Args:
        text: 토큰을 계산할 텍스트
        model_name: 사용할 모델명

    Returns:
        int: 토큰 수
    """
    encoding = get_encoding(model_name)
    tokens = encoding.encode(text)
    return len(tokens)


def count_tokens_from_file(
    file_path: str, model_name: str = "gpt-4", encoding: str = "utf-8"
) -> Dict[str, any]:
    """
    파일에서 토큰 수를 계산합니다.

    Args:
        file_path: 파일 경로
        model_name: 사용할 모델명
        encoding: 파일 인코딩

    Returns:
        Dict: 파일 정보와 토큰 수가 포함된 딕셔너리
    """
    try:
        with open(file_path, "r", encoding=encoding) as file:
            content = file.read()

        token_count = count_tokens_from_text(content, model_name)
        file_size = os.path.getsize(file_path)

        return {
            "file_path": file_path,
            "file_size_bytes": file_size,
            "character_count": len(content),
            "token_count": token_count,
            "tokens_per_byte": token_count / file_size if file_size > 0 else 0,
            "model_used": model_name,
            "status": "success",
        }

    except UnicodeDecodeError:
        # UTF-8로 읽을 수 없는 경우 다른 인코딩 시도
        try:
            with open(file_path, "r", encoding="cp949") as file:
                content = file.read()
            token_count = count_tokens_from_text(content, model_name)
            file_size = os.path.getsize(file_path)

            return {
                "file_path": file_path,
                "file_size_bytes": file_size,
                "character_count": len(content),
                "token_count": token_count,
                "tokens_per_byte": token_count / file_size if file_size > 0 else 0,
                "model_used": model_name,
                "encoding_used": "cp949",
                "status": "success",
            }
        except Exception as e:
            return {"file_path": file_path, "error": str(e), "status": "error"}

    except Exception as e:
        return {"file_path": file_path, "error": str(e), "status": "error"}


def count_tokens_from_directory(
    directory_path: str, file_extensions: List[str] = None, model_name: str = "gpt-4"
) -> List[Dict[str, any]]:
    """
    디렉토리 내의 모든 파일에서 토큰 수를 계산합니다.

    Args:
        directory_path: 디렉토리 경로
        file_extensions: 처리할 파일 확장자 리스트 (기본값: ['.html', '.txt', '.md'])
        model_name: 사용할 모델명

    Returns:
        List[Dict]: 각 파일의 토큰 정보가 포함된 딕셔너리 리스트
    """
    if file_extensions is None:
        file_extensions = [".html", ".txt", ".md", ".py", ".js", ".css"]

    results = []
    directory = Path(directory_path)

    for file_path in directory.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in file_extensions:
            result = count_tokens_from_file(str(file_path), model_name)
            results.append(result)

    return results


def print_token_analysis(result: Dict[str, any]):
    """토큰 분석 결과를 출력합니다."""
    if result["status"] == "success":
        print(f"\n📄 파일: {result['file_path']}")
        print(f"   파일 크기: {result['file_size_bytes']:,} bytes")
        print(f"   문자 수: {result['character_count']:,} characters")
        print(f"   토큰 수: {result['token_count']:,} tokens")
        print(f"   토큰/바이트 비율: {result['tokens_per_byte']:.4f}")
        print(f"   사용 모델: {result['model_used']}")
        if "encoding_used" in result:
            print(f"   파일 인코딩: {result['encoding_used']}")
    else:
        print(f"\n❌ 오류 - {result['file_path']}: {result['error']}")


def main():
    parser = argparse.ArgumentParser(description="HTML 파일의 토큰 수를 계산합니다.")
    parser.add_argument("path", help="파일 또는 디렉토리 경로")
    parser.add_argument(
        "--model", default="gpt-4", help="사용할 모델명 (기본값: gpt-4)"
    )
    parser.add_argument(
        "--extensions",
        nargs="*",
        default=[".html", ".txt", ".md"],
        help="처리할 파일 확장자 (기본값: .html .txt .md)",
    )

    args = parser.parse_args()

    path = Path(args.path)

    if path.is_file():
        # 단일 파일 처리
        result = count_tokens_from_file(str(path), args.model)
        print_token_analysis(result)

    elif path.is_directory():
        # 디렉토리 처리
        results = count_tokens_from_directory(str(path), args.extensions, args.model)

        total_tokens = 0
        success_count = 0

        print(f"\n📁 디렉토리: {path}")
        print("=" * 60)

        for result in results:
            print_token_analysis(result)
            if result["status"] == "success":
                total_tokens += result["token_count"]
                success_count += 1

        print("\n" + "=" * 60)
        print("📊 요약:")
        print(f"   처리된 파일 수: {success_count}")
        print(f"   총 토큰 수: {total_tokens:,}")
        print(
            f"   평균 토큰/파일: {total_tokens / success_count:,.0f}"
            if success_count > 0
            else "   평균 토큰/파일: 0"
        )

    else:
        print(f"❌ 경로를 찾을 수 없습니다: {path}")


if __name__ == "__main__":
    # 예제 실행
    if len(os.sys.argv) == 1:
        # 명령행 인자가 없는 경우 예제 실행
        print("🔍 토큰 카운터 예제 실행")

        # 현재 디렉토리의 주성엔지니어링.html 파일 분석
        html_file = "주성엔지니어링.html"
        if os.path.exists(html_file):
            print(f"\n📄 {html_file} 파일 분석:")
            result = count_tokens_from_file(html_file)
            print_token_analysis(result)
        else:
            print(f"\n⚠️  {html_file} 파일을 찾을 수 없습니다.")
            print("현재 디렉토리의 HTML 파일들을 찾아서 분석합니다...")

            # 현재 디렉토리에서 HTML 파일 찾기
            results = count_tokens_from_directory(".", [".html"])
            if results:
                for result in results:
                    print_token_analysis(result)
            else:
                print("HTML 파일을 찾을 수 없습니다.")

        print("\n" + "=" * 60)
        print("💡 사용법:")
        print("   python token_counter.py <파일경로>          # 단일 파일 분석")
        print("   python token_counter.py <디렉토리경로>      # 디렉토리 전체 분석")
        print("   python token_counter.py <경로> --model gpt-3.5-turbo  # 모델 지정")
    else:
        main()
