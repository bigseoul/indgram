from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

os.environ.setdefault(
    "MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "indgram-matplotlib")
)
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API.*",
    category=UserWarning,
)

from pykrx.website.naver.wrap import get_market_ohlcv_by_date

RESULT_COLUMNS = [
    "market",
    "ticker",
    "name",
    "base_date",
    "close_price",
    "listed_shares",
    "market_cap",
    "threshold",
    "risk_level",
]
ERROR_COLUMNS = [
    "market",
    "ticker",
    "name",
    "base_date",
    "error_type",
    "error_message",
]
THRESHOLDS = {
    "KOSDAQ": 20_000_000_000,
    "KOSPI": 30_000_000_000,
}
WARNING_RATIO = 1.3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="위험/경고 후보 종목의 최근 N거래일 이력을 수집합니다."
    )
    parser.add_argument(
        "--candidates",
        default="management_stock/data/warning_candidates_20260309.csv",
        help="위험/경고 후보 CSV 경로",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=45,
        help="수집할 거래일 수",
    )
    parser.add_argument(
        "--calendar-buffer-days",
        type=int,
        default=None,
        help="거래일 조회를 위해 base_date 이전으로 넉넉하게 당겨볼 달력일 수",
    )
    parser.add_argument(
        "--output-stem",
        default=None,
        help="출력 파일 prefix 경로. 미지정 시 warning_history_YYYYMMDD 사용",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="앞에서부터 일부 종목만 테스트 수집",
    )
    parser.add_argument(
        "--request-sleep",
        type=float,
        default=0.3,
        help="종목 간 대기 시간(초)",
    )
    return parser.parse_args()


def load_candidates(candidates_path: str | Path) -> pd.DataFrame:
    path = Path(candidates_path)
    if not path.exists():
        raise FileNotFoundError(f"후보 파일이 없습니다: {path}")

    df = pd.read_csv(path)
    required_columns = {
        "market",
        "ticker",
        "name",
        "base_date",
        "listed_shares",
    }
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"후보 파일 컬럼이 부족합니다: {sorted(missing)}")

    df = df.copy()
    df["ticker"] = df["ticker"].astype(str).str.zfill(6)
    df["base_date"] = df["base_date"].astype(str)
    df["listed_shares"] = df["listed_shares"].astype(int)
    df = df.drop_duplicates(subset=["market", "ticker", "base_date"], keep="last")
    return df


def resolve_base_date(candidates: pd.DataFrame) -> str:
    base_dates = candidates["base_date"].dropna().unique().tolist()
    if len(base_dates) != 1:
        raise ValueError(f"후보 파일의 base_date가 하나가 아닙니다: {base_dates}")
    return str(base_dates[0])


def resolve_output_stem(args: argparse.Namespace, base_date: str) -> Path:
    if args.output_stem:
        return Path(args.output_stem)
    return Path(f"management_stock/data/warning_history_{base_date}")


def build_progress_path(output_stem: Path) -> Path:
    return Path(f"{output_stem}.progress.parquet")


def build_error_path(output_stem: Path) -> Path:
    return Path(f"{output_stem}.errors.parquet")


def build_meta_path(output_stem: Path) -> Path:
    return Path(f"{output_stem}.meta.json")


def load_progress(progress_path: Path) -> pd.DataFrame:
    if not progress_path.exists():
        return pd.DataFrame(columns=RESULT_COLUMNS)

    df = pd.read_parquet(progress_path)
    missing = set(RESULT_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"진행 파일 컬럼이 부족합니다: {sorted(missing)}")

    df = df.copy()
    df["ticker"] = df["ticker"].astype(str).str.zfill(6)
    df["base_date"] = df["base_date"].astype(str)
    return df[RESULT_COLUMNS]


