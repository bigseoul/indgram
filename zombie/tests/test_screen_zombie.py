from __future__ import annotations

from pathlib import Path

import pandas as pd

from zombie.screen_zombie import export_csv


def test_export_csv_writes_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "output.csv"
    export_csv(pd.DataFrame([{"a": 1}]), path)

    data = path.read_bytes()
    assert data.startswith(b"\xef\xbb\xbf")
