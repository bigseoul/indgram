from __future__ import annotations

import argparse
import copy
from pathlib import Path

try:
    from bs4 import BeautifulSoup  # type: ignore
except ImportError as exc:  # pragma: no cover - handled at runtime
    BeautifulSoup = None  # type: ignore
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract tables containing a keyword from an HTML document."
    )
    default_source = Path(__file__).resolve().parent / "before" / "creoSG.html"
    default_target = Path(__file__).resolve().parent / "after"
    parser.add_argument(
        "--source",
        type=Path,
        default=default_source,
        help=f"HTML source file (default: {default_source})",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=default_target,
        help=f"Directory to store the filtered HTML (default: {default_target})",
    )
    parser.add_argument(
        "--keyword",
        dest="keywords",
        action="append",
        default=["지분율", "법인등록번호"],
        help=(
            "Keyword that must appear inside a table to keep it. "
            "Repeat the option to add more keywords. "
            "Defaults to both '지분율' and '법인등록번호'."
        ),
    )
    parser.add_argument(
        "--output-name",
        help="Optional output filename; defaults to the source filename.",
    )
    return parser.parse_args()


def _require_bs4() -> None:
    if BeautifulSoup is None:
        raise SystemExit(
            "beautifulsoup4 is required. Install it with `pip install beautifulsoup4`."
        ) from _IMPORT_ERROR


def _load_soup(source: Path) -> BeautifulSoup:
    _require_bs4()
    html = source.read_text(encoding="utf-8")
    return BeautifulSoup(html, "html.parser")


def _filter_tables(soup: BeautifulSoup, keywords: list[str]) -> list:
    words = [word.strip() for word in keywords if word and word.strip()]
    if not words:
        return []
    # Keep tables whose text includes any of the keywords.
    return [
        table
        for table in soup.find_all("table")
        if any(word in table.get_text() for word in words)
    ]


def _build_document(tables: list) -> BeautifulSoup:
    _require_bs4()
    template = "<html><head><meta charset='utf-8'></head><body></body></html>"
    result = BeautifulSoup(template, "html.parser")
    for table in tables:
        result.body.append(copy.deepcopy(table))
    return result


def main() -> None:
    args = _parse_args()
    if not args.source.exists():
        raise SystemExit(f"Source file not found: {args.source}")

    soup = _load_soup(args.source)
    tables = _filter_tables(soup, args.keywords)
    result = _build_document(tables)

    target_dir: Path = args.target_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_name or args.source.name
    output_path = target_dir / output_name
    output_path.write_text(result.prettify(), encoding="utf-8")
    print(
        f"Extracted {len(tables)} table(s) containing {args.keywords} -> {output_path}"
    )


if __name__ == "__main__":
    main()