def load_run_meta(meta_path: Path) -> dict:
    if not meta_path.exists():
        return {}

    with meta_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_run_meta(meta_path: Path, meta: dict) -> None:
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def ensure_resume_compatible(
    meta_path: Path,
    *,
    candidates_path: str | Path,
    base_date: str,
    days: int,
    calendar_buffer_days: int,
    limit: int | None,
) -> None:
    current_meta = {
        "candidates_path": str(Path(candidates_path)),
        "base_date": str(base_date),
        "days": int(days),
        "calendar_buffer_days": int(calendar_buffer_days),
        "limit": int(limit) if limit is not None else None,
    }
    existing_meta = load_run_meta(meta_path)
    if not existing_meta:
        save_run_meta(meta_path, current_meta)
        return

    mismatched_keys = [
        key for key, value in current_meta.items() if existing_meta.get(key) != value
    ]
    if mismatched_keys:
        details = ", ".join(
            f"{key}={existing_meta.get(key)} -> {current_meta[key]}"
            for key in mismatched_keys
        )
        raise ValueError(
            "기존 progress 파일과 실행 조건이 다릅니다. "
            f"같은 output_stem으로 재개하려면 동일 조건을 사용해야 합니다: {details}"
        )


def save_progress(df: pd.DataFrame, progress_path: Path) -> None:
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    deduped = (
        df.drop_duplicates(subset=["ticker", "base_date"], keep="last")
        .sort_values(["ticker", "base_date"])
        .reset_index(drop=True)
    )
    deduped.to_parquet(progress_path, index=False)


def load_errors(error_path: Path) -> pd.DataFrame:
    if not error_path.exists():
        return pd.DataFrame(columns=ERROR_COLUMNS)

    df = pd.read_parquet(error_path)
    missing = set(ERROR_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"에러 파일 컬럼이 부족합니다: {sorted(missing)}")

    df = df.copy()
    df["ticker"] = df["ticker"].astype(str).str.zfill(6)
    df["base_date"] = df["base_date"].astype(str)
    return df[ERROR_COLUMNS]


def save_errors(df: pd.DataFrame, error_path: Path) -> None:
    error_path.parent.mkdir(parents=True, exist_ok=True)
    deduped = (
        df.drop_duplicates(subset=["ticker", "base_date"], keep="last")
        .sort_values(["ticker", "base_date"])
        .reset_index(drop=True)
    )
    deduped.to_parquet(error_path, index=False)
    deduped.to_csv(error_path.with_suffix(".csv"), index=False, encoding="utf-8-sig")


def build_history_frame(
    market: str,
    ticker: str,
    name: str,
    base_date: str,
    listed_shares: int,
    days: int,
    calendar_buffer_days: int,
) -> pd.DataFrame:
    from_date = (
        datetime.strptime(base_date, "%Y%m%d") - timedelta(days=calendar_buffer_days)
    ).strftime("%Y%m%d")
    raw = get_market_ohlcv_by_date(from_date, base_date, ticker)
    if raw.empty:
        raise RuntimeError(f"거래이력 조회 실패: {ticker} {base_date}")

    history = raw.tail(days).copy()
    if history.empty:
        raise RuntimeError(f"거래이력 부족: {ticker} {base_date}")

    frame = pd.DataFrame(
        {
            "market": market,
            "ticker": ticker,
            "name": name,
            "base_date": history.index.strftime("%Y%m%d"),
            "close_price": history["종가"].astype(int).values,
            "listed_shares": listed_shares,
        }
    )
    frame["market_cap"] = frame["close_price"] * frame["listed_shares"]
    frame["threshold"] = THRESHOLDS[market]
    frame["risk_level"] = frame.apply(classify_risk_level, axis=1)
    return frame[RESULT_COLUMNS]


def classify_risk_level(row: pd.Series) -> str:
    market_cap = int(row["market_cap"])
    threshold = int(row["threshold"])
    warning_upper = int(threshold * WARNING_RATIO)

    if market_cap < threshold:
        return "위험"
    if market_cap < warning_upper:
        return "경고"
    return "안전"


