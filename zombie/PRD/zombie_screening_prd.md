# 한국 상장사 Zombie 기업 스크리닝 PRD

## Summary
- 목적: 한국 전체 상장사 중 최근 3개 연간 사업보고서 기준 이자보상배율(ICR)이 연속으로 1 미만인 기업을 식별하는 재사용 가능한 추출 파이프라인을 구축한다.
- 기준 연도: `2022~2024 사업보고서`
- 기준 변경 사유: 현재 날짜는 `2026-03-10`이며, 12월 결산 상장사의 `2025 사업보고서` 제출기한은 `2026-03-31`이므로 전체 상장사를 동일한 연간 기준으로 비교할 수 없다.
- 사용 입력: `zombie/data/market_tickers_with_corp_code.csv`
- 사용 라이브러리: `OpenDartReader`를 주 라이브러리로 사용하고, `corp_code` 보정에는 기존 DART corp list 로직을 재사용한다.

## Input And Universe
- 입력 파일: `zombie/data/market_tickers_with_corp_code.csv`
- 대상 시장: `KOSPI`, `KOSDAQ`
- 대상 종목: 입력 CSV의 종목 중 `corp_code`로 법인 식별이 가능한 행만 사용한다.
- 현재 입력 파일 현황:
  - 전체 행 수: `2,771`
  - `corp_code` 누락 행 수: `158`
  - 누락 행 표본은 `BYC우`, `CJ우`, `DL우`, `LG전자우` 등 대부분 우선주/종류주 계열이다.
- 최종 제외 기준:
  - `corp_code`가 이미 존재하는 행은 사용
  - `corp_code`가 비어 있으면 DART corp list의 `stock_code -> corp_code` exact match로 1회 보정
  - 보정 후에도 `corp_code`가 비어 있으면 제외
- 우선주/종류주는 별도 법인 분석 대상이 아니므로, 최종 제외 여부는 `stock_code` 패턴이 아니라 `corp_code` 존재 여부로 판단한다.

## Screening Definition
- Zombie 기업 정의: 최근 3개 연간 사업보고서 기준 이자보상배율(ICR)이 모두 `1 미만`인 기업
- 산식: `ICR = 영업이익 / 이자비용`
- strict exact 기준:
  - 분모는 `이자비용`, `InterestExpense` 계열만 인정
  - exact 기준 결과는 대표 산출물 `zombie_2026.csv`에 저장
- proxy fallback 기준:
  - raw 추출 단계에서는 `금융비용`, `금융원가`, `FinanceCosts` 계열도 별도로 함께 추출한다
  - 최종 proxy 결과에서는 exact ICR이 있으면 exact를 사용하고, exact가 없을 때만 proxy ICR로 fallback 한다
  - proxy fallback 기준 결과는 `zombie_2026_proxy.csv`에 저장

## DART Collection Rules
- 회사별 조회 단위: `corp_code x year`
- 대상 연도: `2022`, `2023`, `2024`
- 보고서 코드: `reprt_code='11011'` 고정
- 재무제표 우선순위:
  - `CFS` 우선 조회
  - 결과가 비어 있을 때만 `OFS`를 1회 추가 조회
- 사용 재무제표 범위:
  - `sj_div in {'IS', 'CIS'}`만 사용
  - `thstrm_amount`를 우선 사용
  - `thstrm_amount`가 `NaN` 또는 빈 문자열일 때만 `thstrm_add_amount`를 fallback으로 사용한다
  - `thstrm_amount = 0`은 실제 0원 값으로 간주하고 fallback 하지 않는다

## Account Matching Rules
- 영업이익 후보:
  - `영업이익`
  - `영업이익(손실)`
  - `OperatingIncomeLoss`
- exact 이자비용 후보:
  - `이자비용`
  - `이자비용(손실)`
  - `InterestExpense`
- proxy 비용 후보:
  - `금융비용`
  - `금융원가`
  - `FinanceCosts`
- 중복 후보가 여러 개면 다음 우선순위를 적용한다.
  - `sj_div` 적합 행 우선
  - `account_nm` exact match 우선
  - `ord`가 가장 작은 행 우선

## Numeric Handling And ICR Rules
- 금액 문자열은 쉼표, 공백, 괄호 음수 표기를 정규화해 수치형으로 변환한다.
- ICR 계산 규칙:
  - `interest_cost > 0`일 때만 계산
  - `interest_cost <= 0` 또는 결측이면 ICR은 `NaN`
  - `operating_profit < 0`이고 `interest_cost > 0`이면 음수 ICR을 그대로 사용한다
  - `operating_profit = 0`이고 `interest_cost > 0`이면 `ICR = 0`
- Zombie 판정 규칙:
  - 연도별 ICR이 모두 비결측이어야 한다
  - `2024`, `2023`, `2022` ICR이 모두 `< 1`이어야 한다
