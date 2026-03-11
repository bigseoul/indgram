# dart-fss 방식 검토 메모

## Summary
- 목적: `OpenDartReader`의 `account_nm` 중심 접근 대신 `dart-fss`의 XBRL `concept_id` 기반 접근이 exact 이자비용 탐지에 더 유리한지 확인한다.
- 결론: `dart-fss`는 구조적으로 더 낫다. 단순 단어 매칭이 아니라 XBRL `concept_id`를 직접 조회할 수 있다.
- 다만 표본 결과상 `ifrs-full_InterestExpense`는 거의 보이지 않았고, 대부분 `ifrs-full_FinanceCosts`만 존재했다.

## Checked Path
- 사용 경로:
  - `dart.fs.extract(...)`
  - `FinancialStatement.show('is', show_class=False, show_concept=True)`
  - `report.xbrl.get_income_statement()`
  - `Table.get_value_by_concept_id(concept_id)`
- 핵심 장점:
  - 손익계산서에서 `label_ko`, `label_en`, `concept_id`를 함께 볼 수 있다.
  - 문자열 계정명 대신 `concept_id`로 값 추출이 가능하다.
  - 연결/별도 맥락을 context label로 구분할 수 있다.

## Verified Concepts
- 영업이익:
  - `dart_OperatingIncomeLoss`
  - 일부 회사는 `ifrs-full_OperatingIncomeLoss` 가능성도 열어둔다.
- 금융비용:
  - `ifrs-full_FinanceCosts`
- exact 이자비용:
  - `ifrs-full_InterestExpense`

## Live Findings
- 표본:
  - `zombie_2026_proxy.csv` 상위 20개 기업
  - 연도 `2022~2024`
  - 총 `60`건 probe
- 결과 파일:
  - `zombie/data/dart_fss_interest_probe_top20.csv`
- 결과 요약:
  - `has_interest_expense = 0 / 60`
  - `has_finance_costs = 54 / 60`
  - `fs_div = CFS 40, OFS 14, 없음 6`
  - `error_rows = 6`
- 오류 예시:
  - `NoDataReceived: 조회된 데이타가 없습니다.`
  - `xbrl is None` 성격의 케이스

## Interpretation
- `dart-fss`는 `OpenDartReader`보다 좋은 탐색 기반을 제공한다.
- 이유:
  - `account_nm` 문자열 의존을 줄이고 `concept_id` 직접 조회가 가능하다.
  - exact/proxy를 XBRL 표준 개념 기준으로 나눌 수 있다.
- 하지만 exact coverage 문제는 여전히 남는다.
- 현재 표본에서는:
  - `InterestExpense` 개념이 전혀 잡히지 않았다.
  - 대신 `FinanceCosts`는 대부분 존재했다.
- 따라서 `dart-fss`로 바꿔도 exact 결과가 자동으로 크게 늘어난다고 가정하면 안 된다.

## Concept Difference
- `ifrs-full_InterestExpense`
  - 이자비용만 의미하는 더 좁은 개념
  - 원래 ICR 정의의 분모와 가장 가깝다.
- `ifrs-full_FinanceCosts`
  - 금융비용 전체를 의미하는 더 넓은 개념
  - 이자비용 외 금융 관련 손익이 함께 포함될 수 있다.
- 실무적 해석:
  - `InterestExpense`가 있으면 exact
  - `FinanceCosts`만 있으면 proxy

## Practical Implication
- 다음 구현 대안은 두 가지다.
- 대안 1:
  - 전체 파이프라인을 `dart-fss` XBRL 기반으로 전환
  - exact는 `InterestExpense concept`
  - proxy는 `FinanceCosts concept`
- 대안 2:
  - `dart-fss` XBRL 본문 외에 주석/다른 table까지 추가 탐색
  - `InterestExpense`가 다른 테이블에 존재하는지 확인

## Current Recommendation
- 당장 구조를 바꾼다면 `dart-fss`를 쓰는 것이 맞다.
- 다만 exact coverage 확보가 목적이면, 단순 전환보다 `InterestExpense`가 숨어 있는 추가 XBRL table/주석 탐색 여부를 먼저 논의해야 한다.
