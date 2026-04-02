#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
`dart-fss`와 `OpenDartReader`가 stock_code를 포함한 회사 리스트를 제공하는지 검증하는 테스트 모듈.

참고한 로컬 문서/코드:
- docs/dart_corp.rst: `dart_fss.get_corp_list()`와 `find_by_stock_code()` 예시
- docs/openDartReader_user_guide.md: `corp_codes`, `company_by_name()` 결과에 `stock_code` 포함 예시
- corp_code_extractor/corp_list.py: `corp.stock_code`를 CSV/JSON으로 저장하는 기존 구현
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd

REQUIRED_FIELDS = ("corp_code", "corp_name", "stock_code", "modify_date")
INTEGRATION_FLAG = "RUN_DART_API_TESTS"
API_KEY_ENV_VARS = ("DART_API_KEY", "OPEN_DART_API_KEY", "DART_FSS_API_KEY")


def _load_dart_fss():
    import dart_fss as dart

    return dart


def _load_opendartreader():
    import OpenDartReader

    return OpenDartReader


def _get_default_api_key() -> str:
    for env_var in API_KEY_ENV_VARS:
        value = os.getenv(env_var)
        if value:
            return value

    # 같은 폴더의 기존 스크립트가 이미 사용하는 키를 최후 fallback으로 재사용한다.
    try:
        from corp_code_extractor.corp_list import API_KEY as local_api_key
    except Exception:
        corp_list_path = Path(__file__).with_name("corp_list.py")
        if corp_list_path.exists():
            content = corp_list_path.read_text(encoding="utf-8")
            match = re.search(r'^API_KEY\s*=\s*"([^"]+)"', content, re.MULTILINE)
            if match:
                return match.group(1)
        return ""

    return str(local_api_key)


def _normalize_row(row: dict[str, Any]) -> dict[str, str]:
    return {field: str(row.get(field, "") or "") for field in REQUIRED_FIELDS}


def _assert_rows_have_stock_codes(rows: list[dict[str, str]], source_name: str) -> None:
    assert rows, f"{source_name} returned no listed-company rows"
    assert set(REQUIRED_FIELDS).issubset(rows[0]), (
        f"{source_name} row is missing required fields: {rows[0].keys()}"
    )
    assert any(row["stock_code"] for row in rows), (
        f"{source_name} returned rows but no non-empty stock_code values"
    )


def collect_dart_fss_stock_rows(api_key: str) -> list[dict[str, str]]:
    """docs/dart_corp.rst와 corp_list.py 흐름대로 상장사 리스트를 표준 dict 목록으로 변환한다."""
    dart = _load_dart_fss()
    dart.set_api_key(api_key=api_key)
    corp_list = dart.get_corp_list()

    rows: list[dict[str, str]] = []
    for corp in corp_list.corps:
        if not getattr(corp, "stock_code", ""):
            continue
        rows.append(
            _normalize_row(
                {
                    "corp_code": getattr(corp, "corp_code", ""),
                    "corp_name": getattr(corp, "corp_name", ""),
                    "stock_code": getattr(corp, "stock_code", ""),
                    "modify_date": getattr(corp, "modify_date", ""),
                }
            )
        )
    return rows


def collect_opendartreader_stock_rows(api_key: str) -> list[dict[str, str]]:
    """docs/openDartReader_user_guide.md의 corp_codes 예시대로 종목코드 포함 행만 반환한다."""
    reader_factory = _load_opendartreader()
    reader = reader_factory(api_key)
    frame = reader.corp_codes

    missing = set(REQUIRED_FIELDS).difference(frame.columns)
    if missing:
        raise ValueError(f"OpenDartReader corp_codes is missing columns: {sorted(missing)}")

    listed = frame.loc[
        frame["stock_code"].fillna("").astype(str).str.strip() != "",
        list(REQUIRED_FIELDS),
    ]
    return [_normalize_row(row) for row in listed.to_dict("records")]


def _require_integration_api_key() -> str:
    import pytest

    if os.getenv(INTEGRATION_FLAG) != "1":
        pytest.skip(f"set {INTEGRATION_FLAG}=1 to run live DART API tests")

    api_key = _get_default_api_key()
    if not api_key:
        pytest.skip("no DART API key available for live tests")

    return api_key


