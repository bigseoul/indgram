from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from typing import Literal

import pandas as pd
import requests
from bs4 import BeautifulSoup
from pykrx.website.naver.wrap import get_market_ohlcv_by_date

MarketType = Literal["KOSPI", "KOSDAQ"]

DEFAULT_BASE_DATE = "20260309"  # 전일 또는 당일(장마감 후) 종가 기준으로.
DEFAULT_TICKERS_PATH = Path("management_stock/data/market_tickers_20260310.parquet")
HEADERS = {"User-Agent": "Mozilla/5.0"}
RESULT_COLUMNS = [
    "market",
    "ticker",
    "name",
    "base_date",
    "close_price",
    "listed_shares",
    "market_cap",
]
ERROR_COLUMNS = [
    "market",
    "ticker",
    "name",
    "base_date",
    "error_type",
    "error_message",
]


def load_tickers(tickers_path: str | Path = DEFAULT_TICKERS_PATH) -> pd.DataFrame:
    path = Path(tickers_path)
    if not path.exists():
        raise FileNotFoundError(f"티커 파일이 없습니다: {path}")

    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    elif path.suffix == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(f"지원하지 않는 티커 파일 형식입니다: {path.suffix}")

    required_columns = {"market", "ticker", "name", "isin"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"티커 파일 컬럼이 부족합니다: {sorted(missing)}")

    df = df.copy()
    df["ticker"] = df["ticker"].astype(str).str.zfill(6)
    return df


def parse_current_naver_snapshot(
    ticker: str, session: requests.Session
) -> dict[str, int]:
    response = session.get(
        f"https://finance.naver.com/item/main.naver?code={ticker}",
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    listed_shares = None

    for row in soup.select("tr"):
        th = row.find("th")
        td = row.find("td")
        if th is None or td is None:
            continue

        label = th.get_text(" ", strip=True)
        if label.startswith("상장주식수"):
            digits = re.sub(r"[^0-9]", "", td.get_text())
            if digits:
                listed_shares = int(digits)
                break

    if listed_shares is None:
        raise RuntimeError(f"상장주식수 파싱 실패: {ticker}")

    return {"listed_shares": listed_shares}


def get_close_price_on_date(ticker: str, base_date: str) -> int:
    df = get_market_ohlcv_by_date(base_date, base_date, ticker)
    if df.empty:
        raise RuntimeError(f"기준일 종가 조회 실패: {ticker} {base_date}")
    return int(df.iloc[-1]["종가"])


def empty_snapshot_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=RESULT_COLUMNS)


def empty_error_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=ERROR_COLUMNS)


def load_progress(progress_path: str | Path) -> pd.DataFrame:
    path = Path(progress_path)
    if not path.exists():
        return empty_snapshot_frame()

    df = pd.read_parquet(path)
    missing = set(RESULT_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"진행 파일 컬럼이 부족합니다: {sorted(missing)}")

    df = df.copy()
    df["ticker"] = df["ticker"].astype(str).str.zfill(6)
    return df[RESULT_COLUMNS]


def save_progress(df: pd.DataFrame, progress_path: str | Path) -> Path:
    path = Path(progress_path)
    df.to_parquet(path, index=False)
    return path


def load_errors(error_path: str | Path) -> pd.DataFrame:
    path = Path(error_path)
    if not path.exists():
        return empty_error_frame()

    df = pd.read_parquet(path)
    missing = set(ERROR_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"에러 파일 컬럼이 부족합니다: {sorted(missing)}")

    df = df.copy()
    df["ticker"] = df["ticker"].astype(str).str.zfill(6)
    return df[ERROR_COLUMNS]


def save_errors(df: pd.DataFrame, error_path: str | Path) -> Path:
    path = Path(error_path)
    df.to_parquet(path, index=False)
    df.to_csv(path.with_suffix(".csv"), index=False, encoding="utf-8-sig")
    return path


