from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

try:
    from bs4 import BeautifulSoup  # type: ignore
except ImportError as exc:  # pragma: no cover - handled at runtime
    BeautifulSoup = None  # type: ignore
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


def _require_bs4() -> None:
    if BeautifulSoup is None:
        raise SystemExit(
            "beautifulsoup4 is required. Install it with `pip install beautifulsoup4`."
        ) from _IMPORT_ERROR


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract tables whose previous context contains a keyword."
    )
    default_source = Path(__file__).resolve().parent / "kpartners.html"
    parser.add_argument(
        "--source",
        type=Path,
        default=default_source,
        help=f"HTML source file (default: {default_source})",
    )
    parser.add_argument(
        "--context-keyword",
        dest="context_keywords",
        action="append",
        default=["당기", "당기말", "현재", "대주주", "주주구성"],
        help=(
            "Keyword that must appear in the previous text context. "
            "Repeat the option to add more keywords."
        ),
    )
    parser.add_argument(
        "--no-require-context",
        action="store_true",
        help="Disable the context keyword requirement.",
    )
    parser.add_argument(
        "--table-keyword",
        default="지분율",
        help="Keyword that must appear inside the table.",
    )
    return parser.parse_args()


def _normalize(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def _squeeze_for_match(text: str) -> str:
    # Remove all whitespace (including nbsp) to make matching robust.
    return re.sub(r"\s+", "", text.replace("\xa0", ""))


def _keyword_in_text(text: str, keyword: str) -> bool:
    normalized_text = _squeeze_for_match(text)
    normalized_keyword = _squeeze_for_match(keyword)
    return normalized_keyword in normalized_text


def _keywords_in_text(text: str, keywords: list[str]) -> bool:
    return any(_keyword_in_text(text, keyword) for keyword in keywords)


def _first_meaningful_text(elements: Iterable) -> str:
    for element in elements:
        text = _normalize(element.get_text(" ", strip=True))
        if text:
            return text
    return ""


def _previous_context(table, keywords: list[str]) -> str:
    # Walk backwards to find the nearest text block containing the keyword.
    candidates = table.find_all_previous(["p", "td", "th", "div"], limit=40)
    for element in candidates:
        text = _normalize(element.get_text(" ", strip=True))
        if text and _keywords_in_text(text, keywords):
            return text
    return _first_meaningful_text(candidates)


def _nearest_period_marker(table) -> str | None:
    # Prefer the closest explicit (당기말)/(전기말) marker above the table.
    candidates = table.find_all_previous(["table", "p", "td", "th", "div"], limit=40)
    for element in candidates:
        text = _normalize(element.get_text(" ", strip=True))
        if not text:
            continue
        has_current = _keyword_in_text(text, "당기말")
        has_prior = _keyword_in_text(text, "전기말")
        if has_current and has_prior:
            # This is a generic header (e.g., "당기말과 전기말"), keep searching.
            continue
        if has_current:
            return "당기말"
        if has_prior:
            return "전기말"
    return None


def _table_to_tsv(table) -> list[str]:
    lines: list[str] = []
    for row in table.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if not cells:
            continue
        values = [_normalize(cell.get_text(" ", strip=True)) for cell in cells]
        lines.append("\t".join(values))
    return lines


def main() -> None:
    _require_bs4()
    args = _parse_args()
    if not args.source.exists():
        raise SystemExit(f"Source file not found: {args.source}")

    html = args.source.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    matches = []
    for table in soup.find_all("table"):
        context_keywords = [word.strip() for word in args.context_keywords if word.strip()]
        context = _previous_context(table, context_keywords)
        if not args.no_require_context:
            if not _keywords_in_text(context, context_keywords):
                continue
            marker = _nearest_period_marker(table)
            if marker and marker not in context_keywords:
                continue
        table_text = _normalize(table.get_text(" ", strip=True))
        if not _keyword_in_text(table_text, args.table_keyword):
            continue
        matches.append((context, table))

    for index, (context, table) in enumerate(matches, start=1):
        print(f"[table {index}] context: {context}")
        print("\n".join(_table_to_tsv(table)))
        print("")

    print(
        f"Matched {len(matches)} table(s) with context keywords {context_keywords} "
        f"and table keyword '{args.table_keyword}'."
    )


if __name__ == "__main__":
    main()
