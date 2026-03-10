from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import requests

from zombie import dart_fetcher


def test_load_input_universe_normalizes_codes(tmp_path: Path) -> None:
    csv_path = tmp_path / "tickers.csv"
    csv_path.write_text(
        "market,name,stock_code,corp_code\n"
        "KOSPI,Alpha,1234,001\n"
        "KOSDAQ,Beta,00104K,\n"
        "KONEX,Gamma,999999,003\n",
        encoding="utf-8-sig",
    )

    df = dart_fetcher.load_input_universe(csv_path)

    assert df.to_dict("records") == [
        {"market": "KOSDAQ", "name": "Beta", "stock_code": "00104K", "corp_code": ""},
        {"market": "KOSPI", "name": "Alpha", "stock_code": "001234", "corp_code": "001"},
    ]


def test_resolve_corp_codes_fills_missing_values() -> None:
    universe = pd.DataFrame(
        [
            {"market": "KOSPI", "name": "Alpha", "stock_code": "005930", "corp_code": ""},
            {"market": "KOSDAQ", "name": "Beta", "stock_code": "123456", "corp_code": "00999999"},
            {"market": "KOSDAQ", "name": "Gamma", "stock_code": "654321", "corp_code": ""},
        ]
    )

    class FakeReader:
        def __init__(self, _: str) -> None:
            self.corp_codes = pd.DataFrame(
                [
                    {"stock_code": "005930", "corp_code": "00126380"},
                    {"stock_code": "654321", "corp_code": ""},
                ]
            )

    included, excluded = dart_fetcher.resolve_corp_codes(universe, api_key="test", reader_factory=FakeReader)

    assert included.to_dict("records") == [
        {"market": "KOSPI", "name": "Alpha", "stock_code": "005930", "corp_code": "00126380"},
        {"market": "KOSDAQ", "name": "Beta", "stock_code": "123456", "corp_code": "00999999"},
    ]
    assert excluded.to_dict("records") == [
        {"market": "KOSDAQ", "name": "Gamma", "stock_code": "654321", "corp_code": ""}
    ]


def test_fetch_financial_statement_falls_back_to_ofs() -> None:
    calls: list[tuple[str, int, str]] = []

    class FakeReader:
        def finstate_all(self, corp_code: str, year: int, reprt_code: str, fs_div: str) -> pd.DataFrame:
            calls.append((corp_code, year, fs_div))
            if fs_div == "CFS":
                return pd.DataFrame()
            return pd.DataFrame([{"sj_div": "IS", "account_nm": "영업이익", "thstrm_amount": "10"}])

    result = dart_fetcher.fetch_financial_statement(FakeReader(), "00126380", 2024, request_sleep=0, max_retries=1)

    assert result.fs_div_used == "OFS"
    assert result.source_status == "ok_ofs"
    assert calls == [("00126380", 2024, "CFS"), ("00126380", 2024, "OFS")]


def test_fetch_financial_statement_retries_connection_error() -> None:
    attempts = {"count": 0}

    class FakeReader:
        def finstate_all(self, corp_code: str, year: int, reprt_code: str, fs_div: str) -> pd.DataFrame:
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise requests.exceptions.ConnectionError("dns failed")
            return pd.DataFrame([{"sj_div": "IS", "account_nm": "영업이익", "thstrm_amount": "10"}])

    result = dart_fetcher.fetch_financial_statement(FakeReader(), "00126380", 2024, request_sleep=0, max_retries=2)

    assert result.source_status == "ok_cfs"
    assert attempts["count"] == 2


def test_upsert_rows_keeps_last_record() -> None:
    existing = pd.DataFrame([{"corp_code": "1", "year": 2024, "value": "old"}])
    new = pd.DataFrame([{"corp_code": "1", "year": 2024, "value": "new"}])

    merged = dart_fetcher.upsert_rows(existing, new, ["corp_code", "year"])

    assert merged.to_dict("records") == [{"corp_code": "1", "year": 2024, "value": "new"}]


def test_load_parquet_frame_returns_empty_when_missing(tmp_path: Path) -> None:
    path = tmp_path / "missing.parquet"

    df = dart_fetcher.load_parquet_frame(path, ["corp_code", "year"])

    assert list(df.columns) == ["corp_code", "year"]
    assert df.empty


def test_get_default_api_key_from_local_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    local_file = tmp_path / "corp_list.py"
    local_file.write_text('API_KEY = "test-key"\n', encoding="utf-8")

    monkeypatch.setattr(dart_fetcher, "API_KEY_ENV_VARS", ())
    monkeypatch.setattr(dart_fetcher, "Path", lambda value="": local_file if value == "corp_code_extractor/corp_list.py" else Path(value))

    assert dart_fetcher.get_default_api_key() == "test-key"
