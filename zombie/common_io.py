from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import pandas as pd

DEFAULT_INPUT_PATH = Path("zombie/data/market_tickers_with_corp_code.csv")
DEFAULT_MARKETS = ("KOSPI", "KOSDAQ")
INPUT_COLUMNS = ("market", "name", "stock_code", "corp_code")


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
