import re
from typing import Dict

from bs4 import BeautifulSoup, Tag


def _normalize(text: str) -> str:
    """텍스트 정규화: 특수 공백 제거 및 연속 공백 정리, 불필요한 문장 컷팅"""
    if not text:
        return ""
    # 불필요한 기호 및 과도한 줄바꿈 정리
    text = text.replace("\xa0", " ").replace("\r", " ")
    cleaned = " ".join(text.split())
    # 너무 긴 문장은 핵심 정보가 아닐 가능성이 높으므로 제한
    return cleaned[:450] + "..." if len(cleaned) > 500 else cleaned


def _table_to_compact(table_tag: Tag) -> str:
    """
    병합된 셀(Span)을 인식하여 2차원 그리드 구조를 유지하는 가벼운 테이블 변환기.
    HTML 태그 없이도 열(Column) 정렬이 깨지지 않게 보정하여 LLM의 인식 오류를 방지함.
    """
    grid = {}
    rows = table_tag.find_all("tr")
    if not rows:
        return ""

    for r_idx, tr in enumerate(rows):
        c_idx = 0
        for td in tr.find_all(["td", "th"]):
            # 이미 다른 cell의 rowspan에 의해 점유된 칸은 건너뛰기
            while (r_idx, c_idx) in grid:
                c_idx += 1

            content = _normalize(td.get_text())
            rs = int(td.get("rowspan", 1))
            cs = int(td.get("colspan", 1))

            # 2차원 그리드에 셀 내용 배치
            for r in range(r_idx, r_idx + rs):
                for c in range(c_idx, c_idx + cs):
                    if r == r_idx and c == c_idx:
                        grid[(r, c)] = content
                    else:
                        grid[(r, c)] = ""  # 병합된 영역은 빈 칸으로 처리
            c_idx += cs

    # 그리드 데이터를 파이프(|) 형식 문자열로 변환
    if not grid:
        return ""
    max_c = max(c for r, c in grid.keys()) + 1
    compact_rows = []
    for r in range(len(rows)):
        row_cells = [grid.get((r, c), "") for c in range(max_c)]
        if any(row_cells):
            compact_rows.append("| " + " | ".join(row_cells) + " |")

    return "\n".join(compact_rows)


def _extract_global_meta(soup: BeautifulSoup) -> Dict[str, str]:
    """문서 전체에서 공통 메타데이터(단위, 통화, 기준일)를 추출"""
    text = soup.get_text()
    meta = {}

    # 단위 추출 (예: 단위: 천원, 단위: EUR, (단위: EUR))
    unit_match = re.search(r"단위[:\s]*([가-힣a-zA-Z]+)", text)
    if unit_match:
        meta["unit"] = unit_match.group(1)

    # 기준일 추출 (예: 2024년 12월 31일 현재)
    date_match = re.search(r"(\d{4}년\s*\d{1,2}월\s*\d{1,2}일)\s*현재", text)
    if date_match:
        meta["as_of_date"] = date_match.group(1)

    return meta


def _get_company_name(soup: BeautifulSoup) -> str:
    """공시 본문에서 회사명 추출"""
    for tag in soup.find_all(["td", "p", "h1", "h2"]):
        text = tag.get_text(strip=True)
        if "주식회사" in text:
            match = re.search(
                r"([가-힣a-zA-Z0-9]+주식회사|주식회사\s*[가-힣a-zA-Z0-9]+)", text
            )
            if match:
                return match.group(0).strip()
    return "Unknown"


def extract_evidence_blocks(soup: BeautifulSoup) -> str:
    """
    최적화된 증거 블록 추출기: 메타데이터 분리 + 테이블 압축 + 노이즈 제거
    """
    company_name = _get_company_name(soup)
    global_meta = _extract_global_meta(soup)
    keywords = ["지분율", "주요 주주", "타법인 출자", "1. 일반사항", "1. 회사의 개요"]

    # 1. 문서 헤더 작성 (메타데이터 요약)
    header = [
        "[META]",
        f"Company: {company_name}",
        f"Unit: {global_meta.get('unit', 'Unknown')}",
        f"Date: {global_meta.get('as_of_date', 'Unknown')}",
    ]

    evidence = ["\n".join(header)]
    seen_texts = set()
    seen_elements = set()

    # 분석 대상 태그: table, p, div, h1-h4
    for tag in soup.find_all(["table", "p", "div", "h1", "h2", "h3", "h4"]):
        if tag in seen_elements:
            continue

        text = _normalize(tag.get_text())
        if not text or len(text) < 5:  # 너무 짧은 노이즈 제거
            continue

        # 키워드 매칭 및 중복 텍스트 제거
        if any(kw in text for kw in keywords) and text not in seen_texts:
            block_content = []

            # 주위 문맥(Context) 추가 (앞의 1개 요소)
            prev = tag.find_previous_sibling()
            if prev and prev not in seen_elements:
                p_text = _normalize(prev.get_text())
                if p_text and p_text not in seen_texts:
                    content = (
                        _table_to_compact(prev) if prev.name == "table" else p_text
                    )
                    block_content.append(content)
                    seen_elements.add(prev)
                    seen_texts.add(p_text)

            # 본문(Anchor) 추가
            if tag.name == "table":
                compact_table = _table_to_compact(tag)
                if compact_table:
                    block_content.append(compact_table)
            else:
                block_content.append(text)

            seen_texts.add(text)
            seen_elements.add(tag)

            # 이후 문맥(Context) 추가 (뒤의 1개 요소)
            nxt = tag.find_next_sibling()
            if nxt and nxt not in seen_elements:
                n_text = _normalize(nxt.get_text())
                if n_text and n_text not in seen_texts:
                    content = _table_to_compact(nxt) if nxt.name == "table" else n_text
                    block_content.append(content)
                    seen_elements.add(nxt)
                    seen_texts.add(n_text)

            evidence.append("[DATA]\n" + "\n".join(block_content))

    return "\n\n---\n\n".join(evidence)


if __name__ == "__main__":
    from pathlib import Path

    # 하드코딩된 테스트 파일 경로
    test_file = Path(__file__).resolve().parent / "sample" / "sample.html"

    if not test_file.exists():
        print(f"Error: {test_file} 파일을 찾을 수 없습니다.")
    else:
        print(f"--- 최적화 테스트 시작: {test_file.name} ---")
        content = test_file.read_text(encoding="utf-8")
        soup = BeautifulSoup(content, "html.parser")

        result = extract_evidence_blocks(soup)
        print(result)
        print("\n--- 테스트 종료 ---")
