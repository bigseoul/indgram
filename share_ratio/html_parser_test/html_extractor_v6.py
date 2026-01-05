import re
import sys
from pathlib import Path
from typing import Dict, List

from bs4 import BeautifulSoup, NavigableString, Tag

SAMPLE = "인스파이어인티그레이티드리조트.html"

# 주석 및 footnote 패턴: (*1), (주1), *1, [1], 주1 등 대응
FOOTNOTE_PATTERN = re.compile(
    r"\(\s*[\*주]?\s*\d+\s*\)|"  # (1), (*1), (주1)
    r"\[\s*[\*주]?\s*\d+\s*\]|"  # [1], [*1]
    r"[\*주]\d+|"  # *1, 주1
    r"^\s*[\*주]\s*$"  # 단독 * 또는 주
)

# [v6] 지분율 데이터 식별 패턴: % 또는 "지분율" 텍스트
RATIO_PATTERN = re.compile(r"%|지분율")

# [v6] 태그 매핑
TAG_MAP = {
    "table": "t",
    "tr": "r",
    "td": "d",
    "th": "h",
    "div": "v",
    "span": "s",
    "p": "p",
}

# [v6] 속성 매핑
ATTR_MAP = {
    "colspan": "c",
    "rowspan": "r",
}


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
    """
    태그와 속성을 극한으로 압축하여 토큰을 절약함.
    예: <table colspan="2"> -> <t c="2">
    """
    if isinstance(tag, NavigableString):
        return _clean_text(str(tag), is_navigable_string=True)
    if not isinstance(tag, Tag):
        return ""

    raw_tag_text = tag.get_text()
    if raw_tag_text.strip() and not _clean_text(raw_tag_text).strip():
        return ""

    # 자식 노드 재귀 처리
    inner_html = "".join(_get_simplified_html(child) for child in tag.children)
    inner_html = re.sub(r"\s+", " ", inner_html).strip()

    # 필수적인 구조 태그가 아니면서 내용이 비어있으면 스킵
    if not inner_html and tag.name not in ["td", "th", "tr", "table"]:
        return ""

    # 태약된 태그명 결정
    t_name = TAG_MAP.get(tag.name, tag.name)

    # 속성 압축
    attrs_str = ""
    for orig_attr, short_attr in ATTR_MAP.items():
        if tag.has_attr(orig_attr):
            attrs_str += f' {short_attr}="{tag[orig_attr]}"'

    # 결과 조립 시 공백 최소화
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
    context_tags = []
    prev = tag.find_previous_sibling()
    count = 0
    while prev and count < max_tags:
        if isinstance(prev, Tag) and prev.name in ["p", "div", "span"]:
            text = prev.get_text().strip()
            if text and len(text) < 150:
                context_tags.insert(0, prev)
                count += 1
        prev = prev.find_previous_sibling()
    return context_tags


def _get_section_title(tag: Tag) -> str:
    section_pattern = re.compile(
        r"^\s*([0-9]{1,2}|[IVX]{1,3}|[가-하])[\.)\s]+\s*([가-힣\s]{2,50})"
    )
    prev = tag
    for _ in range(30):
        prev = prev.find_previous()
        if not prev:
            break
        if isinstance(prev, Tag):
            text = prev.get_text().strip()
            if len(text) < 100:
                match = section_pattern.match(text.split("\n")[0])
                if match:
                    return text.split("\n")[0].strip()
    return "Unknown"


def extract_evidence_blocks(soup: BeautifulSoup) -> str:
    company_name = _get_company_name(soup)
    global_meta = _extract_global_meta(soup)

    header = [
        "[META]",
        f"C: {company_name}",
        f"U: {global_meta.get('unit', 'Unknown')}",
        f"D: {global_meta.get('as_of_date', 'Unknown')}",
    ]

    evidence = ["\n".join(header)]
    seen_elements = set()

    all_tags = soup.find_all(["table", "p", "div", "span"])

    for tag in all_tags:
        if tag in seen_elements:
            continue

        raw_text = tag.get_text()
        if not raw_text.strip():
            continue

        if not bool(RATIO_PATTERN.search(raw_text)):
            seen_elements.add(tag)
            continue

        section_title = _get_section_title(tag)

        if tag.name == "table":
            context_tags = _get_preceding_context(tag)
            context_html = ""
            for ctx_tag in context_tags:
                if ctx_tag not in seen_elements:
                    ctx_html = _get_simplified_html(ctx_tag)
                    if ctx_html.strip():
                        context_html += ctx_html + "\n"
                    seen_elements.add(ctx_tag)

            table_html = _get_simplified_html(tag)
            block = f"[TBL]\n[S: {section_title}]\n"
            if context_html.strip():
                block += f"[C]\n{context_html.strip()}\n[T]\n"
            block += table_html

            evidence.append(block)
            seen_elements.add(tag)
            for desc in tag.find_all(True):
                seen_elements.add(desc)
        else:
            simplified = _get_simplified_html(tag)
            if simplified.strip():
                evidence.append(f"[TXT]\n[S: {section_title}]\n{simplified}")
            seen_elements.add(tag)
            if hasattr(tag, "find_all"):
                for desc in tag.find_all(True):
                    seen_elements.add(desc)

    return "\n---\n".join(evidence)


if __name__ == "__main__":
    # 토큰 카운터 경로 설정 (indgram 루트를 path에 추가)
    root_path = Path(__file__).resolve().parent.parent.parent
    if str(root_path) not in sys.path:
        sys.path.append(str(root_path))

    try:
        from tokenizer.token_counter import count_tokens_from_text, count_tokens_gemini
    except ImportError:

        def count_tokens_from_text(text, **kwargs):
            return "ImportError"

        def count_tokens_gemini(text, **kwargs):
            return "ImportError"

    test_file = Path(__file__).resolve().parent / "sample" / SAMPLE
    if not test_file.exists():
        print(f"Error: {test_file} 파일을 찾을 수 없습니다.")
    else:
        content = test_file.read_text(encoding="utf-8")
        soup = BeautifulSoup(content, "html.parser")
        result = extract_evidence_blocks(soup)

        # 결과 저장
        output_file = test_file.parent / "html_extractor_result_v6.html"
        output_file.write_text(result, encoding="utf-8")

        print(result)
        print(f"\n[INFO] Result saved to: {output_file}")

        # 토큰 분석
        try:
            tokens_gpt = count_tokens_from_text(result, model_name="gpt-4")
        except Exception as e:
            tokens_gpt = f"Error: {e}"

        try:
            tokens_gemini = count_tokens_gemini(result)
        except Exception as e:
            tokens_gemini = f"Error: {e}"

        print("\n" + "=" * 50)
        print("📊 Token Analysis (Optimized v6):")
        print(f"   Characters: {len(result):,}")
        print(f"   GPT Tokens: {tokens_gpt if isinstance(tokens_gpt, int) else 'N/A'}")
        print(
            f"   Gemini Tokens: {tokens_gemini if isinstance(tokens_gemini, int) else 'N/A'}"
        )
        print("=" * 50)
