from __future__ import annotations

import json

import pandas as pd
import pytest

from zombie import wisereport_parser


def build_payload_json() -> str:
    payload = {
        "YYMM": [
            "2020/12<br />(IFRS별도)",
            "2021/12<br />(IFRS별도)",
            "2022/12<br />(IFRS별도)",
            "2023/12<br />(IFRS별도)",
            "2024/12<br />(IFRS별도)",
            "2025/12(E)<br />(IFRS별도)",
        ],
        "DATA": [
            {
                "ACC_NM": "부채비율",
                "DATA1": 10,
                "DATA2": 11,
                "DATA3": 12,
                "DATA4": 13,
                "DATA5": 14,
                "DATA6": 15,
            },
            {
                "ACC_NM": "이자보상배율",
                "DATA1": 1.5,
                "DATA2": 0.9,
                "DATA3": 0.8,
                "DATA4": 0.7,
                "DATA5": 0.6,
                "DATA6": None,
            },
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def build_quote_html() -> str:
    return """
    <div class="header-table">
      <p>[기준:2026.03.10]</p>
    </div>
    <table class="gHead" id="cTB11">
      <tbody>
        <tr><th scope="row" class="txt">주가/전일대비/수익률</th><td class="num"><strong>2,370</strong>원 / <span class="cBk">0원</span> / <span class="cBk">0%</span></td></tr>
        <tr><th scope="row" class="txt">52Weeks 최고/최저</th><td class="num">2,370원 / 2,370원</td></tr>
        <tr><th scope="row" class="txt">액면가</th><td class="num">500원</td></tr>
        <tr><th scope="row" class="txt">거래량/거래대금</th><td class="num">0주 / 0억원</td></tr>
        <tr><th scope="row" class="txt">시가총액</th><td class="num">1,161억원</td></tr>
        <tr><th scope="row" class="txt">52주베타</th><td class="num">0</td></tr>
        <tr><th scope="row" class="txt">발행주식수/유동비율</th><td class="num">48,972,158주 / 69.34%</td></tr>
        <tr><th scope="row" class="txt">외국인지분율</th><td class="num">1.55%</td></tr>
        <tr><th scope="row" class="txt noline-bottom">수익률 <span class="span-sub">(1M/3M/6M/1Y)</span></th><td class="num noline-bottom"><span class="cBk">0%</span>/ <span class="cBk">0%</span>/ <span class="cBk">0%</span>/ <span class="cBk">0%</span></td></tr>
      </tbody>
    </table>
    """


def test_parse_payload_record_extracts_interest_coverage_years() -> None:
    raw_row = {
        "market": "KOSDAQ",
        "stock_code": "032940",
        "corp_code": "00123456",
        "name": "원익",
        "rpt": 3,
        "fin_gubun": "IFRSS",
        "frq_typ": "0",
        "payload_json": build_payload_json(),
        "source_status": "ok",
    }

    rows = wisereport_parser.parse_payload_record(raw_row)

    assert rows[-3:] == [
        {
            "market": "KOSDAQ",
            "stock_code": "032940",
            "corp_code": "00123456",
            "name": "원익",
            "rpt": 3,
            "fin_gubun": "IFRSS",
            "frq_typ": "0",
            "year": 2022,
            "period_label": "2022/12<br />(IFRS별도)",
            "icr": 0.8,
            "source_status": "ok",
        },
        {
            "market": "KOSDAQ",
            "stock_code": "032940",
            "corp_code": "00123456",
            "name": "원익",
            "rpt": 3,
            "fin_gubun": "IFRSS",
            "frq_typ": "0",
            "year": 2023,
            "period_label": "2023/12<br />(IFRS별도)",
            "icr": 0.7,
            "source_status": "ok",
        },
        {
            "market": "KOSDAQ",
            "stock_code": "032940",
            "corp_code": "00123456",
            "name": "원익",
            "rpt": 3,
            "fin_gubun": "IFRSS",
            "frq_typ": "0",
            "year": 2024,
            "period_label": "2024/12<br />(IFRS별도)",
            "icr": 0.6,
            "source_status": "ok",
        },
    ]


def test_build_result_frame_matches_existing_output_schema() -> None:
    long_df = pd.DataFrame(
        [
            {"market": "KOSDAQ", "stock_code": "032940", "corp_code": "C1", "name": "원익", "year": 2022, "icr": 0.8},
            {"market": "KOSDAQ", "stock_code": "032940", "corp_code": "C1", "name": "원익", "year": 2023, "icr": 0.7},
            {"market": "KOSDAQ", "stock_code": "032940", "corp_code": "C1", "name": "원익", "year": 2024, "icr": 0.6},
            {"market": "KOSPI", "stock_code": "005930", "corp_code": "C2", "name": "삼성전자", "year": 2022, "icr": 1.5},
            {"market": "KOSPI", "stock_code": "005930", "corp_code": "C2", "name": "삼성전자", "year": 2023, "icr": 1.6},
            {"market": "KOSPI", "stock_code": "005930", "corp_code": "C2", "name": "삼성전자", "year": 2024, "icr": 1.7},
        ]
    )

    result = wisereport_parser.build_result_frame(long_df)

    records = result.to_dict("records")

    assert len(records) == 1
    assert records[0]["market"] == "KOSDAQ"
    assert records[0]["stock_code"] == "032940"
    assert records[0]["corp_code"] == "C1"
    assert records[0]["name"] == "원익"
    assert records[0]["icr_2024"] == 0.6
    assert records[0]["icr_2023"] == 0.7
    assert records[0]["icr_2022"] == 0.8
    assert records[0]["icr_avg"] == pytest.approx(0.7)


def test_parse_quote_snapshot_extracts_quote_metrics() -> None:
    row = wisereport_parser.parse_quote_snapshot(
        {
            "market": "KOSDAQ",
            "stock_code": "041590",
            "corp_code": "00297448",
            "name": "플래스크",
            "fetched_at": "2026-03-11T00:00:00+09:00",
        },
        build_quote_html(),
    )

    assert row["quote_date"] == "2026.03.10"
    assert row["current_price"] == 2370
    assert row["price_change"] == 0
    assert row["return_today_pct"] == 0.0
    assert row["high_52w"] == 2370
    assert row["low_52w"] == 2370
    assert row["volume"] == 0
    assert row["trading_value_krw_100m"] == 0.0
    assert row["return_1y_pct"] == 0.0


def test_is_abnormal_trading_row_flags_zeroed_quote_snapshot() -> None:
    row = pd.Series(
        wisereport_parser.parse_quote_snapshot(
            {
                "market": "KOSDAQ",
                "stock_code": "041590",
                "corp_code": "00297448",
                "name": "플래스크",
                "fetched_at": "2026-03-11T00:00:00+09:00",
            },
            build_quote_html(),
        )
    )

    assert wisereport_parser.is_abnormal_trading_row(row) is True


def test_filter_result_frame_by_trading_status_excludes_abnormal_trading() -> None:
    result_df = pd.DataFrame(
        [
            {"market": "KOSDAQ", "stock_code": "041590", "corp_code": "C1", "name": "플래스크", "icr_2024": 0.5, "icr_2023": 0.4, "icr_2022": 0.3, "icr_avg": 0.4},
            {"market": "KOSDAQ", "stock_code": "032940", "corp_code": "C2", "name": "원익", "icr_2024": 0.6, "icr_2023": 0.7, "icr_2022": 0.8, "icr_avg": 0.7},
        ]
    )
    quote_df = pd.DataFrame(
        [
            wisereport_parser.parse_quote_snapshot(
                {
                    "market": "KOSDAQ",
                    "stock_code": "041590",
                    "corp_code": "C1",
                    "name": "플래스크",
                    "fetched_at": "2026-03-11T00:00:00+09:00",
                },
                build_quote_html(),
            ),
            {
                "market": "KOSDAQ",
                "stock_code": "032940",
                "corp_code": "C2",
                "name": "원익",
                "quote_date": "2026.03.10",
                "current_price": 10000,
                "price_change": 100,
                "return_today_pct": 1.0,
                "high_52w": 12000,
                "low_52w": 8000,
                "volume": 123456,
                "trading_value_krw_100m": 12.3,
                "beta_52w": 1.1,
                "return_1m_pct": 5.0,
                "return_3m_pct": 6.0,
                "return_6m_pct": 7.0,
                "return_1y_pct": 8.0,
                "source_status": "ok",
                "fetched_at": "2026-03-11T00:00:00+09:00",
            },
        ]
    )

    filtered = wisereport_parser.filter_result_frame_by_trading_status(result_df, quote_df)

    assert filtered["stock_code"].tolist() == ["032940"]
