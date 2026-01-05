import os
import re
import sys
from pathlib import Path
from typing import Dict, List

from bs4 import BeautifulSoup, NavigableString, Tag

SAMPLE = "투믹스홀딩스.html"

# 주석 및 footnote 패턴: (*1), (주1), *1, [1], 주1 등 대응
FOOTNOTE_PATTERN = re.compile(
    r"\(\s*[\*주]?\s*\d+\s*\)|"  # (1), (*1), (주1)
    r"\[\s*[\*주]?\s*\d+\s*\]|"  # [1], [*1]
    r"[\*주]\d+|"  # *1, 주1
    r"^\s*[\*주]\s*$"  # 단독 * 또는 주
)

# [v5] 지분율 데이터 식별 패턴: % 또는 "지분율" 텍스트
RATIO_PATTERN = re.compile(r"%|지분율")


def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")


def _clean_text(text: str, is_navigable_string: bool = False) -> str:
    if not text:
        return ""
    cleaned = FOOTNOTE_PATTERN.sub("", text)
    if not cleaned.strip():
        return " " if text.strip() or is_navigable_string else ""
    if is_navigable_string:
        return re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _get_simplified_html(tag) -> str:
    if isinstance(tag, NavigableString):
        return _clean_text(str(tag), is_navigable_string=True)
    if not isinstance(tag, Tag):
        return ""
    raw_tag_text = tag.get_text()
    if raw_tag_text.strip() and not _clean_text(raw_tag_text).strip():
        return ""
    inner_html = "".join(_get_simplified_html(child) for child in tag.children)
    inner_html = re.sub(r"\s+", " ", inner_html).strip()
    if not inner_html and tag.name not in ["td", "th", "tr"]:
        return ""
    attrs_str = ""
    if tag.name in ["td", "th"]:
        for attr in ["colspan", "rowspan"]:
            if tag.has_attr(attr):
                attrs_str += f' {attr}="{tag[attr]}"'
    return f"<{tag.name}{attrs_str}>{inner_html}</{tag.name}>"


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
        text = first_p.get_text()
        match = re.search(
            r"([가-힣a-zA-Z0-9]+?\s*주식회사|주식회사\s*[가-힣a-zA-Z0-9]+?)", text
        )
        if match:
            return _normalize(match.group(0))
    return "Unknown Company"


def _extract_global_meta(soup: BeautifulSoup) -> Dict:
    meta = {"unit": "원", "as_of_date": "Unknown"}
    text = soup.get_text()
    unit_match = re.search(r"\(단위\s*:\s*([가-힣]+)\)", text)
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


def _get_preceding_context(tag: Tag, max_tags: int = 2) -> List[Tag]:
    """테이블 앞의 설명 태그(p, div 등)를 최대 max_tags개까지 가져옴"""
    context_tags = []
    prev = tag.find_previous_sibling()
    count = 0
    while prev and count < max_tags:
        if isinstance(prev, Tag) and prev.name in ["p", "div", "span"]:
            text = prev.get_text().strip()
            # 빈 태그가 아니고, 너무 긴 텍스트(100자 초과)가 아니면 추가
            if text and len(text) < 150:
                context_tags.insert(0, prev)
                count += 1
        prev = prev.find_previous_sibling()
    return context_tags


def _get_section_title(tag: Tag) -> str:
    """현재 태그가 속한 섹션의 제목을 찾음"""
    section_pattern = re.compile(
        r"^\s*([0-9]{1,2}|[IVX]{1,3}|[가-하])[\.)\s]+\s*([가-힣\s]{2,50})"
    )
    # 위로 올라가며 섹션 제목 찾기
    prev = tag
    for _ in range(30):  # 최대 30개 태그까지 탐색
        prev = prev.find_previous()
        if not prev:
            break
        if isinstance(prev, Tag):
            text = prev.get_text().strip()
            if len(text) < 100:
                match = section_pattern.match(text.split("\n")[0])
                if match:
                    return text.split("\n")[0].strip()
    return "Unknown Section"


