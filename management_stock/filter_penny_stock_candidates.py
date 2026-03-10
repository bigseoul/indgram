from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

PENNY_STOCK_PRICE = 1_000
EXCLUDE_KEYWORDS = ("SPAC", "스팩", "ETF", "ETN", "리츠", "REIT")


def is_excluded(name: str) -> bool:
    return any(keyword in name for keyword in EXCLUDE_KEYWORDS)


def build_penny_stock_candidates(snapshot_path: Path) -> pd.DataFrame:
    df = pd.read_csv(snapshot_path)
    required_columns = {
        "market",
        "ticker",
        "name",
        "base_date",
        "close_price",
        "listed_shares",
        "market_cap",
    }
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"스냅샷 컬럼이 부족합니다: {sorted(missing)}")

    df = df.copy()
    df["ticker"] = df["ticker"].astype(str).str.zfill(6)
    df = df.loc[~df["name"].fillna("").apply(is_excluded)].copy()
    df = df.loc[df["close_price"] < PENNY_STOCK_PRICE].copy()
    df["penny_stock_threshold"] = PENNY_STOCK_PRICE
    df["price_gap"] = df["close_price"] - PENNY_STOCK_PRICE
    df["market_cap_100m"] = (df["market_cap"] / 1e8).round(1)

    return df.sort_values(["market", "close_price", "ticker"]).reset_index(drop=True)


def default_output_path(snapshot_path: Path) -> Path:
    stem = snapshot_path.stem.replace("market_snapshot_", "")
    return snapshot_path.with_name(f"penny_stock_candidates_{stem}.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="시장 스냅샷에서 동전주 후보만 추립니다."
    )
    parser.add_argument(
        "--snapshot",
        default="management_stock/data/market_snapshot_20260309.csv",
        help="입력 스냅샷 CSV 경로",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="출력 CSV 경로 (미지정 시 penny_stock_candidates_YYYYMMDD.csv)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    snapshot_path = Path(args.snapshot)
    output_path = Path(args.output) if args.output else default_output_path(snapshot_path)

    filtered = build_penny_stock_candidates(snapshot_path)
    filtered.to_csv(output_path, index=False, encoding="utf-8-sig")

    counts = filtered.groupby(["market"]).size().to_dict()
    print(f"saved: {output_path}")
    print(f"rows: {len(filtered)}")
    print(f"counts: {counts}")


if __name__ == "__main__":
    main()
