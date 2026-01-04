import re
import sys
from pathlib import Path
from typing import Dict

from bs4 import BeautifulSoup


def _get_simplified_html(tag) -> str:
    """
    태그의 모든 속성(style, class 등)을 제거하고
    핵심 구조와 텍스트만 남긴 HTML 문자열을 반환합니다.
    """
    from bs4 import NavigableString, Tag

    if isinstance(tag, NavigableString):
        return str(tag).strip()

    if not isinstance(tag, Tag):
        return ""

    # 자식 노드들을 먼저 단순화
    inner_html = "".join(_get_simplified_html(child) for child in tag.children).strip()

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
    HTML 원본 추출기:
    1. 일반 사항 키워드: 문맥 유지 (태그 원본 포함)
    2. 데이터 키워드: 오직 '지분율' 테이블만 원본으로 추출
    """
    company_name = _get_company_name(soup)
    global_meta = _extract_global_meta(soup)

    general_keywords = ["1. 일반사항", "1. 회사의 개요", "1. 일반적인 사항"]
    data_keywords = ["지분율", "종속", "관계"]
    term_markers = ["당기", "당기말", "당기 말", "현재"]
    exclude_keywords = ["비지배지분율", "비지배지분"]

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
    while idx < len(all_tags):
        tag = all_tags[idx]
        if tag in seen_elements:
            idx += 1
            continue

        raw_text = tag.get_text().strip()
        if not raw_text:
            idx += 1
            continue

        # (*1), (주1) 등으로 시작하는 주석 설명문 제외 (시점 정보는 숫자가 바로 붙지 않으므로 안전)
        if re.match(r"^\s*[\(\{\[]?[\*주]\d+", raw_text):
            seen_elements.add(tag)
            idx += 1
            continue

        # 1. 일반적인 사항: 특정 섹션 전체 추출
        if any(gk in raw_text for gk in general_keywords):
            block_content = []
            curr_idx = idx
            count = 0
            while curr_idx < len(all_tags) and count < 15:
                t = all_tags[curr_idx]
                if count > 0 and t.name in ["h1", "h2", "h3"]:
                    break
                if t not in seen_elements:
                    # 주석 패턴 재확인
                    if not re.match(r"^\s*[\(\{\[]?[\*주]\d+", t.get_text().strip()):
                        block_content.append(_get_simplified_html(t))
                        seen_elements.add(t)
                        # 자식 요소들도 seen_elements에 추가
                        if hasattr(t, "find_all"):
                            for desc in t.find_all(True):
                                seen_elements.add(desc)
                curr_idx += 1
                count += 1
            if block_content:
                evidence.append("[DATA-GENERAL-HTML]\n" + "\n".join(block_content))
            idx = curr_idx
            continue

        # 2. '지분율' 키워드: 테이블 위주로 탐색
        elif any(kw in raw_text for kw in data_keywords):
            # 앵커 태그가 너무 길면 무시하되, div나 table은 내부 검색을 위해 허용
            if len(raw_text) > 500 and tag.name not in ["table", "div"]:
                idx += 1
                continue

            target_table = None
            if tag.name == "table":
                target_table = tag
            else:
                # 다음 10개 노드 내에서 테이블 탐색
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

                # '지분율' 단어가 테이블 내부에 있어야 함
                if "지분율" in table_text and not any(
                    ek in table_text for ek in exclude_keywords
                ):
                    # 시점 판별 및 컨텍스트 수집: 테이블 위쪽 10개 노드 내에 시점 마커가 있는지 확인
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

                        # (당기말), (전기말), (단위:) 등을 포함한 메타데이터성 태그 혹은 설명 단락 추가
                        is_marker = any(
                            m in node_text for m in term_markers + ["(단위"]
                        )
                        is_metadata_node = p_node.name == "table" or (
                            p_node.name == "p" and len(node_text) < 200
                        )

                        if is_marker or is_metadata_node:
                            term_context_tags.insert(0, _get_simplified_html(p_node))
                        search_curr = p_node

                    # 테이블 헤더 자체에서도 시점 마커 확인 (상위 3줄까지 확인)
                    header_text = (
                        target_table.thead.get_text() if target_table.thead else ""
                    )
                    if not header_text:
                        # thead가 없는 경우 상위 3개의 tr을 합쳐서 확인
                        header_rows = target_table.find_all("tr")[:3]
                        header_text = " ".join(r.get_text() for r in header_rows)

                    if any(m in term_context_text for m in term_markers) or any(
                        m in header_text for m in term_markers
                    ):
                        # Anchor 텍스트 정제
                        clean_anchor = re.sub(r"\s+", " ", raw_text[:150]).strip()
                        title_info = f"<p><b>[Anchor]</b> {clean_anchor}</p>"
                        context_html = "\n".join(term_context_tags)
                        evidence.append(
                            f"[DATA-TABLE-HTML]\n{title_info}\n{context_html}\n{_get_simplified_html(target_table)}"
                        )

                        # 타겟 테이블과 앵커 태그, 그리고 그 자식들을 모두 seen 처리
                        seen_elements.add(target_table)
                        for desc in target_table.find_all(True):
                            seen_elements.add(desc)
                        seen_elements.add(tag)
                        for desc in tag.find_all(True):
                            seen_elements.add(desc)

        idx += 1

    return "\n\n---\n\n".join(evidence)


if __name__ == "__main__":
    # 텍스트 카운터 모듈 경로 추가
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent / "tokenizer"))
    try:
        from token_counter import count_tokens_from_text, count_tokens_gemini
    except ImportError:
        count_tokens_from_text = None
        count_tokens_gemini = None

    test_file = Path(__file__).resolve().parent / "sample" / "투믹스홀딩스.html"
    if not test_file.exists():
        print(f"Error: {test_file} 파일을 찾을 수 없습니다.")
    else:
        content = test_file.read_text(encoding="utf-8")
        soup = BeautifulSoup(content, "html.parser")
        result = extract_evidence_blocks(soup)
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
