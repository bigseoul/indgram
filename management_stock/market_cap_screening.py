"""
시가총액 관리종목 지정 우려기업 스크리닝
- 기준: 2026년 7월 1일 신규 기준 적용
  - 코스닥: 200억 원 미만
  - 코스피: 300억 원 미만
- 등급 기준
  - 🔴 위험: 기준치 미달
  - 🟠 경고: 기준치 이상 ~ 130% 미만
  - 🟡 주의: 130% 이상 ~ 200% 미만
  - 🟢 안전: 200% 이상
- ETF/ETN/스팩/리츠 제외
"""

import os
import tempfile
import time
import warnings
from datetime import datetime, timedelta

import pandas as pd

os.environ.setdefault(
    "MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "indgram-matplotlib")
)
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API.*",
    category=UserWarning,
)

from pykrx import stock

THRESHOLD = {
    "KOSDAQ": 20_000_000_000,  # 200억
    "KOSPI": 30_000_000_000,  # 300억
}

WARNING_MULTIPLIER = 2.0
WARNING_RATIO = 1.3
TREND_LOOKBACK_DAYS = 90
REQUEST_SLEEP = 0.3


def is_excluded(name: str) -> bool:
    exclude_keywords = ["SPAC", "스팩", "ETF", "ETN", "리츠", "REIT"]
    return any(keyword in name for keyword in exclude_keywords)


def shift_days(date: str, days: int) -> str:
    current = datetime.strptime(date, "%Y%m%d") + timedelta(days=days)
    return current.strftime("%Y%m%d")


def normalize_business_day(base_date: str) -> str:
    current = datetime.strptime(base_date, "%Y%m%d")
    while current.weekday() >= 5:
        current -= timedelta(days=1)
    return current.strftime("%Y%m%d")


def resolve_base_date() -> str:
    """
    pykrx 당일 데이터는 장 마감 후 반영되므로
    평일 18시 이전이면 전 영업일을 우선 사용
    """
    now = datetime.now()
    today = now.strftime("%Y%m%d")

    if now.weekday() < 5 and now.hour < 18:
        return normalize_business_day(shift_days(today, -1))

    return normalize_business_day(today)


def classify_risk(row: pd.Series) -> str:
    threshold = THRESHOLD[row["시장"]]
    cap = row["시가총액"]
    ratio = cap / threshold if threshold else 0

    if cap < threshold:
        return "🔴 위험 (7월 30거래일 카운트 대상)"
    if ratio < WARNING_RATIO:
        return "🟠 경고 (10~20% 하락 시 미달 가능)"
    if ratio < WARNING_MULTIPLIER:
        return "🟡 주의 (한 달 급락 시 경고권 진입 가능)"
    return "🟢 안전 (단기 우려 낮음)"


def get_snapshot(market: str, base_date: str) -> pd.DataFrame:
    """
    공개 API만 사용:
    1) get_market_ohlcv(date, market)으로 종가/거래량/거래대금 조회
    2) get_exhaustion_rates_of_foreign_investment(date, market)으로 상장주식수 조회
    3) 시가총액 = 종가 * 상장주식수
    """
    print(f"\n[{market}] 전종목 스냅샷 조회 중... (기준일: {base_date})")

    price_df = stock.get_market_ohlcv(base_date, market=market)
    share_df = stock.get_exhaustion_rates_of_foreign_investment(base_date, market=market)

    if price_df.empty:
        raise RuntimeError(f"{market} 가격 데이터 조회 실패: {base_date}")
    if share_df.empty:
        raise RuntimeError(f"{market} 상장주식수 데이터 조회 실패: {base_date}")

    required_price_cols = {"종가", "거래량", "거래대금"}
    required_share_cols = {"상장주식수"}

    if not required_price_cols.issubset(price_df.columns):
        raise RuntimeError(
            f"{market} 가격 데이터 컬럼 이상: {list(price_df.columns)}"
        )
    if not required_share_cols.issubset(share_df.columns):
        raise RuntimeError(
            f"{market} 상장주식수 데이터 컬럼 이상: {list(share_df.columns)}"
        )

    df = price_df[["종가", "거래량", "거래대금"]].join(
        share_df[["상장주식수"]],
        how="inner",
    )

    if df.empty:
        raise RuntimeError(f"{market} 가격/상장주식수 조인 결과가 비어 있음: {base_date}")

    df["시가총액"] = df["종가"] * df["상장주식수"]

    tickers = df.index.tolist()
    names = {ticker: stock.get_market_ticker_name(ticker) for ticker in tickers}
    df["종목명"] = df.index.map(names)

    df = df[~df["종목명"].apply(is_excluded)].copy()
    df["시장"] = market

    return df[["종목명", "시장", "종가", "상장주식수", "거래량", "거래대금", "시가총액"]]


def get_trend(ticker: str, threshold: int, base_date: str) -> dict:
    try:
        from_date = (
            datetime.strptime(base_date, "%Y%m%d") - timedelta(days=TREND_LOOKBACK_DAYS)
        ).strftime("%Y%m%d")
        df = stock.get_market_cap(from_date, base_date, ticker)

        if df.empty or "시가총액" not in df.columns:
            return {"추세": "데이터없음", "연속미달일": 0, "60일대비(%)": None}

        df["미달"] = df["시가총액"] < threshold

        consecutive = 0
        for value in reversed(df["미달"].tolist()):
            if value:
                consecutive += 1
            else:
                break

        first_cap = df["시가총액"].iloc[0]
        last_cap = df["시가총액"].iloc[-1]
        change_pct = None if first_cap <= 0 else (last_cap - first_cap) / first_cap * 100

        if change_pct is None:
            trend = "데이터없음"
        elif change_pct < -10:
            trend = "하락"
        elif change_pct <= 10:
            trend = "보합"
        else:
            trend = "상승"

        return {
            "추세": trend,
            "연속미달일": consecutive,
            "60일대비(%)": round(change_pct, 1) if change_pct is not None else None,
        }
    except Exception:
        return {"추세": "오류", "연속미달일": 0, "60일대비(%)": None}


def run():
    base_date = resolve_base_date()
    results = []

    for market in ["KOSDAQ", "KOSPI"]:
        df = get_snapshot(market, base_date)
        threshold = THRESHOLD[market]

        risk_df = df[df["시가총액"] < threshold * WARNING_MULTIPLIER].copy()
        risk_df["위험등급"] = risk_df.apply(classify_risk, axis=1)

        print(f"[{market}] 위험군 {len(risk_df)}개 종목 추세 분석 중...")

        for ticker in risk_df.index:
            trend_info = get_trend(ticker, threshold, base_date)
            risk_df.loc[ticker, "추세"] = trend_info["추세"]
            risk_df.loc[ticker, "연속미달일"] = trend_info["연속미달일"]
            risk_df.loc[ticker, "60일대비(%)"] = trend_info["60일대비(%)"]
            time.sleep(REQUEST_SLEEP)

        results.append(risk_df)

    final = pd.concat(results).sort_values(["위험등급", "시가총액"])
    final["시가총액(억)"] = (final["시가총액"] / 1e8).round(1)

    output = final[
        [
            "종목명",
            "시장",
            "시가총액(억)",
            "위험등급",
            "추세",
            "연속미달일",
            "60일대비(%)",
        ]
    ].copy()
    output.index.name = "티커"

    output.to_csv("market_cap_risk.csv", encoding="utf-8-sig")

    print("\n완료: market_cap_risk.csv 저장")
    print(f"기준일: {base_date}")
    print(output.to_string())

    return output


if __name__ == "__main__":
    run()