def extract_evidence_blocks(soup: BeautifulSoup) -> str:
    """
    HTML 원본 추출기 (v5):
    - 핵심 원칙: '%' 또는 '지분율' 텍스트가 있으면 무조건 추출
    - 테이블 추출 시 바로 앞의 설명 태그도 함께 추출
    - 섹션/키워드 필터링 최소화
    """
    company_name = _get_company_name(soup)
    global_meta = _extract_global_meta(soup)

    header = [
        "[META]",
        f"Company: {company_name}",
        f"Unit: {global_meta.get('unit', 'Unknown')}",
        f"Date: {global_meta.get('as_of_date', 'Unknown')}",
    ]

    evidence = ["\n".join(header)]
    seen_elements = set()

    # [v5] 모든 테이블과 텍스트 블록을 순회
    all_tags = soup.find_all(["table", "p", "div", "span"])

    for tag in all_tags:
        if tag in seen_elements:
            continue

        raw_text = tag.get_text()
        if not raw_text.strip():
            continue

        # [v5] 핵심 조건: % 또는 지분율이 있으면 추출
        has_ratio = bool(RATIO_PATTERN.search(raw_text))

        if not has_ratio:
            seen_elements.add(tag)
            continue

        section_title = _get_section_title(tag)

        # 테이블 처리
        if tag.name == "table":
            # 테이블 앞의 설명 컨텍스트 추출
            context_tags = _get_preceding_context(tag)
            context_html = ""
            for ctx_tag in context_tags:
                if ctx_tag not in seen_elements:
                    ctx_html = _get_simplified_html(ctx_tag)
                    if ctx_html.strip():
                        context_html += ctx_html + "\n"
                    seen_elements.add(ctx_tag)

            table_html = _get_simplified_html(tag)
            block = f"[DATA-TABLE-HTML]\n[Section: {section_title}]\n"
            if context_html.strip():
                block += f"[Context]\n{context_html.strip()}\n[Table]\n"
            block += table_html

            evidence.append(block)
            seen_elements.add(tag)
            for desc in tag.find_all(True):
                seen_elements.add(desc)

        # 텍스트 블록 처리 (p, div, span)
        else:
            simplified = _get_simplified_html(tag)
            if simplified.strip():
                evidence.append(
                    f"[DATA-GENERAL-HTML]\n[Section: {section_title}]\n{simplified}"
                )
            seen_elements.add(tag)
            # 자식 태그도 seen에 추가하여 중복 방지
            if hasattr(tag, "find_all"):
                for desc in tag.find_all(True):
                    seen_elements.add(desc)

    return "\n\n---\n\n".join(evidence)


if __name__ == "__main__":
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent / "tokenizer"))
    try:
        from token_counter import count_tokens_from_text, count_tokens_gemini
    except ImportError:
        count_tokens_from_text = None
        count_tokens_gemini = None

    test_file = Path(__file__).resolve().parent / "sample" / SAMPLE
    if not test_file.exists():
        print(f"Error: {test_file} 파일을 찾을 수 없습니다.")
    else:
        content = test_file.read_text(encoding="utf-8")
        soup = BeautifulSoup(content, "html.parser")
        result = extract_evidence_blocks(soup)
        clear_terminal()
        print(result)

        # 결과 파일 저장
        output_file = test_file.parent / "html_extractor_result.html"
        output_file.write_text(result, encoding="utf-8")
        print(f"\n[INFO] Result saved to: {output_file}")

        if count_tokens_from_text:
            tokens_gpt = count_tokens_from_text(result, model_name="gpt-5-nano")
            tokens_gemini = (
                count_tokens_gemini(result) if count_tokens_gemini else "N/A"
            )
            print("\n" + "=" * 50)
            print("📊 Token Analysis (Extracted Content):")
            print(f"   Characters: {len(result):,}")
            print(f"   GPT Tokens: {tokens_gpt:,}")
            print(
                f"   Gemini Tokens: {tokens_gemini if isinstance(tokens_gemini, str) else f'{tokens_gemini:,}'}"
            )
            print("=" * 50)
