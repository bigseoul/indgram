from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from zombie.common_io import DEFAULT_INPUT_PATH, load_input_universe, load_parquet_frame, save_parquet_frame, upsert_rows, utc_now
from zombie.screen_zombie import export_csv
from zombie.wisereport_fetcher import (
    DEFAULT_WR_ERROR_PATH,
    DEFAULT_WR_FIN_GUBUN,
    DEFAULT_WR_FRQ_TYP,
    DEFAULT_WR_PROGRESS_PATH,
    DEFAULT_WR_QUOTE_ERROR_PATH,
    DEFAULT_WR_QUOTE_PATH,
    DEFAULT_WR_RAW_PARQUET_PATH,
    DEFAULT_WR_RPT,
    WR_ERROR_COLUMNS,
    WR_PROGRESS_COLUMNS,
    WR_QUOTE_COLUMNS,
    WR_QUOTE_ERROR_COLUMNS,
    WR_RAW_COLUMNS,
    build_raw_payload_row,
    build_session,
    empty_error_frame,
    empty_progress_frame,
    empty_quote_error_frame,
    empty_quote_frame,
    fetch_overview_page_with_retries,
    fetch_indicator_payload_with_retries,
)
from zombie.wisereport_parser import (
    WR_LONG_COLUMNS,
    build_long_frame,
    build_quote_frame,
    build_result_frame,
    filter_result_frame_by_trading_status,
    parse_quote_snapshot,
)

DEFAULT_WR_RAW_CSV_PATH = Path("zombie/data/icr_2022_2024_ifrss_long.csv")
DEFAULT_WR_RESULT_CSV_PATH = Path("zombie/data/icr_2022_2024_ifrss.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Screen zombie companies from WiseReport interest coverage.")
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--progress-path", type=Path, default=DEFAULT_WR_PROGRESS_PATH)
    parser.add_argument("--error-path", type=Path, default=DEFAULT_WR_ERROR_PATH)
    parser.add_argument("--raw-parquet", type=Path, default=DEFAULT_WR_RAW_PARQUET_PATH)
    parser.add_argument("--quote-path", type=Path, default=DEFAULT_WR_QUOTE_PATH)
    parser.add_argument("--quote-error-path", type=Path, default=DEFAULT_WR_QUOTE_ERROR_PATH)
    parser.add_argument("--raw-csv", type=Path, default=DEFAULT_WR_RAW_CSV_PATH)
    parser.add_argument("--result-csv", type=Path, default=DEFAULT_WR_RESULT_CSV_PATH)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--request-sleep", type=float, default=0.1)
    parser.add_argument("--max-retries", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=20.0)
    return parser.parse_args()


def print_top20(df: pd.DataFrame) -> None:
    print()
    print("[wisereport top 20]")
    if df.empty:
        print("(no rows)")
        return
    print(df.head(20).to_string(index=False))


