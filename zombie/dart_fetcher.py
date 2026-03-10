from __future__ import annotations

import contextlib
import io
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

import pandas as pd
import requests

DEFAULT_INPUT_PATH = Path("zombie/data/market_tickers_with_corp_code.csv")
DEFAULT_CHECKPOINT_DIR = Path("zombie/data/checkpoints")
DEFAULT_PROGRESS_PATH = DEFAULT_CHECKPOINT_DIR / "fetch_progress.parquet"
DEFAULT_ERROR_PATH = DEFAULT_CHECKPOINT_DIR / "fetch_errors.parquet"
DEFAULT_RAW_PARQUET_PATH = DEFAULT_CHECKPOINT_DIR / "icr_extract_2022_2024_long.parquet"
DEFAULT_MARKETS = ("KOSPI", "KOSDAQ")
DEFAULT_YEARS = (2022, 2023, 2024)
REPORT_CODE = "11011"
API_KEY_ENV_VARS = ("DART_API_KEY", "OPEN_DART_API_KEY", "DART_FSS_API_KEY")

INPUT_COLUMNS = ("market", "name", "stock_code", "corp_code")
PROGRESS_COLUMNS = (
    "market",
    "stock_code",
    "corp_code",
    "name",
    "year",
    "report_code",
    "fs_div_used",
    "source_status",
    "processed_at",
)
ERROR_COLUMNS = (
    "market",
    "stock_code",
    "corp_code",
    "name",
    "year",
    "report_code",
    "error_type",
    "error_message",
    "processed_at",
)


@dataclass(frozen=True)
class FetchResult:
    frame: pd.DataFrame
    fs_div_used: str
    source_status: str


def _load_opendartreader():
    import OpenDartReader

    return OpenDartReader


def get_default_api_key() -> str:
    for env_var in API_KEY_ENV_VARS:
        value = os.getenv(env_var)
        if value:
            return value

    corp_list_path = Path("corp_code_extractor/corp_list.py")
    if not corp_list_path.exists():
        return ""

    content = corp_list_path.read_text(encoding="utf-8")
    match = re.search(r'^API_KEY\s*=\s*"([^"]+)"', content, re.MULTILINE)
    return match.group(1) if match else ""


def normalize_stock_code(value: Any) -> str:
    text = str(value or "").strip().upper()
    if not text:
        return ""
    return text.zfill(6) if len(text) < 6 else text


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return bool(pd.isna(value))


def utc_now() -> str:
    return pd.Timestamp.utcnow().isoformat()


def load_input_universe(input_path: str | Path = DEFAULT_INPUT_PATH) -> pd.DataFrame:
    path = Path(input_path)
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")

    missing = set(INPUT_COLUMNS).difference(df.columns)
    if missing:
        raise ValueError(f"input CSV is missing columns: {sorted(missing)}")

    df = df.loc[df["market"].isin(DEFAULT_MARKETS), list(INPUT_COLUMNS)].copy()
    df["stock_code"] = df["stock_code"].map(normalize_stock_code)
    df["corp_code"] = df["corp_code"].fillna("").astype(str).str.strip()
    df["name"] = df["name"].fillna("").astype(str).str.strip()
    return df.sort_values(["market", "stock_code"]).reset_index(drop=True)


def load_corp_codes_frame(
    api_key: str,
    reader_factory: Callable[[str], Any] | None = None,
) -> pd.DataFrame:
    reader_cls = reader_factory or _load_opendartreader()
    reader = reader_cls(api_key)
    frame = reader.corp_codes.copy()
    required = {"corp_code", "stock_code"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"corp_codes is missing columns: {sorted(missing)}")
    frame["stock_code"] = frame["stock_code"].map(normalize_stock_code)
    frame["corp_code"] = frame["corp_code"].fillna("").astype(str).str.strip()
    listed = frame.loc[(frame["stock_code"] != "") & (frame["corp_code"] != ""), ["stock_code", "corp_code"]]
    return listed.drop_duplicates(subset=["stock_code"], keep="first").reset_index(drop=True)


def resolve_corp_codes(
    universe_df: pd.DataFrame,
    api_key: str,
    reader_factory: Callable[[str], Any] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    mapping_frame = load_corp_codes_frame(api_key, reader_factory=reader_factory)
    stock_to_corp = dict(mapping_frame.itertuples(index=False, name=None))

    resolved = universe_df.copy()
    missing_mask = resolved["corp_code"].eq("")
    resolved.loc[missing_mask, "corp_code"] = resolved.loc[missing_mask, "stock_code"].map(stock_to_corp).fillna("")

    included = resolved.loc[resolved["corp_code"] != ""].copy()
    excluded = resolved.loc[resolved["corp_code"] == ""].copy()
    return included.reset_index(drop=True), excluded.reset_index(drop=True)


def build_reader(api_key: str):
    return _load_opendartreader()(api_key)


def is_retryable_exception(exc: Exception) -> bool:
    if isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
        return True
    if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
        return exc.response.status_code in {429, 500, 502, 503, 504}
    return False


def _call_finstate_all(reader: Any, corp_code: str, year: int, fs_div: str) -> pd.DataFrame:
    with contextlib.redirect_stdout(io.StringIO()):
        frame = reader.finstate_all(corp_code, int(year), reprt_code=REPORT_CODE, fs_div=fs_div)
    if frame is None:
        return pd.DataFrame()
    return frame.copy()


def fetch_financial_statement(
    reader: Any,
    corp_code: str,
    year: int,
    request_sleep: float = 0.1,
    max_retries: int = 4,
) -> FetchResult:
    for fs_div, status in (("CFS", "ok_cfs"), ("OFS", "ok_ofs")):
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                frame = _call_finstate_all(reader, corp_code, year, fs_div)
                if request_sleep > 0:
                    time.sleep(request_sleep)
                if not frame.empty:
                    return FetchResult(frame=frame, fs_div_used=fs_div, source_status=status)
                break
            except Exception as exc:
                last_error = exc
                if not is_retryable_exception(exc) or attempt == max_retries - 1:
                    raise
                time.sleep(min(2**attempt, 8))
        if last_error is not None:
            raise last_error
    return FetchResult(frame=pd.DataFrame(), fs_div_used="", source_status="missing_statement")


def empty_progress_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=PROGRESS_COLUMNS)


def empty_error_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=ERROR_COLUMNS)


def ensure_parent(path: str | Path) -> Path:
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    return path_obj


def load_parquet_frame(path: str | Path, columns: Iterable[str]) -> pd.DataFrame:
    path_obj = Path(path)
    if not path_obj.exists():
        return pd.DataFrame(columns=list(columns))

    df = pd.read_parquet(path_obj)
    for column in columns:
        if column not in df.columns:
            df[column] = pd.NA
    return df[list(columns)].copy()


def save_parquet_frame(df: pd.DataFrame, path: str | Path) -> Path:
    path_obj = ensure_parent(path)
    df.to_parquet(path_obj, index=False)
    return path_obj


def upsert_rows(existing_df: pd.DataFrame, row_df: pd.DataFrame, key_columns: list[str]) -> pd.DataFrame:
    if existing_df.empty:
        return row_df.drop_duplicates(subset=key_columns, keep="last").reset_index(drop=True)
    combined = pd.concat([existing_df, row_df], ignore_index=True)
    return combined.drop_duplicates(subset=key_columns, keep="last").reset_index(drop=True)
