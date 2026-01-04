import os
import re
import sys
from pathlib import Path
from typing import Dict

from bs4 import BeautifulSoup

SAMPLE = "투믹스홀딩스.html"

# 주석 및 footnote 패턴: (*1), (주1), *1, [1], 주1 등 대응
# 숫자가 단독으로 쓰인 경우는 지분율 등 소중한 데이터일 수 있으므로
# 반드시 괄호()나 대괄호[], 혹은 *, 주 기호가 동반된 경우만 제거합니다.
FOOTNOTE_PATTERN = re.compile(
    r"\(\s*[\*주]?\s*\d+\s*\)|"  # (1), (*1), (주1)
    r"\[\s*[\*주]?\s*\d+\s*\]|"  # [1], [*1]
    r"[\*주]\d+|"  # *1, 주1
    r"^\s*[\*주]\s*$"  # 단독 * 또는 주
)


def clear_terminal():
    # os.name이 'nt'이면 윈도우(cls), 아니면 맥/리눅스(clear) 실행
    os.system("cls" if os.name == "nt" else "clear")


def _clean_text(text: str, is_navigable_string: bool = False) -> str:
    """
    텍스트 내의 주석 마커를 제거하고 정규화합니다.
    is_navigable_string이 True이면 순수 텍스트 노드이므로
    공백 소실을 방지하기 위해 과도한 strip()을 자제합니다.
    """
    if not text:
        return ""

    # 1. 문서 전체의 FOOTNOTE_PATTERN 제거
    cleaned = FOOTNOTE_PATTERN.sub("", text)

    # 2. 만약 제거 후 텍스트가 순수 공백만 남았다면
    if not cleaned.strip():
        # 원래 공백이 있었다면 공백 하나로 보존 (단어 붙음 방지)
        return " " if text.strip() or is_navigable_string else ""

    # 3. 앞뒤 공백 정외 (단, NavigableString인 경우 문맥 유지를 위해 공백 하나 수준으로 정규화)
    if is_navigable_string:
        return re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()


def _get_simplified_html(tag) -> str:
    """
    태그의 모든 속성(style, class 등)을 제거하고
    핵심 구조와 텍스트만 남긴 HTML 문자열을 반환합니다.
    자식 노드 간의 공백을 보존하여 단어가 붙는 현상을 방지합니다.
    """
    from bs4 import NavigableString, Tag

    if isinstance(tag, NavigableString):
        return _clean_text(str(tag), is_navigable_string=True)

    if not isinstance(tag, Tag):
        return ""

    # 주석으로만 구성된 태그인지 확인
    raw_tag_text = tag.get_text()
    if raw_tag_text.strip() and not _clean_text(raw_tag_text).strip():
        return ""

    # 자식 노드들을 단순화하여 합침 (공백 보전을 위해 ""로 join하되 _clean_text가 공백을 관리함)
    inner_html = "".join(_get_simplified_html(child) for child in tag.children)

    # 연속된 공백 정규화
    inner_html = re.sub(r"\s+", " ", inner_html).strip()

    # 내용이 없는 비본질적인 태그는 제거 (단, 테이블 셀은 구조상 유지)
    if not inner_html and tag.name not in ["td", "th", "tr"]:
        return ""

    # 테이블 구조를 위한 속성(colspan, rowspan)은 보존
    attrs_str = ""
    if tag.name in ["td", "th"]:
        for attr in ["colspan", "rowspan"]:
            if tag.has_attr(attr):
                attrs_str += f' {attr}="{tag[attr]}"'

    return f"<{tag.name}{attrs_str}>{inner_html}</{tag.name}>"


def _normalize(text: str) -> str:
    """
    텍스트 정규화: 불필요한 공백 제거
    """
    if not text:
        return ""
    return re.sub(r"[\s\xa0]+", " ", text).strip()


