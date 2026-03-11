from __future__ import annotations

import html
import json
import re
from typing import Any

import pandas as pd

WR_LONG_COLUMNS = (
    "market",
    "stock_code",
    "corp_code",
    "name",
    "rpt",
    "fin_gubun",
    "frq_typ",
    "year",
    "period_label",
    "icr",
    "source_status",
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


def parse_payload_json(payload_json: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload_json, dict):
        return payload_json
    text = str(payload_json or "").strip()
    if not text:
        return {}
    return json.loads(text)


def strip_html_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_number(value: Any) -> float | None:
    text = strip_html_text(value)
    if not text:
        return None
    match = re.search(r"[-+]?\d[\d,]*\.?\d*", text)
    if not match:
        return None
    return float(match.group(0).replace(",", ""))


def parse_int(value: Any) -> int | None:
    number = parse_number(value)
    if number is None:
        return None
    return int(round(number))


def split_metric_values(value: Any, expected_parts: int) -> list[str]:
    text = strip_html_text(value)
    parts = [part.strip() for part in text.split("/") if part.strip()]
    if len(parts) < expected_parts:
        return []
    return parts[:expected_parts]


def extract_quote_table(html_text: str) -> dict[str, str]:
    table_match = re.search(r'<table[^>]+id="cTB11"[^>]*>(.*?)</table>', html_text, flags=re.IGNORECASE | re.DOTALL)
    if not table_match:
        raise ValueError("quote table cTB11 not found")

    quote_map: dict[str, str] = {}
    row_pattern = re.compile(
        r"<tr>\s*<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>\s*</tr>",
        flags=re.IGNORECASE | re.DOTALL,
    )
    for heading_html, value_html in row_pattern.findall(table_match.group(1)):
        heading = strip_html_text(heading_html)
        value = strip_html_text(value_html)
        if heading:
            quote_map[heading] = value
    return quote_map


def parse_quote_snapshot(raw_row: dict[str, Any], page_html: str) -> dict[str, Any]:
    quote_map = extract_quote_table(page_html)
    price_parts = split_metric_values(quote_map.get("주가/전일대비/수익률"), 3)
    high_low_parts = split_metric_values(quote_map.get("52Weeks 최고/최저"), 2)
    volume_parts = split_metric_values(quote_map.get("거래량/거래대금"), 2)
    return_parts = split_metric_values(quote_map.get("수익률 (1M/3M/6M/1Y)"), 4)
    quote_date_match = re.search(r"\[기준:(\d{4}\.\d{2}\.\d{2})\]", page_html)

    if not price_parts or not high_low_parts or not volume_parts or not return_parts:
        raise ValueError("required quote metrics missing")

    return {
        "market": raw_row["market"],
        "stock_code": raw_row["stock_code"],
        "corp_code": raw_row["corp_code"],
        "name": raw_row["name"],
        "quote_date": quote_date_match.group(1) if quote_date_match else None,
        "current_price": parse_int(price_parts[0]),
        "price_change": parse_int(price_parts[1]),
        "return_today_pct": parse_number(price_parts[2]),
        "high_52w": parse_int(high_low_parts[0]),
        "low_52w": parse_int(high_low_parts[1]),
        "volume": parse_int(volume_parts[0]),
        "trading_value_krw_100m": parse_number(volume_parts[1]),
        "beta_52w": parse_number(quote_map.get("52주베타")),
        "return_1m_pct": parse_number(return_parts[0]),
        "return_3m_pct": parse_number(return_parts[1]),
        "return_6m_pct": parse_number(return_parts[2]),
        "return_1y_pct": parse_number(return_parts[3]),
        "source_status": "ok",
        "fetched_at": raw_row.get("fetched_at"),
    }


def build_quote_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=list(WR_QUOTE_COLUMNS))
    return pd.DataFrame(rows, columns=list(WR_QUOTE_COLUMNS)).sort_values(["market", "stock_code"]).reset_index(drop=True)


def _is_zero(value: Any) -> bool:
    if value is None or pd.isna(value):
        return False
    return abs(float(value)) < 1e-12


def is_abnormal_trading_row(row: pd.Series | dict[str, Any]) -> bool:
    current_price = row.get("current_price")
    high_52w = row.get("high_52w")
    low_52w = row.get("low_52w")
    return (
        _is_zero(row.get("volume"))
        and _is_zero(row.get("trading_value_krw_100m"))
        and _is_zero(row.get("price_change"))
        and _is_zero(row.get("return_today_pct"))
        and current_price is not None
        and high_52w is not None
        and low_52w is not None
        and not pd.isna(current_price)
        and not pd.isna(high_52w)
        and not pd.isna(low_52w)
        and float(current_price) == float(high_52w) == float(low_52w)
        and _is_zero(row.get("return_1m_pct"))
        and _is_zero(row.get("return_3m_pct"))
        and _is_zero(row.get("return_6m_pct"))
        and _is_zero(row.get("return_1y_pct"))
    )


