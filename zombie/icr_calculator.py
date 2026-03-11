from __future__ import annotations

import re
from typing import Any

import pandas as pd

from zombie.common_io import is_blank

RAW_COLUMNS = (
    "market",
    "stock_code",
    "corp_code",
    "name",
    "year",
    "fs_div_used",
    "report_code",
    "source_status",
    "operating_profit",
    "interest_expense_exact",
    "finance_cost_proxy",
    "icr_exact",
    "icr_proxy",
)

SUPPORTED_SJ_DIVS = {"IS", "CIS"}
OPERATING_PROFIT_ACCOUNT_NAMES = ("영업이익", "영업이익(손실)", "OperatingIncomeLoss")
OPERATING_PROFIT_ACCOUNT_IDS = ("OperatingIncomeLoss",)
EXACT_INTEREST_ACCOUNT_NAMES = ("이자비용", "이자비용(손실)", "InterestExpense")
EXACT_INTEREST_ACCOUNT_IDS = ("InterestExpense",)
PROXY_INTEREST_ACCOUNT_NAMES = ("금융비용", "금융원가", "FinanceCosts")
PROXY_INTEREST_ACCOUNT_IDS = ("FinanceCosts",)
def normalize_account_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    return re.sub(r"[^0-9a-z가-힣]+", "", text)


def parse_amount(value: Any) -> float | None:
    if is_blank(value):
        return None

    text = str(value).strip()
    if not text:
        return None

    negative = text.startswith("(") and text.endswith(")")
    cleaned = text.replace(",", "").replace(" ", "")
    cleaned = cleaned.strip("()")
    if cleaned == "":
        return None

    amount = float(cleaned)
    return -amount if negative else amount


def amount_from_row(row: pd.Series) -> float | None:
    primary = row.get("thstrm_amount")
    if not is_blank(primary):
        return parse_amount(primary)

    fallback = row.get("thstrm_add_amount")
    if is_blank(fallback):
        return None
    return parse_amount(fallback)


def _candidate_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()

    working = frame.copy()
    working["sj_div"] = working.get("sj_div", "").fillna("").astype(str)
    working = working.loc[working["sj_div"].isin(SUPPORTED_SJ_DIVS)].copy()
    if working.empty:
        return working

    working["account_nm_normalized"] = working.get("account_nm", "").map(normalize_account_text)
    working["account_id_normalized"] = working.get("account_id", "").map(normalize_account_text)
    working["amount"] = working.apply(amount_from_row, axis=1)
    working["ord_numeric"] = pd.to_numeric(working.get("ord"), errors="coerce").fillna(10**9)
    return working


def _select_metric(
    frame: pd.DataFrame,
    account_names: tuple[str, ...],
    account_ids: tuple[str, ...],
) -> float | None:
    candidates = _candidate_frame(frame)
    if candidates.empty:
        return None

    normalized_names = {normalize_account_text(name) for name in account_names}
    normalized_ids = {normalize_account_text(account_id) for account_id in account_ids}

    name_matches = candidates.loc[candidates["account_nm_normalized"].isin(normalized_names)].copy()
    if not name_matches.empty:
        ordered = name_matches.sort_values(["ord_numeric", "account_nm_normalized"], kind="stable")
        return ordered.iloc[0]["amount"]

    if not normalized_ids:
        return None

    id_matches = candidates.loc[candidates["account_id_normalized"].isin(normalized_ids)].copy()
    if id_matches.empty:
        return None

    ordered = id_matches.sort_values(["ord_numeric", "account_id_normalized"], kind="stable")
    return ordered.iloc[0]["amount"]


def calculate_icr(operating_profit: float | None, interest_cost: float | None) -> float | None:
    if operating_profit is None or interest_cost is None or interest_cost <= 0:
        return None
    return operating_profit / interest_cost


def derive_source_status(
    base_status: str,
    exact_interest: float | None,
    proxy_interest: float | None,
) -> str:
    if base_status == "missing_statement":
        return base_status
    if exact_interest is None:
        return "missing_exact_interest"
    if exact_interest <= 0:
        return "invalid_interest_sign"
    if proxy_interest is None:
        return "missing_proxy_interest"
    if proxy_interest <= 0:
        return "invalid_interest_sign"
    return base_status