- 정렬 규칙:
  - `icr_avg` 오름차순
  - 동률이면 `market`, `stock_code`

## Deliverables
- 원시 추출 파일:
  - `zombie/data/icr_extract_2022_2024_long.csv`
- strict 대표 결과:
  - `zombie_2026.csv`
- proxy 보조 결과:
  - `zombie_2026_proxy.csv`
- 콘솔 출력:
  - strict 상위 20개 랭킹 테이블
  - proxy 상위 20개 랭킹 테이블
- 변환 책임:
  - checkpoint와 중간 수집 결과는 `parquet`로 저장한다
  - 최종 사용자 산출물 `csv` 생성과 랭킹 출력은 `screen_zombie.py`의 책임으로 둔다

## Output Schemas
- 최종 결과 CSV 컬럼:
  - `market`
  - `stock_code`
  - `corp_code`
  - `name`
  - `icr_2024`
  - `icr_2023`
  - `icr_2022`
  - `icr_avg`
- 원시 추출 CSV 컬럼:
  - `market`
  - `stock_code`
  - `corp_code`
  - `name`
  - `year`
  - `fs_div_used`
  - `report_code`
  - `source_status`
  - `operating_profit`
  - `interest_expense_exact`
  - `finance_cost_proxy`
  - `icr_exact`
  - `icr_proxy`

## Checkpoint And Resume Requirements
- 대량 API 호출을 고려해 checkpoint/resume을 필수 요구사항으로 둔다.
- 체크포인트 디렉터리:
  - `zombie/data/checkpoints/`
- 저장 파일:
  - `fetch_progress.parquet`
  - `fetch_errors.parquet`
  - `icr_extract_2022_2024_long.parquet`
- 진행 단위:
  - unique key는 `corp_code, year`
- 저장 정책:
  - 성공 시 즉시 progress와 raw parquet에 upsert 저장
  - 실패 시 error parquet에 에러 타입과 메시지를 기록
  - 재실행 시 이미 완료된 `corp_code-year`는 skip
  - 수집 완료 후 `screen_zombie.py`가 raw parquet를 기준으로 raw CSV와 최종 결과 CSV를 생성한다
- 호출 안정화 정책:
  - 기본 throttle을 적용해 분당 과도한 호출을 피한다
  - `ConnectionError`, `Timeout`, HTTP `429`, HTTP `5xx`는 지수 백오프로 재시도
  - 재시도 초과 시 에러 기록 후 다음 회사로 진행

## Suggested Module Structure
- `zombie/screen_zombie.py`
  - CLI 진입점
  - 실행 옵션 파싱
  - raw long 생성
  - exact/proxy wide 결과 생성
  - 상위 20개 랭킹 출력
- `zombie/dart_fetcher.py`
  - DART API 호출
  - corp_code 보정
  - checkpoint/resume
  - 재시도와 에러 기록
- `zombie/icr_calculator.py`
  - 계정 선택
  - 금액 정규화
  - ICR 계산
  - long to wide 변환

## Source Status Values
- `ok_cfs`
- `ok_ofs`
- `missing_statement`
- `missing_exact_interest`
- `missing_proxy_interest`
- `invalid_interest_sign`
- `excluded_no_corp_code`

## Test Plan
- 오프라인 단위 테스트
  - `corp_code` 보정 및 보정 실패 처리
  - `corp_code` 미존재 행 제외
  - `CFS -> OFS` fallback
  - `sj_div` 필터와 중복 계정 선택 우선순위
  - 괄호 음수, 쉼표 포함 금액 파싱
  - `interest_cost <= 0` 처리
  - 음수 영업이익, 0 영업이익, 결측 ICR 처리
  - long to wide pivot 시 연도 누락 회사 제외
  - `icr_avg` 정렬과 상위 20개 추출
  - CSV 컬럼 순서와 `utf-8-sig` 인코딩 검증
  - checkpoint resume 동작 검증
- 선택적 live 스모크 테스트
  - `RUN_DART_API_TESTS=1`일 때만 실행
  - 표본 1~2개 회사로 `finstate_all()` 응답 컬럼 확인
  - 실 API 응답 기반으로 exact/proxy 추출 검증

## Constraints And Assumptions
- `zombie_2026.csv`는 strict exact 대표 결과 파일이다.
- `zombie_2026_proxy.csv`는 coverage 확장용 보조 결과 파일이다.
- 현재 sandbox에서는 DART DNS 접근이 제한되어 있으므로 실제 추출 실행과 live 테스트에는 네트워크 권한이 필요하다.
- checkpoint 패턴은 과거 `zombie/market_snapshot.py`의 저장/재개 방식과 동일한 철학을 따른다.
