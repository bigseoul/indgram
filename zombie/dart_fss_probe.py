from __future__ import annotations

import argparse
import contextlib
import io
from pathlib import Path
from typing import Any

import pandas as pd

from zombie.dart_fetcher import get_default_api_key

OPERATING_INCOME_CONCEPTS = ("dart_OperatingIncomeLoss", "ifrs-full_OperatingIncomeLoss")
FINANCE_COST_CONCEPTS = ("ifrs-full_FinanceCosts",)
INTEREST_EXPENSE_CONCEPTS = ("ifrs-full_InterestExpense",)
DEFAULT_PROXY_SOURCE = Path("zombie_2026_proxy.csv")
DEFAULT_OUTPUT_PATH = Path("zombie/data/dart_fss_interest_probe_top20.csv")


def _load_dart_fss():
    import dart_fss as dart

    return dart


def _context_rank(label_tuple: tuple[str, ...], separate: bool) -> tuple[int, int, int, str]:
    if not isinstance(label_tuple, tuple):
        label_tuple = (str(label_tuple),)

    exact_target = ("Separate",) if separate else ("Consolidated",)
    score_exact = 0 if label_tuple == exact_target else 1
    score_contains = 0 if exact_target[0] in label_tuple else 1
    score_len = len(label_tuple)
    return (score_exact, score_contains, score_len, " | ".join(label_tuple))


def select_best_context_value(values: dict[Any, Any], separate: bool) -> tuple[float | None, str]:
    candidates: list[tuple[tuple[int, int, int, str], float, str]] = []
    for raw_key, raw_value in values.items():
        if pd.isna(raw_value):
            continue
        if not isinstance(raw_key, tuple) or len(raw_key) != 2:
            continue
        _, context = raw_key
        if not isinstance(context, tuple):
            context = (str(context),)
        label = " | ".join(str(item) for item in context)
        candidates.append((_context_rank(tuple(str(item) for item in context), separate), float(raw_value), label))

    if not candidates:
        return None, ""

    best = sorted(candidates, key=lambda item: item[0])[0]
    return best[1], best[2]


def extract_concept_value(statement: Any, concept_ids: tuple[str, ...], separate: bool) -> tuple[float | None, str, str]:
    for concept_id in concept_ids:
        values = statement.get_value_by_concept_id(concept_id, lang="en")
        amount, context_label = select_best_context_value(values, separate=separate)
        if amount is not None:
            return amount, concept_id, context_label
    return None, "", ""


def fetch_income_statement_statement(corp_code: str, year: int, separate: bool) -> Any:
    dart = _load_dart_fss()
    corp_list = dart.get_corp_list()
    corp = corp_list.find_by_corp_code(corp_code=corp_code)
    reports = corp.search_filings(
        bgn_de=f"{year}0101",
        end_de=f"{year}1231",
        pblntf_detail_ty="a001",
        last_reprt_at="Y",
    )
    if len(reports) == 0:
        raise ValueError(f"no annual report found for corp_code={corp_code} year={year}")

    report = reports[0]
    with contextlib.redirect_stdout(io.StringIO()):
        xbrl = report.xbrl
    statements = xbrl.get_income_statement(separate=separate)
    if not statements:
        raise ValueError(f"no income statement table for corp_code={corp_code} year={year} separate={separate}")
    return statements[0]


def probe_company_year(row: dict[str, str], year: int) -> dict[str, Any]:
    last_error = ""
    for separate, fs_div in ((False, "CFS"), (True, "OFS")):
        try:
            statement = fetch_income_statement_statement(row["corp_code"], year, separate=separate)
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            continue

        operating_profit, operating_concept, operating_context = extract_concept_value(
            statement,
            OPERATING_INCOME_CONCEPTS,
            separate=separate,
        )
        finance_costs, finance_concept, finance_context = extract_concept_value(
            statement,
            FINANCE_COST_CONCEPTS,
            separate=separate,
        )
        interest_expense, interest_concept, interest_context = extract_concept_value(
            statement,
            INTEREST_EXPENSE_CONCEPTS,
            separate=separate,
        )

        return {
            "market": row["market"],
            "stock_code": row["stock_code"],
            "corp_code": row["corp_code"],
            "name": row["name"],
            "year": year,
            "fs_div": fs_div,
            "operating_profit": operating_profit,
            "operating_concept_id": operating_concept,
            "operating_context": operating_context,
            "finance_costs": finance_costs,
            "finance_costs_concept_id": finance_concept,
            "finance_costs_context": finance_context,
            "interest_expense": interest_expense,
            "interest_expense_concept_id": interest_concept,
            "interest_expense_context": interest_context,
            "has_finance_costs": finance_costs is not None,
            "has_interest_expense": interest_expense is not None,
            "error": "",
        }

    return {
        "market": row["market"],
        "stock_code": row["stock_code"],
        "corp_code": row["corp_code"],
        "name": row["name"],
        "year": year,
        "fs_div": "",
        "operating_profit": None,
        "operating_concept_id": "",
        "operating_context": "",
        "finance_costs": None,
        "finance_costs_concept_id": "",
        "finance_costs_context": "",
        "interest_expense": None,
        "interest_expense_concept_id": "",
        "interest_expense_context": "",
        "has_finance_costs": False,
        "has_interest_expense": False,
        "error": last_error,
    }


def load_probe_targets(source_path: str | Path, limit: int) -> pd.DataFrame:
    df = pd.read_csv(source_path, encoding="utf-8-sig", dtype=str)
    required = {"market", "stock_code", "corp_code", "name"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"target CSV is missing columns: {sorted(missing)}")
    return df.loc[:, ["market", "stock_code", "corp_code", "name"]].head(limit).copy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe dart-fss XBRL concept availability.")
    parser.add_argument("--source-path", type=Path, default=DEFAULT_PROXY_SOURCE)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--years", nargs="+", type=int, default=[2022, 2023, 2024])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_key = get_default_api_key()
    if not api_key:
        print("DART API key not found.")
        return 1

    dart = _load_dart_fss()
    dart.set_api_key(api_key=api_key)
    targets = load_probe_targets(args.source_path, limit=args.limit)

    rows: list[dict[str, Any]] = []
    total = len(targets) * len(args.years)
    index = 0
    for target in targets.to_dict("records"):
        for year in args.years:
            index += 1
            print(f"probe {index}/{total}: {target['stock_code']} {target['name']} {year}")
            rows.append(probe_company_year(target, year))

    output_df = pd.DataFrame(rows)
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(args.output_path, index=False, encoding="utf-8-sig")

    print()
    print(f"output: {args.output_path}")
    print(f"rows: {len(output_df)}")
    print("has_interest_expense:", int(output_df["has_interest_expense"].sum()))
    print("has_finance_costs:", int(output_df["has_finance_costs"].sum()))
    print("error_rows:", int(output_df["error"].astype(str).str.strip().ne("").sum()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
