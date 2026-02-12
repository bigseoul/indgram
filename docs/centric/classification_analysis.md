# '구분' (Classification) 시트 상세 분석 보고서

'구분' 시트 분석 결과, 본 시스템은 **컬럼 기반의 동적 필터링 매커니즘**을 사용하여 멀티 허브 서비스를 운영하고 있습니다.

## 1. 서비스 매핑 테이블
각 코드(표시)는 메인 데이터 시트(`Tax_Hub`)의 특정 컬럼 및 배포된 Vercel 앱에 매핑됩니다.

| 코드 (Code) | 인덱스(row) | 연결 서비스 명칭 | Vercel 프로젝트 ID / 도메인 |
| :--- | :--- | :--- | :--- |
| **KC** | 5 | Tax AI & Forensics | `taxforensics` |
| **HUB** | 6 | TaxHub | `taxhubkr` |
| **SPK** | 7 | spk-sites (Static) | `spk-sites.html` |
| **CEN** | 8 | Centric | `centrictax` |
| **TA** | 9 | TaxAI | `kr-taxai` |
| **TR** | 10 | TaxRoad | `taxroad` |
| **TP** | 11 | TaxPro | `atfkr`, `taxprokr` |
| **TX** | 12 | Taxpert | `taxpertkr` |
| **DD** | 13 | -- | (미정/예비) |

## 2. 핵심 로직: 0-Based 컬럼 인덱싱
'구분' 시트의 `row` 값(예: KC=5)은 `Tax_Hub` 시트의 **0부터 시작하는 컬럼 번호**를 의미합니다.

- **작동 방식**: 
    1. 각 웹 포털(예: Centric)은 자신의 코드(`CEN`)에 해당하는 `row` 값인 `8`을 참조합니다.
    2. `Tax_Hub` 데이터의 8번 컬럼(I열) 값이 `1`인 행만 필터링하여 웹 화면에 노출합니다.
    3. 이를 통해 하나의 마스터 시트에서 값(0/1)만 수정하면 여러 사이트의 메뉴 구성을 동시에 제어할 수 있습니다.

## 3. 기술적 시사점
- **중앙 집중식 관리**: 개발 지식 없이도 시트 수정만으로 서비스 라우팅과 메뉴 구성을 관리할 수 있는 **Headless CMS** 구조입니다.
- **멀티 테넌시(Multi-tenancy)**: 동일한 데이터베이스를 공유하면서 필터링 값에 따라 서로 다른 서비스 경험(Centric, TaxAI 등)을 제공합니다.
