📌 PRD – DART 회사 개요 수집 배치 (업데이트 최신본)
변경사항 요약
1. 목적

보유 중인 corp_list 파일 기반으로 DART 회사 기본 개요 정보를 안정적으로 수집하며, 중단 후 재실행 시 정확하게 재개한다.

2. 기능 요구사항
기능 1) 회사 목록 입력

입력 파일: corp_list.csv 또는 corp_list.json

corp_code 추출 후 처리 대상 목록 생성

이미 Streaming CSV에 저장된 기업 코드 스킵

기능 2) 회사 개요 정보 수집

corp_code로 Corp(corp_code) 객체 생성

**Corp.load() 호출 (필수!)** - API 호출하여 상세 정보 로드

Corp.to_dict() 실행

반환 필드: (요구하신 필드 그대로 반영)

'corp_code', 'corp_name', 'corp_name_eng', 'stock_code',
'modify_date', 'stock_name', 'ceo_nm', 'corp_cls',
'jurir_no', 'bizr_no', 'adres', 'hm_url', 'ir_url',
'phn_no', 'fax_no', 'induty_code', 'est_dt', 'acc_mt'

재시도 로직: 실패 시 최대 3회 재시도

기능 3) Streaming CSV 실시간 저장

성공 시 즉시 Append

cor_code_extractor/fsdata/dart_corp_list_streaming.csv

기능 4) 진행 상태 저장 및 Resume

성공한 corp_code는 JSON에 기록

실패 발생 시 재시도 후에도 실패하면 즉시 중단

재실행 시 남은 대상만 다시 시도

기능 5) CSV 기반 중복 방지

CSV + JSON 모두 기반으로 정확한 Resume 보장

3. 데이터 흐름
corp_code_extractor/fsdata/corp_list.csv or corp_list.json
        ↓ (corp_code 읽기)
Corp(corp_code) 객체 찾기
        ↓
Corp.load() 호출 (재시도 포함)
        ↓
Corp.to_dict() 실행
        ↓ (성공 시)
dart_corp_list_streaming.csv Append
        ↓ (진행중/종료시)
fsdata/dart_corp_list.progress.json 갱신

4. 실패 정책

재시도 후에도 실패 시 즉시 전체 중단
이후 재실행 시 실패 지점부터 Resume

5. 테스트 시나리오(업데이트)
TC	시나리오	기대 결과
01	SAMPLE_SIZE 테스트	N건만 정상 수집
02	개요 호출 실패	재시도 → 실패 시 즉시 종료
03	중도 종료 → 재실행	실패 지점부터 이어서 수집
04	CSV/JSON 불일치 처리	JSON 우선으로 일관성 유지
05	Windows 환경 테스트	인코딩 문제 없이 동작
✅ 최종 결론 (검증 완료)
핵심 의사결정	상태	비고
corp_list는 API로 다시 가져오지 않음	✅ 확정	기존 CSV 사용
**corp.load() 필수 호출**	✅ 확정	상세 정보 수집에 필수 (테스트로 검증)
재시도 로직 포함	✅ 확정	최대 3회 재시도
실패 시 즉시 전체 중단	✅ 확정	재실행 시 이어서 진행