def main() -> int:
    args = parse_args()

    universe_df = load_input_universe(args.input_path)
    if args.limit is not None:
        universe_df = universe_df.head(args.limit).reset_index(drop=True)

    progress_df = load_parquet_frame(args.progress_path, WR_PROGRESS_COLUMNS)
    error_df = load_parquet_frame(args.error_path, WR_ERROR_COLUMNS)
    raw_df = load_parquet_frame(args.raw_parquet, WR_RAW_COLUMNS)
    quote_df = load_parquet_frame(args.quote_path, WR_QUOTE_COLUMNS)
    quote_error_df = load_parquet_frame(args.quote_error_path, WR_QUOTE_ERROR_COLUMNS)

    completed_keys = {
        (str(row.stock_code), int(row.rpt), str(row.fin_gubun), str(row.frq_typ))
        for row in progress_df.itertuples(index=False)
        if pd.notna(row.stock_code)
    }
    completed_quote_codes = {str(row.stock_code) for row in quote_df.itertuples(index=False) if pd.notna(row.stock_code)}

    session = build_session()
    total_tasks = len(universe_df)
    processed = 0

    for company in universe_df.to_dict("records"):
        key = (company["stock_code"], DEFAULT_WR_RPT, DEFAULT_WR_FIN_GUBUN, DEFAULT_WR_FRQ_TYP)
        if key in completed_keys:
            continue

        processed += 1
        if processed == 1 or processed % 25 == 0 or processed == total_tasks:
            print(f"processing {processed}/{total_tasks}: {company['stock_code']} {company['name']}")

        try:
            result = fetch_indicator_payload_with_retries(
                session=session,
                stock_code=company["stock_code"],
                rpt=DEFAULT_WR_RPT,
                fin_gubun=DEFAULT_WR_FIN_GUBUN,
                frq_typ=DEFAULT_WR_FRQ_TYP,
                timeout=args.timeout,
                request_sleep=args.request_sleep,
                max_retries=args.max_retries,
            )
            raw_row = build_raw_payload_row(
                company_row=company,
                payload_json=result.payload_json,
                rpt=DEFAULT_WR_RPT,
                fin_gubun=DEFAULT_WR_FIN_GUBUN,
                frq_typ=DEFAULT_WR_FRQ_TYP,
                source_status=result.source_status,
            )
            raw_df = upsert_rows(raw_df, raw_row, ["stock_code", "rpt", "fin_gubun", "frq_typ"])
            save_parquet_frame(raw_df, args.raw_parquet)

            progress_row = pd.DataFrame(
                [
                    {
                        "market": company["market"],
                        "stock_code": company["stock_code"],
                        "corp_code": company["corp_code"],
                        "name": company["name"],
                        "rpt": DEFAULT_WR_RPT,
                        "fin_gubun": DEFAULT_WR_FIN_GUBUN,
                        "frq_typ": DEFAULT_WR_FRQ_TYP,
                        "source_status": result.source_status,
                        "processed_at": utc_now(),
                    }
                ],
                columns=list(WR_PROGRESS_COLUMNS),
            )
            progress_df = upsert_rows(progress_df, progress_row, ["stock_code", "rpt", "fin_gubun", "frq_typ"])
            save_parquet_frame(progress_df, args.progress_path)
            if not error_df.empty:
                error_df = error_df.loc[
                    ~(
                        error_df["stock_code"].eq(company["stock_code"])
                        & error_df["rpt"].astype("Int64").eq(DEFAULT_WR_RPT)
                        & error_df["fin_gubun"].eq(DEFAULT_WR_FIN_GUBUN)
                        & error_df["frq_typ"].eq(DEFAULT_WR_FRQ_TYP)
                    )
                ].reset_index(drop=True)
                save_parquet_frame(error_df, args.error_path)
            completed_keys.add(key)
        except Exception as exc:
            error_row = pd.DataFrame(
                [
                    {
                        "market": company["market"],
                        "stock_code": company["stock_code"],
                        "corp_code": company["corp_code"],
                        "name": company["name"],
                        "rpt": DEFAULT_WR_RPT,
                        "fin_gubun": DEFAULT_WR_FIN_GUBUN,
                        "frq_typ": DEFAULT_WR_FRQ_TYP,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                        "processed_at": utc_now(),
                    }
                ],
                columns=list(WR_ERROR_COLUMNS),
            )
            error_df = upsert_rows(error_df, error_row, ["stock_code", "rpt", "fin_gubun", "frq_typ"])
            save_parquet_frame(error_df, args.error_path)
            print(f"skip {company['stock_code']} {company['name']}: {type(exc).__name__}: {exc}")

    quote_rows: list[dict[str, object]] = []
    for index, company in enumerate(universe_df.to_dict("records"), start=1):
        stock_code = company["stock_code"]
        if stock_code in completed_quote_codes:
            continue

        if index == 1 or index % 25 == 0 or index == total_tasks:
            print(f"quote {index}/{total_tasks}: {stock_code} {company['name']}")

        try:
            page_html = fetch_overview_page_with_retries(
                session=session,
                stock_code=stock_code,
                timeout=args.timeout,
                request_sleep=args.request_sleep,
                max_retries=args.max_retries,
            )
            quote_rows.append(parse_quote_snapshot({"fetched_at": utc_now(), **company}, page_html))
            if len(quote_rows) >= 25:
                quote_df = upsert_rows(quote_df, build_quote_frame(quote_rows), ["stock_code"])
                save_parquet_frame(quote_df, args.quote_path)
                quote_rows = []
            if not quote_error_df.empty:
                quote_error_df = quote_error_df.loc[~quote_error_df["stock_code"].eq(stock_code)].reset_index(drop=True)
                save_parquet_frame(quote_error_df, args.quote_error_path)
            completed_quote_codes.add(stock_code)
        except Exception as exc:
            quote_error_row = pd.DataFrame(
                [
                    {
                        "market": company["market"],
                        "stock_code": stock_code,
                        "corp_code": company["corp_code"],
                        "name": company["name"],
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                        "processed_at": utc_now(),
                    }
                ],
                columns=list(WR_QUOTE_ERROR_COLUMNS),
            )
            quote_error_df = upsert_rows(quote_error_df, quote_error_row, ["stock_code"])
            save_parquet_frame(quote_error_df, args.quote_error_path)
            print(f"quote skip {stock_code} {company['name']}: {type(exc).__name__}: {exc}")

    if quote_rows:
        quote_df = upsert_rows(quote_df, build_quote_frame(quote_rows), ["stock_code"])
        save_parquet_frame(quote_df, args.quote_path)

    if progress_df.empty:
        progress_df = empty_progress_frame()
    if error_df.empty:
        error_df = empty_error_frame()
    if quote_df.empty:
        quote_df = empty_quote_frame()
    if quote_error_df.empty:
        quote_error_df = empty_quote_error_frame()

    export_source_df = raw_df.loc[
        raw_df["rpt"].astype("Int64").eq(DEFAULT_WR_RPT)
        & raw_df["fin_gubun"].eq(DEFAULT_WR_FIN_GUBUN)
        & raw_df["frq_typ"].eq(DEFAULT_WR_FRQ_TYP)
    ].copy()

    long_df = build_long_frame(export_source_df)
    if long_df.empty:
        long_df = pd.DataFrame(columns=list(WR_LONG_COLUMNS))
    export_csv(long_df, args.raw_csv)

    result_df = build_result_frame(long_df)
    result_df = filter_result_frame_by_trading_status(result_df, quote_df)
    export_csv(result_df, args.result_csv)
    print_top20(result_df)
    print()
    print(f"raw csv: {args.raw_csv}")
    print(f"result csv: {args.result_csv}")
    print(f"progress parquet: {args.progress_path}")
    print(f"error parquet: {args.error_path}")
    print(f"quote parquet: {args.quote_path}")
    print(f"quote error parquet: {args.quote_error_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
