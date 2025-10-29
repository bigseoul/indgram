# OpenDartReader - Reference Manual

![](https://i.imgur.com/FMsL0id.png)`OpenDartReader`는 금융감독원 전자공시 시스템의 "Open DART"서비스 API를 손쉽게 사용할 수 있도록 돕는 오픈소스 라이브러리 입니다.

* **2020-2022 [FinanceData.KR](https://nbviewer.org/github/FinanceData/OpenDartReader/blob/master/docs/OpenDartReader_reference_manual.ipynb) | [facebook.com/financedata](https://nbviewer.org/github/FinanceData/OpenDartReader/blob/master/docs/OpenDartReader_reference_manual.ipynb)** *

## 1. 공시정보 검색

다음과 같은 함수가 제공됩니다.

### list() - 공시검색

지정한 회사의 보고서를 검색합니다. 기간과 보고서의 종류를 지정할 수 있습니다.

```
dart.list(corp, start=None, end=None, kind='', kind_detail='', final=True)
```

인자

* `corp` (문자열): 검색대상 회사의 종목코드를 지정합니다. 고유번호, 회사이름도 가능합니다.
* `start` (datetime 혹은 문자열, 기본값=None): 검색 시작일.
* `end` (datetime 혹은 문자열, 기본값=None): 검색 종료일. 지정하지 않으면 오늘이 됩니다.
* `kind` (문자열, 기본값=''): 공시유형 ('A'=정기공시, 'B'=주요사항보고, 'C'=발행공시, 'D'=지분공시, 'E'=기타공시, 'F'=외부감사관련, 'G'=펀드공시, 'H'=자산유동화, 'I'=거래소공시, 'J'=공정위공시)
* `kind_detail` (문자열, 기본값=''): 공시 상세 유형. ('5'=정기공시, '3'=주요사항보고, '11'=발행공시, '4'=지분공시, '9'=기타공시, '5'=외부감사관련, '3'=펀드공시, '6'=자산유동화, '6'=거래소공시, '5'=공정위공시)
* `final` (bool, 기본값=True): 최종보고서 여부, False면 중간 변경 보고서를 포함합니다.

반환값(DataFrame): 조회 결과를 데이터프레임(DataFrame)으로 반환합니다. 각 컬럼은 다음과 같습니다.

* corp_code: 고유번호
* corp_name: 회사이름
* stock_code: 주식의 종목코드 (상장회사인 경우)
* corp_cls: 법인구분 Y(유가), K(코스닥), N(코넥스), E(기타)
* report_nm: 보고서명
* rcept_no: 접수번호
* flr_nm: 공시 제출인명
* rcept_dt: 접수일자
* rm: 비고 (비고 상세 참조)

`start`와 `end`에 지정하는 날짜의 형식 '2020-07-01', '2020-7-1', '20200701', '1 july 2020', 'JULY 1 2020' 모두 가능합니다. datetime객체도 가능합니다.

* start 와 end를 함께 지정하면 start~end 기간을 지정합니다.
* start만 지정하면 start 부터 현재까지,
* end만 지정하면 end 하루를 지정하게 됩니다.

비고 상세: 조합된 문자로 각각은 아래와 같은 의미가 있습니다.

* 유 : 유가증권 종목
* 코 : 코스닥 종목
* 채 : 채권 종목 채권상장법인 공시사항임
* 넥 : 코넥스 종목
* 공 : 공정거래 공시
* 연 : 연결 공시
* 정 : 이후 정정 보고 있음 (최종보고서가 아님)
* 철 : 철회된 보고서

### company() - 기업개황

기업의 개황정보를 읽어옵니다

```
dart.company(corp)
```

인자

* `corp` (문자열): 검색대상 회사의 종목코드를 지정합니다. 고유번호, 회사이름도 가능합니다.

반환값 (dict): 기업 개황 정보(정식명칭, 영문명칭, 종목명 또는 약식명칭, 상장회사인 경우 주식의 종목코드, 대표자명, 법인구분, 법인등록번호, 사업자등록번호, 주소, 홈페이지, IR홈페이지, 전화번호, 팩스번호, 업종코드, 설립일, 결산월) 조회 결과를 딕셔너리(dict)로 반환 합니다.

### company_by_name() - 기업개황 이름 검색

기업을 검색하여 이름이 포함된 모든 기업들의 기업개황 정보를 반환합니다.

```
dart.company_by_name(name)
```

인자

* `name` (문자열): 검색대상 회사의 명칭을 지정합니다. 이 문자열이 포함된 모든 회사에 대한 정보가 반환됩니다.

반환값(dict list): 지정한 이름을 포함하는 기업들의 기업 개황 (정식명칭, 영문명칭, 종목명 또는 약식명칭, 상장회사인 경우 주식의 종목코드, 대표자명, 법인구분, 법인등록번호, 사업자등록번호, 주소, 홈페이지, IR홈페이지, 전화번호, 팩스번호, 업종코드, 설립일, 결산월) 조회 결과를 딕셔너리(dict) 리스트로 반환 합니다.

### document() - 공시서류 원문

공시보고서 접수번호(rcp_no)에 해당하는 공시보고서 원본 문서를 XML문서로 반환합니다

```
dart.document(rcp_no)
```

인자

* `rcp_no` (문자열): 접수번호 (8자리)

반환값(str): 공시서류 원문을 XML문서로 반환합니다.

### find_corp_code() - 고유번호 얻기

종목코드 혹은 기업명으로 고유번호를 가져옵니다. 전자공시에서 개별 기업은 고유번호로 식별 됩니다. 특히, 상장종목이 아닌 경우는 고유번호를 사용해야 합니다.

```
dart.find_corp_code(corp)
```

인자

* `corp` (문자열): 검색대상 회사의 종목코드를 지정합니다. 고유번호, 회사이름도 가능합니다.

반환값(str): 고유번호를 반환합니다.

### corp_codes - 고유번호(속성)

고유번호, 종목명, 종목코드 등의 정보를 포함하고 있는 속성값 입니다.

```
dart.corp_codes
```

`corp_codes`(DataFrame)은 속성값으로 언제들 참고할 수 있습니다. 7만 6천여개 기업에 대한 고유번호, 종목명, 종목코드 등의 정보를 포함하고 있습니다. 컬럼의 구성은 다음과 같습니다.

* corp_code: 고유번호
* corp_name: 종목명
* stock_code: 주식의 종목코드 (상장회사인 경우)
* modify_date: 수정일

## 2. 사업보고서 주요정보

### report() - 사업보고서 주요정보

사업보고서의 주요 내용을 조회 합니다.

```
dart.report(corp, key_word, bsns_year, reprt_code='11011')
```

인자

* `corp` (문자열): 검색대상 회사의 종목코드를 지정합니다. 고유번호, 회사이름도 가능합니다.
* `key_word` (문자열): 조회 내용 지정, 아래 "key_word 항목"을 참고하십시오 ('증자','배당','자기주식','최대주주','최대주주변동','소액주주','임원','직원','임원개인보수','임원전체보수','개인별보수','타법인출자')
* `bsns_year` (문자열 혹은 정수값): 사업연도
* `reprt_code` (문자열): 보고서 코드 ('11013'=1분기보고서, '11012'=반기보고서, '11014'=3분기보고서, '11011'=사업보고서)

key_word 항목

| 번호 | 파라미터 문자열 | 설명                                  |
| ---- | --------------- | ------------------------------------- |
| 1.   | '증자'          | 증자(감자) 현황                       |
| 2.   | '배당'          | 배당에 관한 사항                      |
| 3.   | '자기주식'      | 자기주식 취득 및 처분 현황            |
| 4.   | '최대주주'      | 최대주주 현황                         |
| 5.   | '최대주주변동'  | 최대주주 변동 현황                    |
| 6.   | '소액주주'      | 소액주주현황                          |
| 7.   | '임원'          | 임원현황                              |
| 8.   | '직원'          | 직원현황                              |
| 9.   | '임원개인보수'  | 이사ㆍ감사의 개인별 보수 현황         |
| 10.  | '임원전체보수'  | 이사ㆍ감사 전체의 보수현황            |
| 11.  | '개인별보수'    | 개인별 보수지급 금액(5억이상 상위5인) |
| 12.  | '타법인출자'    | 타법인 출자현황                       |

반환값 (DataFrame): 조회 결과를 데이터프레임(DataFrame)으로 반환합니다. 데이터프레임의 각 컬럼은 다음과 같습니다.

* `rcept_no`: 접수번호
* `corp_cls`: 법인구분 Y(유가), K(코스닥), N(코넥스), E(기타)
* `corp_code`: 고유번호
* `corp_name`: 법인명

key_word 항목 지정에 따라 결과 데이터의 컬럼이 달라집니다. `'배당'` - 배당에 관한 사항

* se: 구분. 유상증자(주주배정), 전환권행사 등
* stock_knd: 주식 종류
* thstrm: 당기
* frmtrm: 전기
* lwfr: 전전기

## 3. 상장기업 재무정보

### finstate() - 재무 정보

상장기업의 재무 데이터를 가져옵니다.

```
dart.finstate(corp, bsns_year, reprt_code='11011')
```

인자

* `corp` (문자열): 검색대상 회사의 종목코드를 지정합니다. 고유번호, 회사이름도 가능합니다.
* `bsns_year` (문자열 혹은 정수값): 사업연도
* `reprt_code` (문자열): 보고서 코드 ('11013'=1분기보고서, '11012'=반기보고서, '11014'=3분기보고서, '11011'=사업보고서)

반환값 (DataFrame): 조회 결과를 데이터프레임(DataFrame)으로 반환합니다. 데이터프레임의 각 컬럼은 다음과 같습니다.

* rcept_no: 접수번호
* corp_code: 사업 연도
* stock_code: 종목 코드
* reprt_code: 보고서 코드
* account_nm: 계정명 (예: 자본총계)
* fs_div: 개별/연결구분 ('CFS'=연결재무제표, 'OFS'=재무제표)
* fs_nm: 개별/연결명 ('연결재무제표' 또는 '재무제표')
* sj_div: 재무제표구분 ('BS'=재무상태표, 'IS'=손익계산서)
* sj_nm: 재무제표명 ( '재무상태표' 또는 '손익계산서')
* thstrm_nm: 당기명
* thstrm_dt: 당기일자
* thstrm_amount: 당기금액
* thstrm_add_amount: 당기누적금액
* frmtrm_nm: 전기명
* frmtrm_dt: 전기일자
* frmtrm_amount: 전기금액
* frmtrm_add_amount: 전기누적금액
* bfefrmtrm_nm: 전전기명
* bfefrmtrm_dt: 전전일자
* bfefrmtrm_amount: 전전기금액
* ord: 계정과목 정렬순서

`corp`에 여러 종목을 한번에 지정할 수 있습니다.

```
dart.finstate('00126380,00164779,00164742', 2018)
dart.finstate('005930, 000660, 005380', 2018)
dart.finstate('삼성전자, SK하이닉스, 현대자동차', 2018)
```

### finstate_all() - 단일회사 전체 재무제표

재무 데이터 전체를 가져옵니다.

```
dart.finstate_all(corp, bsns_year, reprt_code='11011', fs_div='CFS')
```

인자

* `corp` (문자열): 검색대상 회사의 종목코드를 지정합니다. 고유번호, 회사이름도 가능합니다.
* `bsns_year` (문자열 혹은 정수값): 사업연도
* `reprt_code` (문자열): 보고서 코드 ('11013'=1분기보고서, '11012' =반기보고서, '11014'=3분기보고서, '11011'=사업보고서)
* `fs_div` (문자열): 재무제표의 종류: 'CFS'=연결제무제표, 'OFS'=별도(개별)제무제표

반환값 (DataFrame): finstate()와 같습니다.

## 4. 지분공시

### major_shareholders() - 대량보유 상황보고

주식등의 대량보유상황보고서 내에 대량보유 상황보고 정보를 조회합니다.

```
dart.major_shareholders(corp)
```

인자

* `corp` (문자열): 검색대상 회사의 종목코드를 지정합니다. 고유번호, 회사이름도 가능합니다.

반환값 (DataFrame): 조회 결과를 데이터프레임(DataFrame)으로 반환합니다. 데이터프레임의 각 컬럼은 다음과 같습니다.

* rcept_no: 접수번호
* rcept_dt: 접수일자
* corp_code: 종목코드
* corp_name: 회사명
* report_tp: 보고구분
* repror: 대표보고자
* stkqy: 보유주식등의 수
* stkqy_irds: 보유주식등의 증감
* stkrt: 보유비율
* stkrt_irds: 보유비율 증감
* ctr_stkqy: 주요체결 주식등의 수
* ctr_stkrt: 주요체결 보유비율
* report_resn: 보고사유

### major_shareholders_exec() - 임원ㆍ주요주주 소유보고

임원ㆍ주요주주특정증권등 소유상황보고서 내에 임원ㆍ주요주주 소유보고 정보를 조회합니다.

```
dart.major_shareholders_exec(corp)
```

인자

* `corp` (문자열): 검색대상 회사의 종목코드를 지정합니다. 고유번호, 회사이름도 가능합니다.

반환값 (DataFrame): 조회 결과를 데이터프레임(DataFrame)으로 반환합니다. 데이터프레임의 각 컬럼은 다음과 같습니다.

* rcept_no: 접수번호
* rcept_dt: 접수일자
* corp_code: 종목코드
* corp_name: 회사명
* repror: 대표보고자
* isu_exctv_rgist_at: 발행 회사 관계 임원(등기여부)
* isu_exctv_ofcps: 발행 회사 관계 임원 직위
* isu_main_shrholdr: 발행 회사 관계 주요 주주
* sp_stock_lmp_cnt: 특정 증권 등 소유 수
* sp_stock_lmp_irds_cnt: 특정 증권 등 소유 증감 수
* sp_stock_lmp_rate: 특정 증권 등 소유 비율
* sp_stock_lmp_irds_rate: 특정 증권 등 소유 증감 비율

## 5. 주요사항보고서

dart.event(corp, event, start=None, end=None)

사업보고서내 주요사항보고 항목을 가져옵니다.
조회가능한 주요사항 항목은 다음과 같습니다.

> '부도발생', '영업정지', '회생절차', '해산사유', '유상증자', '무상증자', '유무상증자', '감자', '관리절차개시', '소송', '해외상장결정', '해외상장폐지결정', '해외상장', '해외상장폐지', '전환사채발행', '신주인수권부사채발행', '교환사채발행', '관리절차중단', '조건부자본증권발행', '자산양수도', '타법인증권양도', '유형자산양도', '유형자산양수', '타법인증권양수', '영업양도', '영업양수', '자기주식취득신탁계약해지', '자기주식취득신탁계약체결', '자기주식처분', '자기주식취득', '주식교환', '회사분할합병', '회사분할', '회사합병', '사채권양수', '사채권양도결정'

## 6. 증권신고서

dart.regstate(corp, key_word, start=None, end=None)

조회가능한 증권신고서 항목: '주식의포괄적교환이전', '합병', '증권예탁증권', '채무증권', '지분증권', '분할'

## 7. 확장 기능

### list_date_ex() - 특정 날짜의 보고서 목록

list_date()와 유사한 기능을 수행하며, 공시가 게시된 시간 정보를 포함합니다.

```
dart.list_date_ex(date)
```

인자

* `date` (문자열 혹은 datetime) 날짜 지정 (지정하지 않으면 오늘)

반환값 (DataFrame): 조회 결과를 데이터프레임(DataFrame)으로 반환합니다. 데이터프레임의 각 컬럼은 다음과 같습니다.

* corp_code: 고유번호
* corp_name: 회사이름
* corp_cls: 법인구분 유(유가), 코(코스닥), 넥(코넥스), 기(기타)
* report_nm: 보고서명
* rcept_no: 접수번호
* flr_nm: 공시 제출인명
* rcept_dt: 접수일자(시간 정보를 포함)
* rm: 비고

### sub_docs() - 하위 문서 목록

특정 공시보고서의 하위 문서에 대한 정보를 리스트로 반환합니다

```
dart.sub_docs(rcp_no, match)
```

인자

* `rcp_no` (문자열): 접수번호
* `match` (문장열): `match`와 가장 잘 매칭되는 순서로 소트하여 반환합니다.

반환값 (DataFrame): 컬럼은 (`title`, `url`) 입니다.

### attach_docs() - 첨부 문서 리스트

특정 공시보고서의 첨부 문서에 대한 정보를 리스트로 반환합니다.

```
dart.attach_docs(rcp_no, match)
```

인자

* `rcp_no` (문자열): 접수번호
* `match` (문장열): `match`와 가장 잘 매칭되는 순서로 소트하여 반환합니다.

반환값 (DataFrame): 컬럼은 (`title`, `url`) 입니다.

### attach_files() - 첨부 파일 리스트

특정 공시보고서의 첨부 파일에 대한 정보를 dict로 반환합니다.

```
dart.attach_files(rcp_no)
```

인자

* `rcp_no` (문자열): 접수번호

반환값 (dict): {`file_name`: `url`} 입니다.

### download() - URL을 파일로 저장

지정한 링크(url)을 파일(fn)로 저장합니다. 첨부 파일의 URL을 가져와 저장하기 위해 `dart.download(url, fn)`을 사용할 수 있습니다.

```
retrieve(url, fn)
```

인자

* `url` (문자열): URL(링크)
* `fn` (문장열): 저장할 파일경로

사용예:

```
# 첨부 파일 모두 다운로드 하기

rcp_no = '20220308000798' # 삼성전자 2021년 사업보고서

files = dart.attach_files(rcp_no)
for title, url in files.items():
    print(title)
    print(url)
    dart.download(url, title)
```

* **2020-2022 [FinanceData.KR](https://nbviewer.org/github/FinanceData/OpenDartReader/blob/master/docs/OpenDartReader_reference_manual.ipynb) | [facebook.com/financedata](https://nbviewer.org/github/FinanceData/OpenDartReader/blob/master/docs/OpenDartReader_reference_manual.ipynb)** *
