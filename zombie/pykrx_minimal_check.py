import os
import tempfile
import warnings

os.environ.setdefault(
    "MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "indgram-matplotlib")
)
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API.*",
    category=UserWarning,
)

from pykrx import stock


def run_step(title, fn):
    print(f"\n=== {title} ===")
    try:
        value = fn()
        print("OK")
        print(value)
    except Exception as exc:
        print("FAIL")
        print(f"{type(exc).__name__}: {exc}")


def main():
    run_step("1. 종목명 조회", lambda: stock.get_market_ticker_name("005930"))

    run_step(
        "2. 개별 종목 OHLCV 조회 (2026-03-04 ~ 2026-03-06, 005930)",
        lambda: stock.get_market_ohlcv("20260304", "20260306", "005930").tail(3),
    )

    run_step(
        "3. 최근 영업일 조회 (2026-03-08 기준)",
        lambda: stock.get_nearest_business_day_in_a_week("20260308", prev=True),
    )

    run_step(
        "4. 티커 목록 조회 (2025-03-07, KOSDAQ)",
        lambda: {
            "count": len(tickers := stock.get_market_ticker_list("20250307", market="KOSDAQ")),
            "sample": tickers[:10],
        },
    )

    run_step(
        "5. 전종목 OHLCV 조회 (2025-03-07, KOSDAQ)",
        lambda: stock.get_market_ohlcv("20250307", market="KOSDAQ").head(5),
    )

    run_step(
        "6. 외국인 보유율/상장주식수 조회 (2025-03-07, KOSDAQ)",
        lambda: stock.get_exhaustion_rates_of_foreign_investment("20250307", "KOSDAQ").head(5),
    )

    run_step(
        "7. 개별 종목 시가총액 조회 (2025-12-01 ~ 2026-03-06, 005930)",
        lambda: stock.get_market_cap("20251201", "20260306", "005930").tail(5),
    )


if __name__ == "__main__":
    main()