def get_market_snapshot(
    tickers: pd.DataFrame,
    progress_df: pd.DataFrame,
    progress_path: str | Path,
    error_df: pd.DataFrame,
    error_path: str | Path,
    market: MarketType,
    base_date: str = DEFAULT_BASE_DATE,
    request_sleep: float = 0.0,
    limit: int | None = None,
) -> pd.DataFrame:
    df = tickers.loc[tickers["market"] == market, ["market", "ticker", "name"]].copy()
    if limit is not None:
        df = df.head(limit).copy()

    total = len(df)
    completed_mask = (progress_df["market"] == market) & (
        progress_df["base_date"] == base_date
    )
    completed_tickers = set(progress_df.loc[completed_mask, "ticker"].tolist())
    pending_df = df.loc[~df["ticker"].isin(completed_tickers)].copy()
    completed = total - len(pending_df)

    print(f"[{market}] start: {total} tickers")
    if completed:
        print(f"[{market}] resume: {completed}/{total} already done")

    with requests.Session() as session:
        for index, row in enumerate(pending_df.itertuples(index=False), start=1):
            ticker = row.ticker
            name = row.name
            current_index = completed + index
            if index == 1 or current_index % 20 == 0 or current_index == total:
                print(f"[{market}] {current_index}/{total} {ticker} {name}")

            try:
                close_price = get_close_price_on_date(ticker, base_date)
                current_snapshot = parse_current_naver_snapshot(ticker, session)
                listed_shares = int(current_snapshot["listed_shares"])
                row_df = pd.DataFrame(
                    [
                        {
                            "market": market,
                            "ticker": ticker,
                            "name": name,
                            "base_date": base_date,
                            "close_price": close_price,
                            "listed_shares": listed_shares,
                            "market_cap": close_price * listed_shares,
                        }
                    ]
                )
                progress_df = pd.concat([progress_df, row_df], ignore_index=True)
                save_progress(progress_df[RESULT_COLUMNS], progress_path)
            except Exception as exc:
                error_row = pd.DataFrame(
                    [
                        {
                            "market": market,
                            "ticker": ticker,
                            "name": name,
                            "base_date": base_date,
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                        }
                    ]
                )
                error_df = pd.concat([error_df, error_row], ignore_index=True)
                error_df = error_df.drop_duplicates(
                    subset=["market", "ticker", "base_date"],
                    keep="last",
                ).reset_index(drop=True)
                save_errors(error_df[ERROR_COLUMNS], error_path)
                print(f"[{market}] skip: {ticker} {name} ({type(exc).__name__}: {exc})")
                continue

            if request_sleep > 0:
                time.sleep(request_sleep)

    print(f"[{market}] done: {total} tickers")
    market_result = progress_df.loc[
        (progress_df["market"] == market) & (progress_df["base_date"] == base_date),
        RESULT_COLUMNS,
    ].copy()
    return market_result.sort_values("ticker").reset_index(drop=True)


def get_all_market_snapshot(
    base_date: str = DEFAULT_BASE_DATE,
    request_sleep: float = 0.0,
    limit_per_market: int | None = None,
    tickers_path: str | Path = DEFAULT_TICKERS_PATH,
    progress_path: str | Path | None = None,
    error_path: str | Path | None = None,
) -> pd.DataFrame:
    tickers = load_tickers(tickers_path)
    if progress_path is None:
        raise ValueError("progress_path is required")
    if error_path is None:
        raise ValueError("error_path is required")
    progress_df = load_progress(progress_path)
    error_df = load_errors(error_path)
    kospi = get_market_snapshot(
        tickers,
        progress_df,
        progress_path,
        error_df,
        error_path,
        "KOSPI",
        base_date=base_date,
        request_sleep=request_sleep,
        limit=limit_per_market,
    )
    progress_df = load_progress(progress_path)
    error_df = load_errors(error_path)
    kosdaq = get_market_snapshot(
        tickers,
        progress_df,
        progress_path,
        error_df,
        error_path,
        "KOSDAQ",
        base_date=base_date,
        request_sleep=request_sleep,
        limit=limit_per_market,
    )
    return pd.concat([kospi, kosdaq], ignore_index=True)


def save_snapshot_csv(df: pd.DataFrame, output_path: str | Path) -> Path:
    path = Path(output_path)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def save_snapshot_parquet(df: pd.DataFrame, output_path: str | Path) -> Path:
    path = Path(output_path)
    df.to_parquet(path, index=False)
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-date", default=DEFAULT_BASE_DATE)
    parser.add_argument("--request-sleep", type=float, default=0.0)
    parser.add_argument("--limit-per-market", type=int, default=None)
    parser.add_argument("--tickers-path", default=str(DEFAULT_TICKERS_PATH))
    parser.add_argument("--output-dir", default="management_stock/data")
    parser.add_argument("--output-stem", default="market_snapshot")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    progress_path = output_dir / f"{args.output_stem}_{args.base_date}.progress.parquet"
    error_path = output_dir / f"{args.output_stem}_{args.base_date}.errors.parquet"
    csv_path = output_dir / f"{args.output_stem}_{args.base_date}.csv"
    parquet_path = output_dir / f"{args.output_stem}_{args.base_date}.parquet"
    snapshot = get_all_market_snapshot(
        base_date=args.base_date,
        request_sleep=args.request_sleep,
        limit_per_market=args.limit_per_market,
        tickers_path=args.tickers_path,
        progress_path=progress_path,
        error_path=error_path,
    )

    save_snapshot_csv(snapshot, csv_path)
    save_snapshot_parquet(snapshot, parquet_path)

    print(f"saved progress: {progress_path}")
    print(f"saved errors: {error_path}")
    print(f"saved csv: {csv_path}")
    print(f"saved parquet: {parquet_path}")
    print(snapshot.to_string(index=False))
