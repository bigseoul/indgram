# PRD — 시가총액 관리종목 지정 우려기업 선별 시스템
**Market Cap Risk Screening System** | v1.1 | 2026년 3월

| 항목 | 내용 |
|------|------|
| 목적 | 2026년 7월 1일 신시가총액 기준 적용 시 관리종목 지정 우려기업을 선제적으로 추리는 수동 실행형 리서치 시스템 |
| 운영 방식 | 파일 단위 CLI 실행 |
| 현재 범위 | 티커 수집, 일별 스냅샷 수집, 위험/경고 후보 필터링, 후보군 45거래일 이력 수집 |
| 후속 범위 | 차트 및 리포트 생성 |

---

## 1. 배경

2026년 7월 1일부터 시가총액 관련 관리종목 지정 기준이 강화된다.

| 시장 | 2026.7.1 기준 |
|------|---------------|
| 코스닥 | 200억 원 미만 |
| 코스피 | 300억 원 미만 |

핵심 판단 규칙은 아래와 같다.

- 관리종목 지정: 30거래일 연속 기준 미달
- 상장폐지: 지정 후 90거래일 내 연속 45거래일 이상 회복 실패

이 시스템의 목적은 전 종목을 매일 장 마감 후 스냅샷으로 기록하고, 그중 위험도가 높은 종목만 따로 추려 45거래일 이력을 모아 분석 가능한 형태로 남기는 것이다.

---

## 2. 목표

- 코스피·코스닥 전 종목 티커를 수집한다.
- 특정 `base_date` 기준 전 종목 스냅샷을 수집한다.
- 스냅샷에서 `위험`과 `경고` 수준 종목만 추린다.
- 필터링된 후보 티커에 대해 45거래일 이력을 수집한다.
- 결과를 CSV와 parquet 중심으로 남긴다.

v1에서는 차트를 핵심 범위에 포함하지 않는다. 차트는 데이터 구조가 안정된 뒤 후속 작업으로 분리한다.

---

## 3. 범위

### 3.1 포함

- 티커 수집
- 전 종목 일별 스냅샷 수집
- 위험/경고 후보 필터링
- 후보군 45거래일 이력 수집
- CSV / parquet 산출물 생성

### 3.2 제외

- 동전주 요건
- 거래정지 / 관리종목 / 상장폐지사유 상태 수집
- 자동 스케줄러 운영
- HTML 리포트
- 시각화 차트 생성

---

## 4. 파일별 책임

각 파일은 하나의 기능만 담당한다.

### 4.1 티커 수집

- 파일: `management_stock/collect_market_tickers.py`
- 역할: 코스피·코스닥 전 종목 티커 목록 수집
- 출력:
  - `management_stock/data/market_tickers_YYYYMMDD.csv`
  - `management_stock/data/market_tickers_YYYYMMDD.parquet`

출력 컬럼:

| 컬럼 | 설명 |
|------|------|
| market | `KOSPI` / `KOSDAQ` |
| ticker | 6자리 종목코드 |
| name | 종목명 |
| isin | ISIN |

### 4.2 일별 스냅샷 수집

- 파일: `management_stock/market_cap_screening.py`
- 역할: 특정 `base_date` 기준 전 종목 종가와 시가총액 스냅샷 생성
- 입력:
  - `market_tickers_YYYYMMDD.csv` 또는 parquet
- 출력:
  - `management_stock/data/market_snapshot_YYYYMMDD.csv`
  - `management_stock/data/market_snapshot_YYYYMMDD.parquet`

출력 컬럼:

| 컬럼 | 설명 |
|------|------|
| market | `KOSPI` / `KOSDAQ` |
| ticker | 6자리 종목코드 |
| name | 종목명 |
| base_date | 기준일자 `YYYYMMDD` |
| close_price | 기준일 종가 |
| listed_shares | 상장주식수 |
| market_cap | `close_price × listed_shares` |

### 4.3 위험/경고 후보 필터링

- 파일: `management_stock/filter_warning_candidates.py`
- 역할: 일별 스냅샷에서 위험/경고 수준 종목만 추림
- 입력:
  - `management_stock/data/market_snapshot_YYYYMMDD.csv`
- 출력:
  - `management_stock/data/warning_candidates_YYYYMMDD.csv`

필터링 조건:

- 제외 키워드: `ETF`, `ETN`, `SPAC`, `스팩`, `리츠`, `REIT`
- 위험:
  - 코스닥 `200억 미만`
  - 코스피 `300억 미만`
- 경고:
  - 코스닥 `200억 이상 260억 미만`
  - 코스피 `300억 이상 390억 미만`

출력 컬럼 예시:

| 컬럼 | 설명 |
|------|------|
| market | 시장 |
| ticker | 종목코드 |
| name | 종목명 |
| base_date | 기준일 |
| close_price | 종가 |
| listed_shares | 상장주식수 |
| market_cap | 시가총액 |
| risk_level | `위험` / `경고` |
| threshold | 시장별 기준치 |
### 4.4 후보군 45거래일 이력 수집

- 파일: 미구현, 신규 작성 예정
- 역할: `warning_candidates_YYYYMMDD.csv`에 포함된 종목들의 45거래일 이력을 수집
- 입력:
  - `management_stock/data/warning_candidates_YYYYMMDD.csv`
- 출력:
  - 예시: `management_stock/data/warning_history_YYYYMMDD.csv`
  - 예시: `management_stock/data/warning_history_YYYYMMDD.parquet`

