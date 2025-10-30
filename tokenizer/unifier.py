from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional

ENCODINGS = ("utf-8", "utf-8-sig", "cp949", "euc-kr")

DIGITS_PREFIX = re.compile(r"^(\d+)_")

def read_text_with_fallback(p: Path) -> str:
    for enc in ENCODINGS:
        try:
            return p.read_text(encoding=enc, errors="replace")
        except Exception:
            continue
    # last resort
    return p.read_text(encoding="utf-8", errors="replace")

def main() -> None:
    base_dir = Path(__file__).resolve().parent
    after_dir = base_dir / "after"
    out_dir = base_dir / "unified"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not after_dir.is_dir():
        raise SystemExit(f"Not found: {after_dir}")

    # Collect .txt files only (ignore .zip, .csv, etc.)
    txt_files: List[Path] = [p for p in after_dir.iterdir() if p.is_file() and p.suffix.lower() == ".txt"]

    groups: Dict[str, List[Tuple[Optional[int], Path]]] = {}

    for p in txt_files:
        name = p.name
        m = DIGITS_PREFIX.match(name)
        if m:
            # group key is the suffix after the first underscore
            key = name[m.end():]
            num = int(m.group(1))
        else:
            # no leading digits -> group by full filename
            key = name
            num = None
        groups.setdefault(key, []).append((num, p))

    # Build each unified file
    for key, items in groups.items():
        # sort: items with numeric prefix ascending, others by filename
        items.sort(key=lambda x: (0 if x[0] is not None else 1, x[0] if x[0] is not None else x[1].name))

        contents: List[str] = []
        for _, path in items:
            contents.append(read_text_with_fallback(path).rstrip())

        unified_text = ("\n\n").join(contents) + "\n"

        out_path = out_dir / key  # keep the suffix (e.g., "이수앱지스_전환청구권행사_후처리.txt")
        out_path.write_text(unified_text, encoding="utf-8")

    # Optional console summary
    print(f"Unified {len(groups)} group(s) into: {out_dir}")
    for key, items in groups.items():
        print(f"- {key}: {len(items)} file(s)")

if __name__ == "__main__":
    main()