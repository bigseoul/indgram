from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from zombie.dart_fetcher import (
    DEFAULT_CHECKPOINT_DIR,
    DEFAULT_ERROR_PATH,
    DEFAULT_INPUT_PATH,
    DEFAULT_PROGRESS_PATH,
    DEFAULT_RAW_PARQUET_PATH,
    DEFAULT_YEARS,
    ERROR_COLUMNS,
    PROGRESS_COLUMNS,
    REPORT_CODE,
    build_reader,
    empty_error_frame,
    empty_progress_frame,
    fetch_financial_statement,
    get_default_api_key,
    load_input_universe,
    load_parquet_frame,
    resolve_corp_codes,
    save_parquet_frame,
    upsert_rows,
    utc_now,
)
from zombie.icr_calculator import RAW_COLUMNS, build_excluded_rows, build_proxy_metric_series, build_raw_record, build_result_frame

DEFAULT_RAW_CSV_PATH = Path("zombie/data/icr_extract_2022_2024_long.csv")
DEFAULT_EXACT_CSV_PATH = Path("zombie_2026.csv")
DEFAULT_PROXY_CSV_PATH = Path("zombie_2026_proxy.csv")


def export_csv(df: pd.DataFrame, path: str | Path) -> Path:
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path_obj, index=False, encoding="utf-8-sig")
    return path_obj


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Screen listed Korean zombie companies from DART.")
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--checkpoint-dir", type=Path, default=DEFAULT_CHECKPOINT_DIR)
    parser.add_argument("--raw-parquet", type=Path, default=DEFAULT_RAW_PARQUET_PATH)
    parser.add_argument("--progress-path", type=Path, default=DEFAULT_PROGRESS_PATH)
    parser.add_argument("--error-path", type=Path, default=DEFAULT_ERROR_PATH)
    parser.add_argument("--raw-csv", type=Path, default=DEFAULT_RAW_CSV_PATH)
    parser.add_argument("--exact-csv", type=Path, default=DEFAULT_EXACT_CSV_PATH)
    parser.add_argument("--proxy-csv", type=Path, default=DEFAULT_PROXY_CSV_PATH)
    parser.add_argument("--years", nargs="+", type=int, default=list(DEFAULT_YEARS))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--request-sleep", type=float, default=0.07)
    parser.add_argument("--max-retries", type=int, default=4)
    return parser.parse_args()


def print_top20(title: str, df: pd.DataFrame) -> None:
    print()
    print(title)
    if df.empty:
        print("(no rows)")
        return
    print(df.head(20).to_string(index=False))


def main() -> int:
    args = parse_args()
    args.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    api_key = get_default_api_key()
    if not api_key:
        print("DART API key not found. Set DART_API_KEY or provide corp_code_extractor/corp_list.py API_KEY.")
        return 1

    years = tuple(sorted(set(args.years)))
    universe_df = load_input_universe(args.input_path)
    included_df, excluded_df = resolve_corp_codes(universe_df, api_key)
    if args.limit is not None:
        included_df = included_df.head(args.limit).reset_index(drop=True)

    print(f"input rows: {len(universe_df):,}")
    print(f"included rows: {len(included_df):,}")
    print(f"excluded rows: {len(excluded_df):,}")

    progress_df = load_parquet_frame(args.progress_path, PROGRESS_COLUMNS)
    error_df = load_parquet_frame(args.error_path, ERROR_COLUMNS)
    raw_df = load_parquet_frame(args.raw_parquet, RAW_COLUMNS)
    completed_keys = {
        (str(row.corp_code), int(row.year))
        for row in progress_df.itertuples(index=False)
        if pd.notna(row.corp_code) and pd.notna(row.year)
    }

    reader = build_reader(api_key)
    total_tasks = len(included_df) * len(years)
    processed = 0

    for company in included_df.to_dict("records"):
        for year in years:
            key = (company["corp_code"], int(year))
            if key in completed_keys:
                continue

            processed += 1
            if processed == 1 or processed % 25 == 0 or processed == total_tasks:
                print(f"processing {processed}/{total_tasks}: {company['stock_code']} {company['name']} {year}")

            try:
                fetch_result = fetch_financial_statement(
                    reader,
                    company["corp_code"],
                    int(year),
                    request_sleep=args.request_sleep,
                    max_retries=args.max_retries,
                )
                record = build_raw_record(
                    company_row=company,
                    year=int(year),
                    frame=fetch_result.frame,
                    fs_div_used=fetch_result.fs_div_used,
                    base_status=fetch_result.source_status,
                    report_code=REPORT_CODE,
                )
                record_df = pd.DataFrame([record], columns=list(RAW_COLUMNS))
                raw_df = upsert_rows(raw_df, record_df, ["corp_code", "year"])
                save_parquet_frame(raw_df, args.raw_parquet)

                progress_row = pd.DataFrame(
                    [
                        {
                            "market": company["market"],
                            "stock_code": company["stock_code"],
                            "corp_code": company["corp_code"],
                            "name": company["name"],
                            "year": int(year),
                            "report_code": REPORT_CODE,
                            "fs_div_used": fetch_result.fs_div_used,
                            "source_status": record["source_status"],
                            "processed_at": utc_now(),
                        }
                    ],
                    columns=list(PROGRESS_COLUMNS),
                )
                progress_df = upsert_rows(progress_df, progress_row, ["corp_code", "year"])
                save_parquet_frame(progress_df, args.progress_path)
                if not error_df.empty:
                    error_df = error_df.loc[
                        ~(
                            error_df["corp_code"].eq(company["corp_code"])
                            & error_df["year"].astype("Int64").eq(int(year))
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
                            "year": int(year),
                            "report_code": REPORT_CODE,
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                            "processed_at": utc_now(),
                        }
                    ],
                    columns=list(ERROR_COLUMNS),
                )
                error_df = upsert_rows(error_df, error_row, ["corp_code", "year"])
                save_parquet_frame(error_df, args.error_path)
                print(f"skip {company['stock_code']} {company['name']} {year}: {type(exc).__name__}: {exc}")

    if progress_df.empty:
        progress_df = empty_progress_frame()
    if error_df.empty:
        error_df = empty_error_frame()

    excluded_rows = build_excluded_rows(excluded_df, years=years, report_code=REPORT_CODE)
    raw_export_df = pd.concat([raw_df, excluded_rows], ignore_index=True)
    raw_export_df = raw_export_df.sort_values(["market", "stock_code", "year"]).reset_index(drop=True)
    export_csv(raw_export_df, args.raw_csv)

    exact_df = build_result_frame(raw_df, "icr_exact")
    proxy_source_df = raw_df.copy()
    proxy_source_df["icr_proxy_fallback"] = build_proxy_metric_series(proxy_source_df)
    proxy_df = build_result_frame(proxy_source_df, "icr_proxy_fallback")

    export_csv(exact_df, args.exact_csv)
    export_csv(proxy_df, args.proxy_csv)

    print_top20("[exact top 20]", exact_df)
    print_top20("[proxy top 20]", proxy_df)
    print()
    print(f"raw csv: {args.raw_csv}")
    print(f"exact csv: {args.exact_csv}")
    print(f"proxy csv: {args.proxy_csv}")
    print(f"progress parquet: {args.progress_path}")
    print(f"error parquet: {args.error_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
