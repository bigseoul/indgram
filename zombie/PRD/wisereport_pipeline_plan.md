# WiseReport 기반 Zombie 스크리닝 구현 기준서

## 목적
- 입력 파일 `zombie/data/market_tickers_with_corp_code.csv`를 사용해 종목별 `stock_code` 기준으로 WiseReport 투자지표를 수집한다.
- 수집 대상 지표는 `이자보상배율`이다.
- 기존 DART 기반 파이프라인과 분리된 별도 WiseReport 파이프라인으로 구현한다.

## 설계 원칙
- 기존 DART 경로와 WiseReport 경로를 한 CLI에 섞지 않는다.
- WiseReport는 `기계산 지표 수집`이고, DART는 `line-item 기반 직접 계산`이므로 모듈을 분리한다.
- 결과 스키마는 기존과 최대한 맞춘다.
- checkpoint/resume을 기본 전제로 둔다.

## 모듈 구조

### 1. `zombie/common_io.py`
- 역할: DART/ WiseReport 공용 IO 유틸리티
- 포함 대상
  - `DEFAULT_INPUT_PATH`
  - `DEFAULT_MARKETS`
  - `INPUT_COLUMNS`
  - `normalize_stock_code()`
  - `is_blank()`
  - `utc_now()`
  - `load_input_universe()`
  - `ensure_parent()`
  - `load_parquet_frame()`
  - `save_parquet_frame()`
  - `upsert_rows()`
- 비포함 대상
  - `get_default_api_key()`
  - DART API 호출 관련 함수

### 2. `zombie/dart_fetcher.py`
- 역할: 기존 DART 파이프라인 유지
- 변경 원칙
  - `common_io`에서 범용 함수와 상수를 import
  - 기존 import 경로 호환을 위해 re-export 유지
- 목표
  - 기존 `screen_zombie.py` 및 기존 테스트가 깨지지 않게 유지

### 3. `zombie/wisereport_fetcher.py`
- 역할: WiseReport HTTP 수집 + raw payload checkpoint
- fetcher 책임 범위
  - 입력 universe 로드
  - `stock_code` 기준 세션 생성
  - `c1040001.aspx` 방문으로 세션 쿠키 확보
  - 동일 세션으로 `cF4002.aspx` 호출
  - raw JSON 문자열 또는 raw JSON object 저장
  - progress / error checkpoint 저장
- fetcher 비책임 범위
  - `ACC_NM == '이자보상배율'` 행 선택
  - `YYMM`, `DATA` 의미 해석
  - 연도별 wide 변환
  - zombie 판정

### 4. `zombie/wisereport_parser.py`
- 역할: WiseReport raw payload 해석
- parser 책임 범위
  - raw JSON 파싱
  - `ACC_NM == '이자보상배율'` 행 선택
  - `YYMM`와 `DATA1~DATA6`를 연도별 값으로 변환
  - 최종 wide 결과 생성
  - `icr_2024`, `icr_2023`, `icr_2022`, `icr_avg` 계산
  - 최근 3개년 연속 `< 1` 판정

### 5. `zombie/screen_zombie_wisereport.py`
- 역할: WiseReport 파이프라인 전용 CLI
- 책임
  - fetcher 실행
  - parser 실행
  - raw CSV / final CSV 생성
  - 상위 20개 랭킹 출력

## WiseReport 수집 경로

### 진입 페이지
- `https://finance.naver.com/item/coinfo.naver?code={stock_code}`
- 실제 종목분석 iframe:
  - `https://navercomp.wisereport.co.kr/v2/company/c1010001.aspx?cmp_cd={stock_code}`

### 투자지표 페이지
- `https://navercomp.wisereport.co.kr/v2/company/c1040001.aspx?cmp_cd={stock_code}&cn=`

### 실제 지표 값 엔드포인트
- `https://navercomp.wisereport.co.kr/v2/company/cF4002.aspx`

### 확인된 파라미터
- `cmp_cd={stock_code}`
- `frq=0`
- `rpt=3`
  - `안정성` 탭
- `finGubun=IFRSS`
- `frqTyp=0`
  - 연간
- `cn=`
- `encparam=...`
  - 페이지 스크립트에서 제공되는 값 사용

## 확인된 WiseReport 탭 매핑
- `rpt=1`: 수익성
- `rpt=2`: 성장성
- `rpt=3`: 안정성
- `rpt=4`: 활동성

## 실제 검증 결과
- WiseReport `c1040001`의 formula 표에는 `안정성 > 이자보상배율 = 영업이익/이자비용`이 명시되어 있음
- `cF4002.aspx` JSON에서 `ACC_NM == '이자보상배율'` 행이 실제로 내려오는 것을 표본 종목 `032940`에서 확인함
- 예시 응답 필드
  - `YYMM`
  - `DATA`
  - `FIN`
  - `FRQ`
- 예시 row 필드
  - `ACC_NM`
  - `DATA1 ~ DATA6`
  - `DATAQ1 ~ DATAQ6`
  - `YYOY`, `QOQ`, `YOY`

## checkpoint 경로
- 디렉터리: `zombie/data/checkpoints`
- WiseReport 전용 상수는 `wisereport_fetcher.py`에 둔다.

```python
DEFAULT_WR_CHECKPOINT_DIR = Path("zombie/data/checkpoints")
DEFAULT_WR_PROGRESS_PATH = DEFAULT_WR_CHECKPOINT_DIR / "wisereport_fetch_progress.parquet"
DEFAULT_WR_ERROR_PATH = DEFAULT_WR_CHECKPOINT_DIR / "wisereport_fetch_errors.parquet"
DEFAULT_WR_RAW_PARQUET_PATH = DEFAULT_WR_CHECKPOINT_DIR / "wisereport_raw_payload.parquet"
```

## raw payload 스키마 제안
- `market`
- `stock_code`
- `corp_code`
- `name`
- `rpt`
- `fin_gubun`
- `frq_typ`
- `payload_json`
- `source_status`
- `fetched_at`

## 최종 결과 스키마
- 기존 DART 결과와 호환되게 유지

```text
market, stock_code, corp_code, name, icr_2024, icr_2023, icr_2022, icr_avg
```

## 기본 출력 파일명
- 최종 결과: `zombie/data/icr_2022_2024_ifrss.csv`
- raw long: `zombie/data/icr_2022_2024_ifrss_long.csv`

## 구현 순서
1. `zombie/common_io.py`
2. `zombie/dart_fetcher.py`에서 `common_io` re-export 적용
3. `zombie/wisereport_fetcher.py`
4. `zombie/wisereport_parser.py`
5. `zombie/screen_zombie_wisereport.py`
6. 테스트 추가

## 테스트 범위

### 공용
- `common_io` 추출 후 기존 `dart_fetcher` 테스트가 그대로 통과하는지 확인

### WiseReport fetcher
- 세션 페이지 방문 후 raw payload 저장
- progress / error parquet 저장
- 동일 `stock_code` 재실행 시 skip/resume

### WiseReport parser
- fixture JSON에서 `이자보상배율` row 선택
- `YYMM`와 `DATA1~DATA6` 매핑 검증
- wide 변환 검증
- `icr_avg` 계산 및 `< 1` 필터 검증

## 주의사항
- `fetcher`는 raw JSON까지만 책임진다.
- `parser`가 도메인 의미를 해석한다.
- `get_default_api_key()`는 DART 전용이므로 `dart_fetcher.py`에 남긴다.
- 기존 DART 파이프라인 파일명과 checkpoint 파일명을 재사용하지 않는다.
