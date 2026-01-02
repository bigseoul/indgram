import argparse
import json
import re
import copy
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

def _parse_args():
    parser = argparse.ArgumentParser(description="Extract tables with cleaned HTML for LLM efficiency.")
    default_source = Path(__file__).resolve().parent / "kpartners.html"
    parser.add_argument("--source", type=Path, default=default_source)
    parser.add_argument("--context-keyword", dest="context_keywords", action="append",
                        default=["당기", "당기말", "현재", "대주주", "주주구성"])
    parser.add_argument("--table-keyword", default="지분율")
    return parser.parse_args()

def _normalize(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())

def _keyword_in_text(text: str, keyword: str) -> bool:
    clean = lambda t: re.sub(r"\s+", "", t.replace("\xa0", ""))
    return clean(keyword) in clean(text)

def _get_company_name(soup) -> str:
    for td in soup.find_all("td"):
        text = td.get_text(strip=True)
        if "주식회사" in text:
            name = text.replace("주식회사", "").strip()
            if name: return name
    return "Unknown"

def _clean_table_html(table_tag) -> str:
    """디자인 속성을 제거하고 rowspan, colspan만 남겨 토큰 효율을 극대화함"""
    table_copy = copy.deepcopy(table_tag)
    for tag in table_copy.find_all(True):
        # rowspan, colspan만 유지하고 나머지 모든 속성 삭제
        allowed_attrs = {k: v for k, v in tag.attrs.items() if k in ['rowspan', 'colspan']}
        tag.attrs = allowed_attrs
    
    # 가독성을 해치지 않는 선에서 태그 사이 공백 제거 (토큰 절약)
    cleaned_html = str(table_copy)
    cleaned_html = re.sub(r'>\s+<', '><', cleaned_html)
    return cleaned_html.strip()

def _table_to_data(table) -> tuple[list[str], list[list[str]]]:
    rows = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if cells:
            rows.append([_normalize(cell.get_text(" ", strip=True)) for cell in cells])
    return (rows[0], rows[1:]) if rows else ([], [])

def _previous_context(table, keywords) -> str:
    candidates = table.find_all_previous(["p", "td", "th", "div"], limit=40)
    for element in candidates:
        text = _normalize(element.get_text(" ", strip=True))
        if text and any(_keyword_in_text(text, kw) for kw in keywords):
            return text
    return ""

def main():
    args = _parse_args()
    if not args.source.exists():
        raise SystemExit(f"Source not found: {args.source}")

    soup = BeautifulSoup(args.source.read_text(encoding="utf-8"), "html.parser")
    company = _get_company_name(soup)
    extracted_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    context_keywords = [w.strip() for w in args.context_keywords if w.strip()]

    matches = []
    for table in soup.find_all("table"):
        context = _previous_context(table, context_keywords)
        # 테이블 및 컨텍스트 키워드 검증
        if not any(_keyword_in_text(context, kw) for kw in context_keywords): continue
        if not _keyword_in_text(_normalize(table.get_text(" ", strip=True)), args.table_keyword): continue

        headers, rows = _table_to_data(table)
        
        matches.append({
            "source_type": "audit_comment",
            "company": company,
            "document_id": args.source.name,
            "extracted_at": extracted_at,
            "context": context,
            "table": {
                "table_type": "shareholders",
                "headers": headers,
                "rows": rows,
            },
            "raw": {
                "text": "\n".join([" | ".join(r) for r in [headers] + rows]),
                "html": _clean_table_html(table)
            },
            "schema_version": 1
        })

    if not matches: return print("No matches found.")
    print(json.dumps(matches if len(matches) > 1 else matches[0], ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
