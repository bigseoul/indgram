corp_list.py
기능: dart-fss 라이브러리를 사용하여 DART(전자공시시스템)에서 제공하는 전체 회사 목록을 수집하고 저장합니다.
저장 위치: fsdata/2025/corp_list.json (및 .csv)

2_corp_list_detail.py
기능: corp_list.json을 기반으로 DART에서 제공하는 회사 개요를 수집하고 저장합니다.
제약: MAX_WORKERS 1로 설정, REQUEST_DELAY 0.2로 설정. opendart에서 ip 컷 할 수 있음. 

3_add_induty_name_complete_levels.py
기능: dart_corp_list.csv 파일에 KSIC 산업 분류 코드를 기반으로 `induty_name` 컬럼을 추가하는 Python 스크립트