중요 원칙:

- `warning_candidates_YYYYMMDD.csv`는 특정 기준일 스냅샷에서 생성된 파일이므로, 기본적으로 종목당 1행을 전제로 한다.
- 수집 기간 기본값은 `45거래일`
- `45거래일`은 `base_date`를 포함한 실제 거래일 45개를 의미한다.
- 달력 기준으로 하루씩 거슬러 올라가는 방식은 사용하지 않는다.
- 현재는 테스트 목적이므로 사용자가 기간을 직접 지정할 수 있어야 함
- 실제 운영 시에는 장 마감 후 실행을 전제로 함
- 누적 파일 구조로 확장 가능해야 함

이력 데이터는 long-format으로 저장한다.

예시:

```csv
market,ticker,name,base_date,close_price,listed_shares,market_cap
KOSDAQ,065650,메디프론,20260105,980,42000000,41160000000
KOSDAQ,065650,메디프론,20260106,955,42000000,40110000000
KOSDAQ,065650,메디프론,20260107,930,42000000,39060000000
KOSPI,000040,KR모터스,20260105,385,86375184,33254445840
KOSPI,000040,KR모터스,20260106,372,86375184,32131568448
```

---

## 5. 핵심 로직

### 5.1 기준일

- 모든 판단은 `base_date` 기준으로 수행한다.
- `base_date`는 해당 날짜의 종가 스냅샷을 의미한다.
- 실제 운영 시에는 장 마감 후 실행한다.
- 이력 수집 시 `base_date`를 포함한 최근 `45거래일`을 사용한다.
- 예를 들어 `base_date`가 `20260309`이면, `20260308`처럼 달력상 전날이 아니라 실제 거래가 있었던 날짜 목록을 기준으로 직전 거래일을 계산한다.

### 5.2 영업일 처리

- 이력 수집은 거래일 데이터 자체를 기준으로 한다.
- 구현 시에는 특정 종목의 일별 시세 데이터를 `base_date`까지 넉넉한 기간으로 조회한 뒤 마지막 `45행`을 사용한다.
- 주말, 공휴일, 임시휴장일은 거래 데이터에 없으므로 자동 제외된다.
- 따라서 시작일을 달력 날짜로 직접 계산해 고정하지 않는다.

### 5.3 등급 정의

2026년 7월 1일 신규 기준을 사용한다.

| 등급 | 코스닥 | 코스피 | 의미 |
|------|--------|--------|------|
| 위험 | 200억 미만 | 300억 미만 | 7월 1일부터 즉시 30거래일 카운트 대상 |
| 경고 | 200억 이상 260억 미만 | 300억 이상 390억 미만 | 기준치 130% 미만 |
| 안전 | 그 외 | 그 외 | v1 후보군 수집 대상 아님 |

경고 구간을 `130% 미만`으로 둔 이유는 한 달 내 20~30% 하락 시 기준치 미달 가능성을 선제적으로 보기 위함이다.

### 5.4 이력 계산 방식

v1에서는 단순한 방식을 사용한다.

- 이력 데이터의 `market_cap`은 `close_price × listed_shares`로 계산한다.
- `listed_shares`는 해당 수집 시점 값 기준으로 사용한다.
- 과거 일자별 상장주식수 변동은 v1에서 반영하지 않는다.

주의:

- 유상증자, 감자, 전환사채 전환, 액면분할/병합 등 자본변동이 있었던 종목은 과거 시총이 일부 왜곡될 수 있다.
- 그러나 v1 목적은 정밀 회계 추적이 아니라 위험 후보군 선별이므로 이 단순 방식을 우선 채택한다.

---

## 6. 산출물

### 6.1 현재 산출물

| 단계 | 파일 |
|------|------|
| 티커 수집 | `market_tickers_YYYYMMDD.csv`, `.parquet` |
| 일별 스냅샷 | `market_snapshot_YYYYMMDD.csv`, `.parquet` |
| 후보군 필터링 | `warning_candidates_YYYYMMDD.csv` |
| 이력 수집 | `warning_history_YYYYMMDD.csv`, `.parquet` 예정 |

### 6.2 차트

차트는 후속 범위로 분리한다.

후속 예시:

- 종목별 시가총액 라인차트
- 시장별 위험/경고 종목 수 막대그래프

v1에서는 차트 파일 생성을 요구하지 않는다.

---

## 7. 실행 흐름

1. `collect_market_tickers.py` 실행
2. `market_cap_screening.py` 실행
3. `filter_warning_candidates.py` 실행
4. `warning_candidates`에 포함된 종목의 45거래일 이력 수집

---

## 8. 제약 및 가정

- 리서치/분석용 수동 실행을 기준으로 한다.
- 전체 시장의 45거래일 이력을 처음부터 전부 수집하지 않는다.
- 후보군 티커만 별도로 이력을 수집한다.
- 당일 장중 데이터는 사용하지 않는다.
- 거래정지, 관리종목, 상장폐지사유는 현재 수집 데이터만으로 판단하지 않는다.
- 차트는 후속 작업에서 별도 구현한다.

---

## 9. 다음 작업

| 순서 | 작업 | 상태 |
|------|------|------|
| 1 | 후보군 45거래일 이력 수집 스크립트 작성 | 대기 |
| 2 | 누적 저장 방식 정의 | 대기 |
| 3 | 이력 CSV/parquet 검증 | 대기 |
| 4 | 차트 및 간단한 리포트 생성 | 후속 |
