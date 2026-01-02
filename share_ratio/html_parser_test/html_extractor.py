import copy
import re

from bs4 import BeautifulSoup, Tag


def _normalize(text: str) -> str:
    """텍스트 정규화: 특수 공백 제거 및 연속 공백 정리"""
    if not text:
        return ""
    return " ".join(text.replace("\xa0", " ").split())


def _clean_table_html(table_tag: Tag) -> str:
    """테이블에서 디자인 속성을 제거하고 구조(rowspan, colspan)만 남김"""
    table_copy = copy.deepcopy(table_tag)
    for tag in table_copy.find_all(True):
        allowed_attrs = {
            k: v for k, v in tag.attrs.items() if k in ["rowspan", "colspan"]
        }
        tag.attrs = allowed_attrs
    cleaned_html = str(table_copy)
    cleaned_html = re.sub(r">\s+<", "><", cleaned_html)
    return cleaned_html.strip()


def _get_company_name(soup: BeautifulSoup) -> str:
    """공시 본문에서 회사명 추출"""
    for td in soup.find_all(["td", "p"]):
        text = td.get_text(strip=True)
        if "주식회사" in text:
            match = re.search(
                r"([가-힣a-zA-Z0-9]+주식회사|주식회사\s*[가-힣a-zA-Z0-9]+)", text
            )
            if match:
                return match.group(0).strip()
    return "Unknown"


def extract_evidence_blocks(soup: BeautifulSoup) -> str:
    """
    지분율과 관련된 평문(P, DIV 등) 및 테이블(TABLE)을 추출하여
    LLM에 전달할 최적화된 '증거 블록'을 생성함.
    날짜, 단위 등 주변 문맥(Context)을 포함하도록 개선됨.
    """
    company_name = _get_company_name(soup)
    keywords = ["지분율", "주주명"]
    evidence = [f"[COMPANY NAME]\n{company_name}"]
    seen_elements = set()

    for tag in soup.find_all(True):
        if tag in seen_elements:
            continue

        # 분석 대상 태그: table, p, div, span, h1-h4, tr 등
        if tag.name not in ["table", "p", "div", "span", "h1", "h2", "h3", "h4", "tr"]:
            continue

        text = _normalize(tag.get_text())
        if any(kw in text for kw in keywords):
            block_content = []

            # 1. 이전 문맥 추출 (최대 3개의 형제 요소를 확인하여 날짜/단위 등 확보)
            prev_siblings = list(tag.find_previous_siblings(limit=3))
            for s in reversed(prev_siblings):
                if s in seen_elements:
                    continue
                if s.name == "table":
                    block_content.append(_clean_table_html(s))
                else:
                    s_text = _normalize(s.get_text())
                    if s_text:
                        block_content.append(s_text)
                seen_elements.add(s)
                for child in s.find_all(True):
                    seen_elements.add(child)

            # 2. 본문(Anchor) 추가
            if tag.name == "table":
                block_content.append(_clean_table_html(tag))
            else:
                block_content.append(text)

            seen_elements.add(tag)
            for child in tag.find_all(True):
                seen_elements.add(child)

            # 3. 이후 문맥 추출 (최대 2개의 형제 요소)
            next_siblings = list(tag.find_next_siblings(limit=2))
            for s in next_siblings:
                if s in seen_elements:
                    continue
                # 다음 요소에 이미 키워드가 있다면 여기서 끊고 다음 루프에서 처리
                s_text = _normalize(s.get_text())
                if any(kw in s_text for kw in keywords):
                    break

                if s.name == "table":
                    block_content.append(_clean_table_html(s))
                else:
                    if s_text:
                        block_content.append(s_text)
                seen_elements.add(s)
                for child in s.find_all(True):
                    seen_elements.add(child)

            block_label = (
                "[TABLE DATA BLOCK]" if tag.name == "table" else "[TEXT BLOCK]"
            )
            evidence.append(f"{block_label}\n" + "\n".join(block_content))

    return "\n\n---\n\n".join(evidence)


if __name__ == "__main__":
    from pathlib import Path

    # 하드코딩된 테스트 파일 경로
    test_file = Path(__file__).resolve().parent / "kpartners.html"

    if not test_file.exists():
        print(f"Error: {test_file} 파일을 찾을 수 없습니다.")
    else:
        print(f"--- 독립 테스트 시작: {test_file.name} ---")
        content = test_file.read_text(encoding="utf-8")
        soup = BeautifulSoup(content, "html.parser")

        result = extract_evidence_blocks(soup)
        print(result)
        print("\n--- 테스트 종료 ---")