def build_raw_record(
    company_row: dict[str, Any],
    year: int,
    frame: pd.DataFrame,
    fs_div_used: str,
    base_status: str,
    report_code: str,
) -> dict[str, Any]:
    if base_status == "missing_statement" or frame.empty:
        return {
            "market": company_row["market"],
            "stock_code": company_row["stock_code"],
            "corp_code": company_row["corp_code"],
            "name": company_row["name"],
            "year": year,
            "fs_div_used": fs_div_used,
            "report_code": report_code,
            "source_status": "missing_statement",
            "operating_profit": None,
            "interest_expense_exact": None,
            "finance_cost_proxy": None,
            "icr_exact": None,
            "icr_proxy": None,
        }

    operating_profit = _select_metric(
        frame,
        OPERATING_PROFIT_ACCOUNT_NAMES,
        OPERATING_PROFIT_ACCOUNT_IDS,
    )
    exact_interest = _select_metric(
        frame,
        EXACT_INTEREST_ACCOUNT_NAMES,
        EXACT_INTEREST_ACCOUNT_IDS,
    )
    proxy_interest = _select_metric(
        frame,
        PROXY_INTEREST_ACCOUNT_NAMES,
        PROXY_INTEREST_ACCOUNT_IDS,
    )

    return {
        "market": company_row["market"],
        "stock_code": company_row["stock_code"],
        "corp_code": company_row["corp_code"],
        "name": company_row["name"],
        "year": year,
        "fs_div_used": fs_div_used,
        "report_code": report_code,
        "source_status": derive_source_status(base_status, exact_interest, proxy_interest),
        "operating_profit": operating_profit,
        "interest_expense_exact": exact_interest,
        "finance_cost_proxy": proxy_interest,
        "icr_exact": calculate_icr(operating_profit, exact_interest),
        "icr_proxy": calculate_icr(operating_profit, proxy_interest),
    }


def build_excluded_rows(excluded_df: pd.DataFrame, years: tuple[int, ...], report_code: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in excluded_df.itertuples(index=False):
        for year in years:
            rows.append(
                {
                    "market": row.market,
                    "stock_code": row.stock_code,
                    "corp_code": "",
                    "name": row.name,
                    "year": year,
                    "fs_div_used": "",
                    "report_code": report_code,
                    "source_status": "excluded_no_corp_code",
                    "operating_profit": None,
                    "interest_expense_exact": None,
                    "finance_cost_proxy": None,
                    "icr_exact": None,
                    "icr_proxy": None,
                }
            )
    return pd.DataFrame(rows, columns=list(RAW_COLUMNS))


def build_result_frame(raw_df: pd.DataFrame, metric_column: str) -> pd.DataFrame:
    ordered_columns = ["market", "stock_code", "corp_code", "name", "icr_2024", "icr_2023", "icr_2022", "icr_avg"]
    if raw_df.empty:
        return pd.DataFrame(columns=ordered_columns)

    working = raw_df.loc[:, ["market", "stock_code", "corp_code", "name", "year", metric_column]].copy()
    working = working.rename(columns={metric_column: "icr"})
    pivoted = working.pivot_table(
        index=["market", "stock_code", "corp_code", "name"],
        columns="year",
        values="icr",
        aggfunc="first",
    )
    pivoted = pivoted.reset_index()

    for year in (2024, 2023, 2022):
        if year not in pivoted.columns:
            pivoted[year] = pd.NA

    pivoted = pivoted.rename(columns={2024: "icr_2024", 2023: "icr_2023", 2022: "icr_2022"})
    filtered = pivoted.dropna(subset=["icr_2024", "icr_2023", "icr_2022"]).copy()
    if filtered.empty:
        return filtered.reindex(columns=ordered_columns)

    metric_cols = ["icr_2024", "icr_2023", "icr_2022"]
    filtered = filtered.loc[(filtered[metric_cols] < 1).all(axis=1)].copy()
    filtered["icr_avg"] = filtered[metric_cols].mean(axis=1)
    filtered = filtered.reindex(columns=ordered_columns)
    return filtered.sort_values(["icr_avg", "market", "stock_code"]).reset_index(drop=True)


def build_proxy_metric_series(raw_df: pd.DataFrame) -> pd.Series:
    return raw_df["icr_exact"].combine_first(raw_df["icr_proxy"])
