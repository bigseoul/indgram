from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from zombie.common_io import (
    DEFAULT_INPUT_PATH,
    load_input_universe,
    load_parquet_frame,
    save_parquet_frame,
    upsert_rows,
    utc_now,
)

DEFAULT_WR_CHECKPOINT_DIR = Path("zombie/data/checkpoints")
DEFAULT_WR_PROGRESS_PATH = DEFAULT_WR_CHECKPOINT_DIR / "wisereport_fetch_progress.parquet"
DEFAULT_WR_ERROR_PATH = DEFAULT_WR_CHECKPOINT_DIR / "wisereport_fetch_errors.parquet"
DEFAULT_WR_RAW_PARQUET_PATH = DEFAULT_WR_CHECKPOINT_DIR / "wisereport_raw_payload.parquet"
DEFAULT_WR_QUOTE_PATH = DEFAULT_WR_CHECKPOINT_DIR / "wisereport_quote_snapshot.parquet"
DEFAULT_WR_QUOTE_ERROR_PATH = DEFAULT_WR_CHECKPOINT_DIR / "wisereport_quote_errors.parquet"

DEFAULT_WR_FIN_GUBUN = "IFRSS"
DEFAULT_WR_FRQ_TYP = "0"
DEFAULT_WR_RPT = 3

WISE_REPORT_OVERVIEW_URL = "https://navercomp.wisereport.co.kr/company/c1010001.aspx"
WISE_REPORT_PAGE_URL = "https://navercomp.wisereport.co.kr/v2/company/c1040001.aspx"
WISE_REPORT_PAYLOAD_URL = "https://navercomp.wisereport.co.kr/v2/company/cF4002.aspx"

WR_PROGRESS_COLUMNS = (
    "market",
    "stock_code",
    "corp_code",
    "name",
    "rpt",
    "fin_gubun",
    "frq_typ",
    "source_status",
    "processed_at",
)
WR_ERROR_COLUMNS = (
    "market",
    "stock_code",
    "corp_code",
    "name",
    "rpt",
    "fin_gubun",
    "frq_typ",
    "error_type",
    "error_message",
    "processed_at",
)
WR_RAW_COLUMNS = (
    "market",
    "stock_code",
    "corp_code",
    "name",
    "rpt",
    "fin_gubun",
    "frq_typ",
    "payload_json",
    "source_status",
    "fetched_at",
)
WR_QUOTE_COLUMNS = (
    "market",
    "stock_code",
    "corp_code",
    "name",
    "quote_date",
    "current_price",
    "price_change",
    "return_today_pct",
    "high_52w",
    "low_52w",
    "volume",
    "trading_value_krw_100m",
    "beta_52w",
    "return_1m_pct",
    "return_3m_pct",
    "return_6m_pct",
    "return_1y_pct",
    "source_status",
    "fetched_at",
)
WR_QUOTE_ERROR_COLUMNS = (
    "market",
    "stock_code",
    "corp_code",
    "name",
    "error_type",
    "error_message",
    "processed_at",
)


@dataclass(frozen=True)
class WiseReportFetchResult:
    payload_json: str
    source_status: str
    encparam: str


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://finance.naver.com/",
        }
    )
    return session


def empty_progress_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=WR_PROGRESS_COLUMNS)


def empty_error_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=WR_ERROR_COLUMNS)


def empty_raw_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=WR_RAW_COLUMNS)


def empty_quote_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=WR_QUOTE_COLUMNS)


def empty_quote_error_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=WR_QUOTE_ERROR_COLUMNS)


