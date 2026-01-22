import os
import re
import sys
from pathlib import Path
from typing import Dict

from bs4 import BeautifulSoup, NavigableString, Tag

# [v7] 기본 설정
SAMPLE = "hoban/20250403000344.html"

# 주석 및 footnote 패턴: (*1), (주1), *1, [1], 주1 등 대응
FOOTNOTE_PATTERN = re.compile(
    r"\(\s*[\*주]?\s*\d+\s*\)|"
    r"\[\s*[\*주]?\s*\d+\s*\]|"
    r"[\*주]\d+|"
    r"^\s*[\*주]\s*$"
)

# [v7] 확장된 태그 매핑 (LLM이 구조를 파악할 수 있는 최소 단위)
TAG_MAP = {
    "table": "t",
    "tr": "r",
    "td": "d",
    "th": "h",
    "div": "v",
    "span": "s",
    "p": "p",
    "h1": "h1",
    "h2": "h2",
    "h3": "h3",
    "h4": "h4",
    "ul": "ul",
    "li": "li",
    "b": "b",
    "strong": "b",
}

# [v7] 속성 매핑 (구조상 필수적인 colspan, rowspan만 보존)
ATTR_MAP = {
    "colspan": "c",
    "rowspan": "r",
}


def _clean_text(text: str, is_navigable_string: bool = False) -> str:
    if not text:
        return ""
    cleaned = FOOTNOTE_PATTERN.sub("", text)
    if not cleaned.strip():
        # 공백 노드 보존 여부 결정
        return " " if text.strip() or is_navigable_string else ""
    # 연속된 공백 및 특수 공백(\xa0) 정리
    cleaned = re.sub(r"[\s\xa0]+", " ", cleaned)
    return cleaned.strip() if not is_navigable_string else cleaned


def _get_simplified_html(tag) -> str:
    """
    태그와 속성을 극한으로 압축하여 토큰을 절약하면서 구조 유지
    """
    if isinstance(tag, NavigableString):
        return _clean_text(str(tag), is_navigable_string=True)
    if not isinstance(tag, Tag):
        return ""

    # 불필요한 태그 완전 제거
    if tag.name in ["script", "style", "meta", "link", "noscript", "iframe"]:
        return ""

    # 자식 노드 재귀 처리
    inner_parts = []
    for child in tag.children:
        part = _get_simplified_html(child)
        if part:
            inner_parts.append(part)

    inner_html = "".join(inner_parts).strip()

    # 내용이 없는 경우 스킵 (단, 테이블 구조 태그는 빈 값이라도 보존)
    if not inner_html and tag.name not in ["td", "th", "tr", "table"]:
        return ""

    # 압축된 태그명 결정
    t_name = TAG_MAP.get(tag.name)

    # 매핑에 없는 태그는 구조적 의미가 적다고 보고 텍스트만 유지
    if not t_name:
        return inner_html

    # 속성 압축 (c="2" r="3" 형태)
    attrs_str = ""
    for orig_attr, short_attr in ATTR_MAP.items():
        if tag.has_attr(orig_attr):
            attrs_str += f' {short_attr}="{tag[orig_attr]}"'

    return f"<{t_name}{attrs_str}>{inner_html}</{t_name}>"


def _normalize(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"[\s\xa0]+", " ", text).strip()


def _get_company_name(soup: BeautifulSoup) -> str:
    title = soup.title.string if soup.title else ""
    if title:
        match = re.search(
            r"([가-힣a-zA-Z0-9]+?\s*주식회사|주식회사\s*[가-힣a-zA-Z0-9]+?)", title
        )
        if match:
            return _normalize(match.group(0))
    first_p = soup.find("p")
    if first_p:
        match = re.search(
            r"([가-힣a-zA-Z0-9]+?\s*주식회사|주식회사\s*[가-힣a-zA-Z0-9]+?)",
            first_p.get_text(),
        )
        if match:
            return _normalize(match.group(0))
    return "Unknown Company"


def _extract_global_meta(soup: BeautifulSoup) -> Dict:
    meta = {"unit": "Unknown", "as_of_date": "Unknown"}
    text = soup.get_text()[:3000]  # 상단 위주 검색
    unit_match = re.search(r"\(단위\s*:\s*([가-힣a-z]+)\)", text, re.I)
    if unit_match:
        meta["unit"] = unit_match.group(1)

    date_patterns = [
        r"(\d{4}년\s*\d{1,2}월\s*\d{1,2}일)\s*현재",
        r"제\s*\d+\s*기말\s*(\d{4}년\s*\d{1,2}월\s*\d{1,2}일)",
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            meta["as_of_date"] = match.group(1)
            break
    return meta


def extract_full_content_minimized(soup: BeautifulSoup) -> str:
    company_name = _get_company_name(soup)
    meta = _extract_global_meta(soup)

    header = f"[META] C:{company_name} | U:{meta['unit']} | D:{meta['as_of_date']}\n"

    # Body 내용 또는 전체 내용 대상
    target = soup.find("body") or soup

    content = _get_simplified_html(target)

    # 최종 후처리: 태그 사이의 불필요한 공백 제거
    content = re.sub(r"[\s\xa0]+", " ", content)
    content = content.replace("> <", "><")

    # 가독성을 위해 주요 블록 태그 뒤에 줄바꿈 추가
    block_tags = ["t", "r", "p", "h1", "h2", "h3", "h4", "ul", "v"]
    for t in block_tags:
        content = content.replace(f"</{t}>", f"</{t}>\n")

    return header + content


def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")


if __name__ == "__main__":
    root_path = Path(__file__).resolve().parent.parent
    if str(root_path) not in sys.path:
        sys.path.append(str(root_path))

    try:
        from tokenizer.token_counter import count_tokens_from_text, count_tokens_gemini
    except ImportError:

        def count_tokens_from_text(text, **kwargs):
            return "N/A"

        def count_tokens_gemini(text, **kwargs):
            return "N/A"

    test_file = Path(__file__).resolve().parent / SAMPLE
    if not test_file.exists():
        print(f"Error: {test_file} 파일을 찾을 수 없습니다.")
    else:
        content = test_file.read_text(encoding="utf-8")
        soup = BeautifulSoup(content, "html.parser")
        result = extract_full_content_minimized(soup)

        # 결과 저장
        output_file = test_file.parent / "html_extractor_result_v7_full.txt"
        output_file.write_text(result, encoding="utf-8")

        clear_terminal()
        print("--- [Preivew (First 1500 chars)] ---")
        print(result[:1500] + "\n...")
        print(f"\n[INFO] Full result saved to: {output_file}")

        # 토큰 분석
        tokens_gpt = count_tokens_from_text(result, model_name="gpt-4")
        tokens_gemini = count_tokens_gemini(result)

        print("\n" + "=" * 50)
        print("📊 Token Analysis (Full Minimized v7):")
        print(f"   Characters: {len(result):,}")
        print(f"   GPT Tokens: {tokens_gpt}")
        print(f"   Gemini Tokens: {tokens_gemini}")
        print("=" * 50)
