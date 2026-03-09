from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Literal

import pandas as pd
from pykrx.website.krx.market.ticker import StockTicker

MarketType = Literal["KOSPI", "KOSDAQ"]

MARKET_CODE = {
    "KOSPI": "STK",
    "KOSDAQ": "KSQ",
}


def get_market_ticker_frame(market: MarketType) -> pd.DataFrame:
    listed = StockTicker().listed
    market_code = MARKET_CODE[market]

    df = listed.loc[listed["시장"] == market_code, ["종목", "ISIN"]].copy()
    df = df.reset_index(names="ticker")
    df = df.rename(columns={"종목": "name", "ISIN": "isin"})
    df.insert(0, "market", market)
    return df


def get_all_market_ticker_frame() -> pd.DataFrame:
    kospi = get_market_ticker_frame("KOSPI")
    kosdaq = get_market_ticker_frame("KOSDAQ")
    return pd.concat([kospi, kosdaq], ignore_index=True)


def save_csv(df: pd.DataFrame, output_path: str | Path) -> Path:
    path = Path(output_path)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def save_parquet(df: pd.DataFrame, output_path: str | Path) -> Path:
    path = Path(output_path)
    df.to_parquet(path, index=False)
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="zombie/data")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    tickers = get_all_market_ticker_frame()
    created_date = datetime.now().strftime("%Y%m%d")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / f"market_tickers_{created_date}.csv"
    parquet_path = output_dir / f"market_tickers_{created_date}.parquet"

    save_csv(tickers, csv_path)
    save_parquet(tickers, parquet_path)

    print(f"saved csv: {csv_path}")
    print(f"saved parquet: {parquet_path}")
    print(tickers.head().to_string(index=False))
