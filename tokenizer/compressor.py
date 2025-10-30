"""
HTML Compressor for ChatGPT Token Optimization

HTML 문서에서 사람의 이해에 필요한 정보만 남기고,
나머지 불필요한 코드는 모두 제거하는 파이썬 코드입니다.

목적:
- ChatGPT API에 전달할 HTML 데이터의 토큰 수를 줄이기 위해
- 시각적 렌더링이나 구조 유지에는 필요하지만 텍스트 이해에는 불필요한 태그 및 내용을 모두 제거
"""

import os
import re

from bs4 import BeautifulSoup


def compress_html(input_file, output_file):
    """
    HTML 파일을 압축하여 핵심 텍스트만 추출합니다.

    Args:
        input_file (str): 입력 HTML 파일 경로
        output_file (str): 출력 텍스트 파일 경로
    """

    # HTML 파일 읽기
    try:
        with open(input_file, "r", encoding="utf-8") as file:
            html_content = file.read()
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {input_file}")
        return
    except Exception as e:
        print(f"❌ 파일 읽기 중 오류 발생: {e}")
        return

    # BeautifulSoup으로 HTML 파싱
    soup = BeautifulSoup(html_content, "html.parser")

    # 제거할 태그들 - 텍스트 이해에 불필요한 요소들
    tags_to_remove = [
        "style",
        "script",
        "meta",
        "link",
        "noscript",
        "iframe",
        "form",
        "input",
        "button",
        "nav",
        "header",
        "footer",
        "aside",
    ]

    # 불필요한 태그들 제거
    for tag_name in tags_to_remove:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # 모든 태그의 속성 제거 (텍스트만 유지)
    for tag in soup.find_all():
        tag.attrs = {}

    # 빈 태그들 제거
    for tag in soup.find_all():
        if not tag.get_text(strip=True) and not tag.find_all():
            tag.decompose()

    # 구조적 요소들 처리 - 섹션 구분을 위한 개행 추가
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        tag.string = f"\n\n### {tag.get_text().strip()}\n\n"

    # 표 처리 - 더 읽기 쉽게 포맷팅
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = []
            for td in tr.find_all(["td", "th"]):
                cell_text = td.get_text().strip()
                if cell_text and cell_text != "-":
                    cells.append(cell_text)
            if cells:
                rows.append(" | ".join(cells))

        if rows:
            table_text = "\n".join(rows)
            # 표를 구분하기 위한 개행 추가
            table.replace_with(f"\n\n{table_text}\n\n")

    # 문단 구분을 위한 개행 추가
    for p in soup.find_all("p"):
        if p.get_text().strip():
            p.string = f"\n{p.get_text().strip()}\n"

    # 텍스트 추출
    text_content = soup.get_text()

    # 텍스트 정리 - 불필요한 공백과 줄바꿈 제거
    # 연속된 공백을 하나로 줄이기 (줄바꿈은 제외)
    text_content = re.sub(r"[ \t]+", " ", text_content)

    # 연속된 줄바꿈을 최대 2개까지만 허용
    text_content = re.sub(r"\n\s*\n\s*\n+", "\n\n", text_content)

    # 앞뒤 공백 제거
    text_content = text_content.strip()

    # 결과를 파일로 저장
    try:
        with open(output_file, "w", encoding="utf-8") as file:
            file.write(text_content)
        print(f"✅ 압축 완료: {output_file}")
        print(f"📊 원본 파일 크기: {os.path.getsize(input_file):,} bytes")
        print(f"📊 압축 파일 크기: {os.path.getsize(output_file):,} bytes")

        # 압축률 계산
        compression_ratio = (
            1 - os.path.getsize(output_file) / os.path.getsize(input_file)
        ) * 100
        print(f"📈 압축률: {compression_ratio:.1f}%")

        # 토큰 수 추정 (한글 기준 대략적 계산)
        estimated_tokens = len(text_content.split())
        print(f"🔢 추정 토큰 수: {estimated_tokens:,} 개")

    except Exception as e:
        print(f"❌ 파일 저장 중 오류 발생: {e}")


def process_files_folder():
    """source 폴더의 HTML 파일을 target 폴더로 변환하여 저장합니다."""
    # 현재 스크립트가 tokenizer 폴더에 있으므로, before/after 폴더는 같은 레벨에 있습니다
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.join(script_dir, "before")
    target_dir = os.path.join(script_dir, "cleaned")

    if not os.path.exists(source_dir):
        print(f"❌ {source_dir} 폴더를 찾을 수 없습니다.")
        return

    # target 폴더가 없으면 생성
    os.makedirs(target_dir, exist_ok=True)

    # HTML 파일 목록 가져오기 (source 폴더 내 .html)
    html_files = [f for f in os.listdir(source_dir) if f.endswith(".html")]

    if not html_files:
        print(f"❌ {source_dir} 폴더에서 HTML 파일을 찾을 수 없습니다.")
        return

    print("🚀 HTML 파일 배치 처리 시작")
    print(f"📥 입력 폴더: {source_dir}")
    print(f"📤 출력 폴더: {target_dir}")
    print(f"📄 발견된 HTML 파일: {len(html_files)}개")
    print("-" * 50)

    processed_count = 0
    for html_file in html_files:
        # 입력 파일 경로
        input_path = os.path.join(source_dir, html_file)

        # 출력 파일명 생성 (확장자 제거 후 _후처리.txt 추가)
        file_name_without_ext = os.path.splitext(html_file)[0]
        output_filename = f"{file_name_without_ext}_후처리.txt"
        output_path = os.path.join(target_dir, output_filename)

        print(f"\n📝 처리 중: {html_file}")
        compress_html(input_path, output_path)
        processed_count += 1

    print("\n✅ 배치 처리 완료!")
    print(f"🎯 총 처리된 파일: {processed_count}개")


def main():
    """메인 실행 함수"""
    # files 폴더의 모든 HTML 파일 처리
    process_files_folder()


if __name__ == "__main__":
    main()