def verify_live_sources(api_key: str, sample_size: int = 5) -> dict[str, list[dict[str, str]]]:
    """두 라이브러리에서 stock_code 포함 상장사 목록을 실제로 받아오는지 확인한다."""
    dart_fss_rows = collect_dart_fss_stock_rows(api_key)
    opendartreader_rows = collect_opendartreader_stock_rows(api_key)

    _assert_rows_have_stock_codes(dart_fss_rows, "dart-fss")
    _assert_rows_have_stock_codes(opendartreader_rows, "OpenDartReader")

    return {
        "dart_fss": dart_fss_rows[:sample_size],
        "opendartreader": opendartreader_rows[:sample_size],
    }


def main() -> int:
    api_key = _get_default_api_key()
    if not api_key:
        print(
            "DART API 키를 찾지 못했습니다. "
            "환경변수 `DART_API_KEY`, `OPEN_DART_API_KEY`, `DART_FSS_API_KEY` 중 하나를 설정하세요."
        )
        return 1

    try:
        dart_fss_rows = collect_dart_fss_stock_rows(api_key)
        opendartreader_rows = collect_opendartreader_stock_rows(api_key)
    except Exception as exc:
        print("실 API 호출에 실패했습니다.")
        print(f"error: {exc}")
        print("네트워크/DNS 또는 API 키 상태를 확인하세요.")
        return 1

    print("[dart-fss]")
    print(f"listed rows: {len(dart_fss_rows):,}")
    print(f"sample: {dart_fss_rows[:3]}")
    print()
    print("[OpenDartReader]")
    print(f"listed rows: {len(opendartreader_rows):,}")
    print(f"sample: {opendartreader_rows[:3]}")

    return 0


def test_collect_dart_fss_stock_rows_filters_unlisted_corps(monkeypatch) -> None:
    import pytest

    captured_api_keys: list[str] = []

    class FakeDartModule:
        @staticmethod
        def set_api_key(*, api_key: str) -> None:
            captured_api_keys.append(api_key)

        @staticmethod
        def get_corp_list() -> SimpleNamespace:
            corps = [
                SimpleNamespace(
                    corp_code="00126380",
                    corp_name="삼성전자",
                    stock_code="005930",
                    modify_date="20240229",
                ),
                SimpleNamespace(
                    corp_code="00366997",
                    corp_name="삼성전자로지텍",
                    stock_code="",
                    modify_date="20240229",
                ),
            ]
            return SimpleNamespace(corps=corps)

    monkeypatch.setattr(
        sys.modules[__name__],
        "_load_dart_fss",
        lambda: FakeDartModule,
    )

    rows = collect_dart_fss_stock_rows("test-api-key")

    assert captured_api_keys == ["test-api-key"]
    assert rows == [
        {
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "stock_code": "005930",
            "modify_date": "20240229",
        }
    ]


def test_collect_opendartreader_stock_rows_validates_required_columns(
    monkeypatch,
) -> None:
    import pytest

    class FakeReader:
        def __init__(self, _: str) -> None:
            self.corp_codes = pd.DataFrame(
                [{"corp_code": "00126380", "corp_name": "삼성전자", "modify_date": "20240229"}]
            )

    monkeypatch.setattr(
        sys.modules[__name__],
        "_load_opendartreader",
        lambda: FakeReader,
    )

    with pytest.raises(ValueError, match="stock_code"):
        collect_opendartreader_stock_rows("test-api-key")


def test_collect_opendartreader_stock_rows_returns_listed_rows_only(
    monkeypatch,
) -> None:
    class FakeReader:
        def __init__(self, _: str) -> None:
            self.corp_codes = pd.DataFrame(
                [
                    {
                        "corp_code": "00126380",
                        "corp_name": "삼성전자",
                        "stock_code": "005930",
                        "modify_date": "20240229",
                    },
                    {
                        "corp_code": "00366997",
                        "corp_name": "삼성전자로지텍",
                        "stock_code": "",
                        "modify_date": "20240229",
                    },
                ]
            )

    monkeypatch.setattr(
        sys.modules[__name__],
        "_load_opendartreader",
        lambda: FakeReader,
    )

    rows = collect_opendartreader_stock_rows("test-api-key")

    assert rows == [
        {
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "stock_code": "005930",
            "modify_date": "20240229",
        }
    ]


def test_dart_fss_returns_stock_code_rows_integration() -> None:
    api_key = _require_integration_api_key()
    rows = collect_dart_fss_stock_rows(api_key)
    _assert_rows_have_stock_codes(rows, "dart-fss")


def test_opendartreader_returns_stock_code_rows_integration() -> None:
    api_key = _require_integration_api_key()
    rows = collect_opendartreader_stock_rows(api_key)
    _assert_rows_have_stock_codes(rows, "OpenDartReader")


if __name__ == "__main__":
    raise SystemExit(main())