def filter_result_frame_by_trading_status(result_df: pd.DataFrame, quote_df: pd.DataFrame) -> pd.DataFrame:
    if result_df.empty:
        return result_df.copy()
    if quote_df.empty:
        return result_df.copy()

    filtered_quote_df = quote_df.loc[quote_df["source_status"].eq("ok")].copy()
    if filtered_quote_df.empty:
        return result_df.copy()

    filtered_quote_df["is_abnormal_trading"] = filtered_quote_df.apply(is_abnormal_trading_row, axis=1)
    merged = result_df.merge(
        filtered_quote_df[["stock_code", "is_abnormal_trading"]],
        on="stock_code",
        how="left",
    )
    keep_mask = ~merged["is_abnormal_trading"].fillna(False)
    return merged.loc[keep_mask, result_df.columns].reset_index(drop=True)


def parse_year_from_label(label: Any) -> int | None:
    text = str(label or "")
    match = re.search(r"(20\d{2})/\d{2}", text)
    if match:
        return int(match.group(1))
    return None


def extract_indicator_row(payload: dict[str, Any], indicator_name: str = "이자보상배율") -> dict[str, Any] | None:
    for row in payload.get("DATA", []):
        if str(row.get("ACC_NM", "")).strip() == indicator_name:
            return row
    return None


def parse_payload_record(raw_row: dict[str, Any], indicator_name: str = "이자보상배율") -> list[dict[str, Any]]:
    payload = parse_payload_json(raw_row.get("payload_json", ""))
    period_labels = payload.get("YYMM", [])
    indicator_row = extract_indicator_row(payload, indicator_name=indicator_name)
    if indicator_row is None:
        return []

    rows: list[dict[str, Any]] = []
    for index, label in enumerate(period_labels[:6], start=1):
        year = parse_year_from_label(label)
        if year is None:
            continue
        value = indicator_row.get(f"DATA{index}")
        if value is None or pd.isna(value):
            continue
        rows.append(
            {
                "market": raw_row["market"],
                "stock_code": raw_row["stock_code"],
                "corp_code": raw_row["corp_code"],
                "name": raw_row["name"],
                "rpt": raw_row["rpt"],
                "fin_gubun": raw_row["fin_gubun"],
                "frq_typ": raw_row["frq_typ"],
                "year": year,
                "period_label": str(label),
                "icr": float(value),
                "source_status": raw_row.get("source_status", "ok"),
            }
        )
    return rows


def build_long_frame(raw_payload_df: pd.DataFrame, indicator_name: str = "이자보상배율") -> pd.DataFrame:
    if raw_payload_df.empty:
        return pd.DataFrame(columns=list(WR_LONG_COLUMNS))

    rows: list[dict[str, Any]] = []
    for raw_row in raw_payload_df.to_dict("records"):
        rows.extend(parse_payload_record(raw_row, indicator_name=indicator_name))
    if not rows:
        return pd.DataFrame(columns=list(WR_LONG_COLUMNS))
    long_df = pd.DataFrame(rows, columns=list(WR_LONG_COLUMNS))
    return long_df.sort_values(["market", "stock_code", "year"]).reset_index(drop=True)


def build_result_frame(long_df: pd.DataFrame, years: tuple[int, int, int] = (2024, 2023, 2022)) -> pd.DataFrame:
    ordered_columns = ["market", "stock_code", "corp_code", "name", "icr_2024", "icr_2023", "icr_2022", "icr_avg"]
    if long_df.empty:
        return pd.DataFrame(columns=ordered_columns)

    pivoted = long_df.pivot_table(
        index=["market", "stock_code", "corp_code", "name"],
        columns="year",
        values="icr",
        aggfunc="first",
    ).reset_index()

    for year in years:
        if year not in pivoted.columns:
            pivoted[year] = pd.NA

    rename_map = {years[0]: "icr_2024", years[1]: "icr_2023", years[2]: "icr_2022"}
    pivoted = pivoted.rename(columns=rename_map)
    filtered = pivoted.dropna(subset=["icr_2024", "icr_2023", "icr_2022"]).copy()
    if filtered.empty:
        return filtered.reindex(columns=ordered_columns)

    metric_cols = ["icr_2024", "icr_2023", "icr_2022"]
    filtered = filtered.loc[(filtered[metric_cols] < 1).all(axis=1)].copy()
    filtered["icr_avg"] = filtered[metric_cols].mean(axis=1)
    return filtered.reindex(columns=ordered_columns).sort_values(["icr_avg", "market", "stock_code"]).reset_index(drop=True)