def collect_warning_history(
    candidates: pd.DataFrame,
    days: int,
    calendar_buffer_days: int,
    output_stem: Path,
    candidates_path: str | Path,
    base_date: str,
    request_sleep: float = 0.0,
    limit: int | None = None,
) -> pd.DataFrame:
    progress_path = build_progress_path(output_stem)
    error_path = build_error_path(output_stem)
    meta_path = build_meta_path(output_stem)
    ensure_resume_compatible(
        meta_path,
        candidates_path=candidates_path,
        base_date=base_date,
        days=days,
        calendar_buffer_days=calendar_buffer_days,
        limit=limit,
    )
    progress_df = load_progress(progress_path)
    error_df = load_errors(error_path)

    candidate_cols = ["market", "ticker", "name", "base_date", "listed_shares"]
    pending = candidates.loc[:, candidate_cols].copy()
    if limit is not None:
        pending = pending.head(limit).copy()

    completed_tickers = set(progress_df["ticker"].astype(str).tolist())
    pending = pending.loc[~pending["ticker"].isin(completed_tickers)].reset_index(
        drop=True
    )
    total = len(pending)
    resumed = len(completed_tickers & set(candidates["ticker"].astype(str).tolist()))

    print(
        f"[history] start: {len(candidates) if limit is None else min(len(candidates), limit)} tickers"
    )
    if resumed:
        print(f"[history] resume: {resumed} tickers already collected")

    if total == 0:
        return (
            progress_df.drop_duplicates(subset=["ticker", "base_date"], keep="last")
            .sort_values(["ticker", "base_date"])
            .reset_index(drop=True)
        )

    for index, row in enumerate(pending.itertuples(index=False), start=1):
        if index == 1 or index % 10 == 0 or index == total:
            print(f"[history] {index}/{total} {row.ticker} {row.name}")

        try:
            history = build_history_frame(
                market=row.market,
                ticker=row.ticker,
                name=row.name,
                base_date=row.base_date,
                listed_shares=int(row.listed_shares),
                days=days,
                calendar_buffer_days=calendar_buffer_days,
            )
            progress_df = pd.concat([progress_df, history], ignore_index=True)
            save_progress(progress_df[RESULT_COLUMNS], progress_path)

            if len(history) < days:
                print(
                    f"[history] warning: {row.ticker} {row.name} "
                    f"{len(history)}/{days}거래일만 수집"
                )
        except Exception as exc:
            error_row = pd.DataFrame(
                [
                    {
                        "market": row.market,
                        "ticker": row.ticker,
                        "name": row.name,
                        "base_date": row.base_date,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    }
                ]
            )
            error_df = pd.concat([error_df, error_row], ignore_index=True)
            save_errors(error_df[ERROR_COLUMNS], error_path)
            print(f"[history] skip: {row.ticker} {row.name} ({type(exc).__name__}: {exc})")
            continue

        if request_sleep > 0:
            time.sleep(request_sleep)

    final = (
        progress_df.drop_duplicates(subset=["ticker", "base_date"], keep="last")
        .sort_values(["ticker", "base_date"])
        .reset_index(drop=True)
    )
    return final[RESULT_COLUMNS]


def main() -> None:
    args = parse_args()
    candidates = load_candidates(args.candidates)
    base_date = resolve_base_date(candidates)
    output_stem = resolve_output_stem(args, base_date)
    calendar_buffer_days = (
        args.calendar_buffer_days
        if args.calendar_buffer_days is not None
        else max(90, args.days * 3)
    )

    result = collect_warning_history(
        candidates=candidates,
        days=args.days,
        calendar_buffer_days=calendar_buffer_days,
        output_stem=output_stem,
        candidates_path=args.candidates,
        base_date=base_date,
        request_sleep=args.request_sleep,
        limit=args.limit,
    )

    csv_path = output_stem.with_suffix(".csv")
    parquet_path = output_stem.with_suffix(".parquet")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(csv_path, index=False, encoding="utf-8-sig")
    result.to_parquet(parquet_path, index=False)

    print(f"saved csv: {csv_path}")
    print(f"saved parquet: {parquet_path}")
    print(
        "rows:",
        len(result),
        "tickers:",
        result["ticker"].nunique() if not result.empty else 0,
    )


if __name__ == "__main__":
    main()
