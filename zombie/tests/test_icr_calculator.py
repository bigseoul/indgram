from __future__ import annotations

import math

import pandas as pd

from zombie import icr_calculator


def test_parse_amount_handles_parentheses_and_commas() -> None:
    assert icr_calculator.parse_amount("(1,234)") == -1234
    assert icr_calculator.parse_amount("2,500") == 2500
    assert icr_calculator.parse_amount("") is None


def test_amount_from_row_preserves_zero_and_does_not_fallback() -> None:
    row = pd.Series({"thstrm_amount": "0", "thstrm_add_amount": "999"})

    assert icr_calculator.amount_from_row(row) == 0


def test_amount_from_row_uses_fallback_only_for_blank_values() -> None:
    row = pd.Series({"thstrm_amount": "", "thstrm_add_amount": "111"})

    assert icr_calculator.amount_from_row(row) == 111


def test_build_raw_record_prefers_is_row_and_computes_exact_and_proxy() -> None:
    frame = pd.DataFrame(
        [
            {"sj_div": "BS", "account_nm": "영업이익", "account_id": "", "ord": "1", "thstrm_amount": "999"},
            {"sj_div": "IS", "account_nm": "영업이익", "account_id": "", "ord": "2", "thstrm_amount": "100"},
            {"sj_div": "IS", "account_nm": "이자비용", "account_id": "InterestExpense", "ord": "1", "thstrm_amount": "25"},
            {"sj_div": "IS", "account_nm": "금융비용", "account_id": "FinanceCosts", "ord": "1", "thstrm_amount": "50"},
        ]
    )

    record = icr_calculator.build_raw_record(
        company_row={"market": "KOSPI", "stock_code": "005930", "corp_code": "00126380", "name": "삼성전자"},
        year=2024,
        frame=frame,
        fs_div_used="CFS",
        base_status="ok_cfs",
        report_code="11011",
    )

    assert record["operating_profit"] == 100
    assert record["interest_expense_exact"] == 25
    assert record["finance_cost_proxy"] == 50
    assert record["icr_exact"] == 4
    assert record["icr_proxy"] == 2
    assert record["source_status"] == "ok_cfs"


def test_build_raw_record_marks_missing_exact_interest() -> None:
    frame = pd.DataFrame(
        [
            {"sj_div": "IS", "account_nm": "영업이익", "account_id": "", "ord": "1", "thstrm_amount": "100"},
            {"sj_div": "IS", "account_nm": "금융비용", "account_id": "FinanceCosts", "ord": "1", "thstrm_amount": "50"},
        ]
    )

    record = icr_calculator.build_raw_record(
        company_row={"market": "KOSPI", "stock_code": "005930", "corp_code": "00126380", "name": "삼성전자"},
        year=2024,
        frame=frame,
        fs_div_used="CFS",
        base_status="ok_cfs",
        report_code="11011",
    )

    assert record["interest_expense_exact"] is None
    assert record["finance_cost_proxy"] == 50
    assert record["source_status"] == "missing_exact_interest"
    assert record["icr_exact"] is None
    assert record["icr_proxy"] == 2


def test_calculate_icr_handles_negative_and_zero_cases() -> None:
    assert icr_calculator.calculate_icr(-100, 20) == -5
    assert icr_calculator.calculate_icr(0, 20) == 0
    assert icr_calculator.calculate_icr(100, 0) is None
    assert icr_calculator.calculate_icr(100, -1) is None


def test_build_result_frame_filters_three_year_sub_one() -> None:
    raw = pd.DataFrame(
        [
            {"market": "KOSPI", "stock_code": "111111", "corp_code": "C1", "name": "A", "year": 2022, "icr_exact": 0.5},
            {"market": "KOSPI", "stock_code": "111111", "corp_code": "C1", "name": "A", "year": 2023, "icr_exact": -0.2},
            {"market": "KOSPI", "stock_code": "111111", "corp_code": "C1", "name": "A", "year": 2024, "icr_exact": 0.7},
            {"market": "KOSDAQ", "stock_code": "222222", "corp_code": "C2", "name": "B", "year": 2022, "icr_exact": 0.5},
            {"market": "KOSDAQ", "stock_code": "222222", "corp_code": "C2", "name": "B", "year": 2023, "icr_exact": 1.1},
            {"market": "KOSDAQ", "stock_code": "222222", "corp_code": "C2", "name": "B", "year": 2024, "icr_exact": 0.3},
        ]
    )

    result = icr_calculator.build_result_frame(raw, "icr_exact")

    assert result.to_dict("records") == [
        {
            "market": "KOSPI",
            "stock_code": "111111",
            "corp_code": "C1",
            "name": "A",
            "icr_2024": 0.7,
            "icr_2023": -0.2,
            "icr_2022": 0.5,
            "icr_avg": (0.7 - 0.2 + 0.5) / 3,
        }
    ]


def test_build_proxy_metric_series_prefers_exact_then_proxy() -> None:
    raw = pd.DataFrame(
        [
            {"icr_exact": 0.3, "icr_proxy": 0.9},
            {"icr_exact": math.nan, "icr_proxy": 0.8},
        ]
    )

    series = icr_calculator.build_proxy_metric_series(raw)

    assert list(series) == [0.3, 0.8]


def test_build_excluded_rows_creates_one_row_per_year() -> None:
    excluded = pd.DataFrame([{"market": "KOSPI", "stock_code": "001465", "corp_code": "", "name": "BYC우"}])

    rows = icr_calculator.build_excluded_rows(excluded, years=(2022, 2023), report_code="11011")

    assert rows[["stock_code", "year", "source_status"]].to_dict("records") == [
        {"stock_code": "001465", "year": 2022, "source_status": "excluded_no_corp_code"},
        {"stock_code": "001465", "year": 2023, "source_status": "excluded_no_corp_code"},
    ]
