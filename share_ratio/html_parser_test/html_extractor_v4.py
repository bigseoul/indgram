import os
import re
import sys
from pathlib import Path
from typing import Dict

from bs4 import BeautifulSoup

SAMPLE = "투믹스홀딩스.html"

# 주석 및 footnote 패턴: (*1), (주1), *1, [1], 주1 등 대응
FOOTNOTE_PATTERN = re.compile(
    r"\(\s*[\*주]?\s*\d+\s*\)|"  # (1), (*1), (주1)
    r"\[\s*[\*주]?\s*\d+\s*\]|"  # [1], [*1]
    r"[\*주]\d+|"  # *1, 주1
    r"^\s*[\*주]\s*$"  # 단독 * 또는 주
)


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
    from bs4 import NavigableString, Tag

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


def extract_evidence_blocks(soup: BeautifulSoup) -> str:
    """
    HTML 원본 추출기 (v4):
    1. 인트로 섹션(회사의 개요 등)은 텍스트와 테이블 모두 추출
    2. 그 외 섹션은 '지분/주주' 키워드와 '%' 기호가 함께 있는 테이블/텍스트 위주로 추출
    3. 회계 원칙 위주의 이론적 문장은 필터링
    """
    company_name = _get_company_name(soup)
    global_meta = _extract_global_meta(soup)

    section_pattern = re.compile(
        r"^\s*([0-9]{1,2}|[IVX]{1,3}|[가-하])[\.\)\s]+\s*(회사의\s*개요|일반사항|일반적인\s*사항|일반\s*사항)",
        re.IGNORECASE,
    )
    any_section_pattern = re.compile(
        r"^\s*([0-9]{1,2}|[IVX]{1,3}|[가-하])[\.\)\s]+\s*([가-힣\s]{2,50})"
    )

    skip_section_keywords = [
        r"회계정책",
        r"작성기준",
        r"현금흐름표",
        r"주당손익",
        r"주당순이익",
        r"위험관리",
        r"금융상품의\s*범주",
        r"금융자산",
        r"금융부채",
        r"우발채무",
        r"약정사항",
    ]

    accounting_principle_pattern = re.compile(
        r"(인식|측정|처리|계상|분류|적용)(합니다|됩니다|하며|하여|하되)\.?\s*$",
        re.MULTILINE,
    )

    data_keywords = [
        "지분",
        "주주",
        "자본금",
        "출자",
        "종속기업",
        "피투자",
        "소유",
        "보유",
        "지배",
    ]

    # 지분율 데이터임을 확신하게 해주는 강력한 문자
    ratio_marker = "%"

    exclude_keywords = [
        "비지배지분율",
        "비지배지분",
        "채권",
        "채무",
        "매출",
        "매입",
        "지급보증",
        "담보제공",
        "주요거래",
        "자금거래",
        "수익",
        "비용",
        "채무면제",
    ]

    header = [
        "[META]",
        f"Company: {company_name}",
        f"Unit: {global_meta.get('unit', 'Unknown')}",
        f"Date: {global_meta.get('as_of_date', 'Unknown')}",
    ]

    evidence = ["\n".join(header)]
    seen_elements = set()
    all_tags = soup.find_all(["h1", "h2", "h3", "p", "table", "div", "span"])

    idx = 0
    current_section = "Unknown Section"
    while idx < len(all_tags):
        tag = all_tags[idx]
        if tag in seen_elements:
            idx += 1
            continue

        raw_text = tag.get_text().strip()
        if not raw_text:
            idx += 1
            continue

        if tag.name in ["h1", "h2", "h3"] or (tag.name == "p" and len(raw_text) < 100):
            first_line = raw_text.split("\n")[0].strip()
            section_m = any_section_pattern.match(first_line)
            if section_m:
                current_section = first_line

        if any(re.search(kw, current_section) for kw in skip_section_keywords):
            seen_elements.add(tag)
            idx += 1
            continue

        is_intro_section = bool(section_pattern.match(current_section))

        if not _clean_text(raw_text).strip():
            seen_elements.add(tag)
            idx += 1
            continue

        # [v4] 테이블 추출 로직 강화
        if tag.name == "table":
            table_text = tag.get_text()

            # 인트로 섹션이면 무조건 가져감, 그 외에는 지분 키워드와 %가 있어야 함
            has_ratio = ratio_marker in table_text or "지분율" in table_text
            has_keyword = any(kw in table_text for kw in data_keywords)
            not_excluded = not any(ek in table_text for ek in exclude_keywords)

            if is_intro_section or (has_ratio and has_keyword and not_excluded):
                evidence.append(
                    f"[DATA-TABLE-HTML]\n[Section: {current_section}]\n{_get_simplified_html(tag)}"
                )
                seen_elements.add(tag)
                for desc in tag.find_all(True):
                    seen_elements.add(desc)
            else:
                seen_elements.add(tag)
            idx += 1
            continue

        # [v4] 텍스트 블록(P 등) 추출 로직
        if is_intro_section:
            # 인트로 섹션은 일반적인 경우 다 가져옴 (단, 다른 섹션 시작 전까지)
            if section_pattern.match(raw_text):
                block_content = []
                curr_idx = idx
                count = 0
                while curr_idx < len(all_tags) and count < 15:
                    t = all_tags[curr_idx]
                    if count > 0 and (
                        t.name in ["h1", "h2", "h3"]
                        or section_pattern.match(t.get_text().strip())
                    ):
                        break
                    if t not in seen_elements:
                        if _clean_text(t.get_text()).strip():
                            block_content.append(_get_simplified_html(t))
                            seen_elements.add(t)
                            if hasattr(t, "find_all"):
                                for desc in t.find_all(True):
                                    seen_elements.add(desc)
                    curr_idx += 1
                    count += 1
                if block_content:
                    evidence.append(
                        f"[DATA-GENERAL-HTML]\n[Section: {current_section}]\n"
                        + "\n".join(block_content)
                    )
                idx = curr_idx
                continue
            else:
                evidence.append(
                    f"[DATA-GENERAL-HTML]\n[Section: {current_section}]\n{_get_simplified_html(tag)}"
                )
                seen_elements.add(tag)
        else:
            # 그 외 섹션의 텍스트: 회계 원칙이 아니면서 + 지분 키워드와 %가 같이 있는 경우만!
            is_principle = bool(accounting_principle_pattern.search(raw_text))
            has_keyword = any(kw in raw_text for kw in data_keywords)
            has_ratio = ratio_marker in raw_text

            if not is_principle and has_keyword and has_ratio:
                evidence.append(
                    f"[DATA-GENERAL-HTML]\n[Section: {current_section}]\n{_get_simplified_html(tag)}"
                )
                seen_elements.add(tag)

        idx += 1

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