def extract_encparam(page_html: str) -> str:
    patterns = (
        r"encparam\s*:\s*'([^']+)'",
        r'encparam\s*:\s*"([^"]+)"',
        r"encparam=([A-Za-z0-9_=+-]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, page_html)
        if match:
            return match.group(1)
    raise ValueError("encparam not found in WiseReport page")


def build_payload_params(
    stock_code: str,
    encparam: str,
    rpt: int = DEFAULT_WR_RPT,
    fin_gubun: str = DEFAULT_WR_FIN_GUBUN,
    frq_typ: str = DEFAULT_WR_FRQ_TYP,
    cn: str = "",
) -> dict[str, str | int]:
    return {
        "cmp_cd": stock_code,
        "frq": frq_typ,
        "rpt": rpt,
        "finGubun": fin_gubun,
        "frqTyp": frq_typ,
        "cn": cn,
        "encparam": encparam,
    }


def fetch_indicator_page(
    session: requests.Session,
    stock_code: str,
    timeout: float = 20.0,
) -> str:
    response = session.get(
        WISE_REPORT_PAGE_URL,
        params={"cmp_cd": stock_code, "cn": ""},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.text


def fetch_overview_page(
    session: requests.Session,
    stock_code: str,
    timeout: float = 20.0,
) -> str:
    response = session.get(
        WISE_REPORT_OVERVIEW_URL,
        params={"cmp_cd": stock_code, "cn": ""},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.text


def fetch_indicator_payload(
    session: requests.Session,
    stock_code: str,
    rpt: int = DEFAULT_WR_RPT,
    fin_gubun: str = DEFAULT_WR_FIN_GUBUN,
    frq_typ: str = DEFAULT_WR_FRQ_TYP,
    cn: str = "",
    timeout: float = 20.0,
) -> WiseReportFetchResult:
    page_html = fetch_indicator_page(session, stock_code, timeout=timeout)
    encparam = extract_encparam(page_html)
    page_url = f"{WISE_REPORT_PAGE_URL}?cmp_cd={stock_code}&cn={cn}"
    params = build_payload_params(
        stock_code=stock_code,
        encparam=encparam,
        rpt=rpt,
        fin_gubun=fin_gubun,
        frq_typ=frq_typ,
        cn=cn,
    )
    response = session.get(
        WISE_REPORT_PAYLOAD_URL,
        params=params,
        headers={"Referer": page_url},
        timeout=timeout,
    )
    response.raise_for_status()
    payload_json = response.text.strip()
    if not payload_json:
        raise ValueError("empty WiseReport payload")
    return WiseReportFetchResult(payload_json=payload_json, source_status="ok", encparam=encparam)


def fetch_indicator_payload_with_retries(
    session: requests.Session,
    stock_code: str,
    rpt: int = DEFAULT_WR_RPT,
    fin_gubun: str = DEFAULT_WR_FIN_GUBUN,
    frq_typ: str = DEFAULT_WR_FRQ_TYP,
    cn: str = "",
    timeout: float = 20.0,
    request_sleep: float = 0.1,
    max_retries: int = 4,
) -> WiseReportFetchResult:
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            result = fetch_indicator_payload(
                session=session,
                stock_code=stock_code,
                rpt=rpt,
                fin_gubun=fin_gubun,
                frq_typ=frq_typ,
                cn=cn,
                timeout=timeout,
            )
            if request_sleep > 0:
                time.sleep(request_sleep)
            return result
        except Exception as exc:
            last_error = exc
            if attempt == max_retries - 1:
                raise
            time.sleep(min(2**attempt, 8))
    assert last_error is not None
    raise last_error


def fetch_overview_page_with_retries(
    session: requests.Session,
    stock_code: str,
    timeout: float = 20.0,
    request_sleep: float = 0.1,
    max_retries: int = 4,
) -> str:
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            page_html = fetch_overview_page(
                session=session,
                stock_code=stock_code,
                timeout=timeout,
            )
            if request_sleep > 0:
                time.sleep(request_sleep)
            return page_html
        except Exception as exc:
            last_error = exc
            if attempt == max_retries - 1:
                raise
            time.sleep(min(2**attempt, 8))
    assert last_error is not None
    raise last_error


def build_raw_payload_row(
    company_row: dict[str, Any],
    payload_json: str,
    rpt: int = DEFAULT_WR_RPT,
    fin_gubun: str = DEFAULT_WR_FIN_GUBUN,
    frq_typ: str = DEFAULT_WR_FRQ_TYP,
    source_status: str = "ok",
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "market": company_row["market"],
                "stock_code": company_row["stock_code"],
                "corp_code": company_row["corp_code"],
                "name": company_row["name"],
                "rpt": rpt,
                "fin_gubun": fin_gubun,
                "frq_typ": frq_typ,
                "payload_json": payload_json,
                "source_status": source_status,
                "fetched_at": utc_now(),
            }
        ],
        columns=list(WR_RAW_COLUMNS),
    )