def _get_company_name(soup: BeautifulSoup) -> str:
    """
    문서에서 회사명 추출
    """
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
    """
    전역 메타데이터(단위, 기준일) 추출
    """
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
    HTML 원본 추출기 (v3):
    1. 섹션 필터 추가: 회계정책, 주당순이익 등 '이론적' 섹션 스킵
    2. 일반 사항 키워드: 문맥 유지 (태그 원본 포함)
    3. 데이터 키워드: 오직 '지분율' 테이블만 원본으로 추출
    """
    company_name = _get_company_name(soup)
    global_meta = _extract_global_meta(soup)

    # 섹션 헤더 정규식: "1. 회사의 개요", "I. 일반사항", "1.일반사항" 등 대응
    section_pattern = re.compile(
        r"^\s*([0-9]{1,2}|[IVX]{1,3}|[가-하])[\.\)\s]+\s*(회사의\s*개요|일반사항|일반적인\s*사항|일반\s*사항)",
        re.IGNORECASE,
    )
    # 모든 상위 섹션 번호/제목을 추적하기 위한 정규식
    any_section_pattern = re.compile(
        r"^\s*([0-9]{1,2}|[IVX]{1,3}|[가-하])[\.\)\s]+\s*([가-힣\s]{2,50})",
    )

    # [v3 신규] 스킵 대상 섹션 키워드 (정규식 경고 방지를 위해 raw string 사용)
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

    # [v3 신규] 회계 원칙/이론 설명 문장 패턴
    # 인식합니다, 측정합니다, 처리합니다, 계상됩니다 등으로 끝나는 문장들을 타겟팅
    accounting_principle_pattern = re.compile(
        r"(인식|측정|처리|계상|분류|적용)(합니다|됩니다|하며|하여|하되)\.?\s*$",
        re.MULTILINE,
    )

    # 지분 구조와 직접 관련된 확실한 키워드 조합 (범용성 고려)
    data_keywords = [
        "지분율",
        "주주",
        "자본금",
        "출자",
        "종속기업",
        "피투자",
        "소유",
        "보유",
        "지배",
    ]
    term_markers = ["당기", "당기말", "당기 말", "현재"]
    # 노이즈(거래, 채권/채무, 담보 등)를 걸러내기 위한 제외 키워드 강화
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

    # 모든 요소를 순차적으로 탐색
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

        # 현재 위치한 섹션 제목 업데이트
        if tag.name in ["h1", "h2", "h3"] or (tag.name == "p" and len(raw_text) < 100):
            first_line = raw_text.split("\n")[0].strip()
            section_m = any_section_pattern.match(first_line)
            if section_m:
                current_section = first_line

        # [v3 신규] 현재 섹션이 스킵 대상인 경우
        if any(re.search(kw, current_section) for kw in skip_section_keywords):
            seen_elements.add(tag)
            idx += 1
            continue

        # [v3 신규] Phrase Filter: 일반 텍스트 블록에서 원칙 설명 문장 제외
        # 단, '회사의 개요'나 '일반사항' 섹션은 예외로 함 (도입부 보호)
        is_intro_section = bool(section_pattern.match(current_section))
        if not is_intro_section and tag.name == "p":
            if accounting_principle_pattern.search(raw_text):
                seen_elements.add(tag)
                idx += 1
                continue

        # 주석 마커만 있는 태그이거나 주석 설명문(예: *1 ...)이면 건너뜀
        if not _clean_text(raw_text).strip():
            seen_elements.add(tag)
            idx += 1
            continue

        # 1. 일반적인 사항: 정규식으로 섹션 시작점 포착
        if section_pattern.match(raw_text):
            block_content = []
            curr_idx = idx
            count = 0
            while curr_idx < len(all_tags) and count < 15:
                t = all_tags[curr_idx]
                # 다른 대단원이 시작되면 중단
                if count > 0 and (
                    t.name in ["h1", "h2", "h3"]
                    or section_pattern.match(t.get_text().strip())
                ):
                    break
                if t not in seen_elements:
                    # 주석 패턴 재확인 (v2 개선됨)
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

        # 2. '지분율' 키워드: 테이블 위주로 탐색
        elif any(kw in raw_text for kw in data_keywords):
            if len(raw_text) > 500 and tag.name not in ["table", "div"]:
                idx += 1
                continue

            target_table = None
            if tag.name == "table":
                target_table = tag
            else:
                search_idx = idx + 1
                for _ in range(10):
                    if search_idx >= len(all_tags):
                        break
                    if all_tags[search_idx].name == "table":
                        target_table = all_tags[search_idx]
                        break
                    search_idx += 1

            if target_table and target_table not in seen_elements:
                table_text = target_table.get_text()

                if "지분율" in table_text and not any(
                    ek in table_text for ek in exclude_keywords
                ):
                    term_context_tags = []
                    term_context_text = table_text
                    search_curr = target_table
                    for _ in range(10):
                        p_node = search_curr.find_previous_sibling()
                        if not p_node:
                            break
                        if p_node.name in ["h1", "h2", "h3"]:
                            break

                        node_text = p_node.get_text().strip()
                        term_context_text += node_text

                        is_marker = any(
                            m in node_text for m in term_markers + ["(단위"]
                        )
                        is_metadata_node = p_node.name == "table" or (
                            p_node.name == "p" and len(node_text) < 200
                        )

                        if is_marker or is_metadata_node:
                            term_context_tags.insert(0, _get_simplified_html(p_node))
                        search_curr = p_node

                    header_text = (
                        target_table.thead.get_text() if target_table.thead else ""
                    )
                    if not header_text:
                        header_rows = target_table.find_all("tr")[:3]
                        header_text = " ".join(r.get_text() for r in header_rows)

                    if any(m in term_context_text for m in term_markers) or any(
                        m in header_text for m in term_markers
                    ):
                        clean_anchor = re.sub(r"\s+", " ", raw_text[:150]).strip()
                        title_info = f"<p><b>[Anchor]</b> {clean_anchor}</p>"
                        context_html = "\n".join(term_context_tags)
                        evidence.append(
                            f"[DATA-TABLE-HTML]\n[Section: {current_section}]\n{title_info}\n{context_html}\n{_get_simplified_html(target_table)}"
                        )

                        seen_elements.add(target_table)
                        for desc in target_table.find_all(True):
                            seen_elements.add(desc)
                        seen_elements.add(tag)
                        for desc in tag.find_all(True):
                            seen_elements.add(desc)
                else:
                    if any(m in raw_text for m in term_markers) and any(
                        k in raw_text for k in ["지분", "주주", "보유"]
                    ):
                        evidence.append(
                            f"[DATA-GENERAL-HTML]\n[Section: {current_section}]\n{_get_simplified_html(tag)}"
                        )
                        seen_elements.add(tag)
            else:
                if any(m in raw_text for m in term_markers) and any(
                    k in raw_text for k in ["지분", "주주", "보유"]
                ):
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
