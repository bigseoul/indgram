# CentricHub Master Service Blueprint (통합 설계서)

본 문서는 'Tax Hub' 시스템의 리버스 엔지니어링 결과와 B2B2C 제휴 전략, 그리고 상세 기술 설계를 하나로 통합한 **종합 서비스 마켓 설계용 마스터 블루프린트**입니다.

---

## 1. 서비스 비전 및 비즈니스 모델 (Vision & Strategy)

### 🧩 전문가 프라이빗 루프 (Expert Private Loop)
- **비전**: 인간 전문가의 지능을 AI가 안전하게 대행하여, 거대 지식(Knowledge)과 사용자(User)를 연결하는 '보안 지식 허브'.
- **핵심 가치**: 
    - **전문성**: 국세청 해설서, 판례 등 검증된 데이터 기반 답변.
    - **보안**: 고객 데이터가 AI 학습에 사용되지 않는 완벽한 격리 환경.

### 🧩 B2B2C 확장 전략 (Distribution Model)
- **파트너십**: 신문사(조세일보 등), 협회, 금융권 등 대규모 회원 기반을 가진 채널과 제휴.
- **상생 구조**:
    - **채널사**: 정회원 프리미엄 서비스 강화 (이탈 방지).
    - **Centric**: 고소득 자산가 리드(Lead) 확보 및 유료 컨설팅 전환 (영업 자동화).
- **운영**: 스프레드시트에 채널별 컬럼(예: `NEWS`) 하나만 추가하여 실시간으로 전용 허브 구축.

---

## 2. 계층별 기술 아키텍처 (Layered Architecture)

### 🏗️ A. 관리 계층 (Integrated Control Layer)
- **Infra**: Google Sheets API.
- **역할**: **'하드코딩 없는 운영'**.
- **기능**: 메뉴 노출 플래그(1/0) 관리, API 라우팅 정보, 서비스별 우선순위 제어.

### 🏗️ B. 지식 계층 (Knowledge Supply Chain)
- **Infra**: Google Drive / Docs / Vertex AI Search.
- **역할**: **'살아있는 지식 베이스'**.
- **기능**: 전문가가 문서를 수정하면 즉시 벡터화(Embedding)되어 AI 답변에 반영되는 실시간 RAG 엔진.

### 🏗️ C. 지능 계층 (Intelligence & Protocol Layer)
- **Infra**: Gemini Enterprise (Private Endpoint).
- **역할**: **'신뢰할 수 있는 답변 생성'**.
- **프로토콜**: 
    - `0-BETA`: 답변 전 실시간 데이터 강제 조회 및 교차 검증.
    - `0-ALPHA`: 오류 지적 시 즉각적인 오염 캐시 파기 및 재추론.

### 🏗️ D. 서비스 계층 (Delivery & Edge Layer)
- **Infra**: Vercel (Next.js) Multi-tenant.
- **역할**: **'유연한 프론트엔드 배포'**.
- **기능**: 하나의 소스로 테넌트별 브랜드(CI/BI)만 바꿔서 무한 배포 가능한 화이트 라벨링 시스템.

---

## 3. 개인정보 및 보안 전략 (Security & Privacy)

- **무신원 인증 (Identity-less Auth)**: 파트너사(신문사)로부터 개인 식별 정보를 받지 않고, 암호화된 권한 토큰(JWT)만으로 서비스 제공.
- **데이터 사일로**: 파트너사 DB와 AI 상담 로그의 완전한 물리적 격리.
- **데이터 비학습**: Gemini Enterprise의 Zero-training 정책을 통해 기업 비밀 및 개인 상담 내용 보호.

---

## 4. 데이터 모델 설계 (Data Model)

- **ServiceItem**: `id`, `title`, `description`, `url`, `icon`, `order`, `flags(HUB_CODE)`, `status`.
- **CatalogSnapshot**: 시트 조회 실패를 대비한 최근 정상 데이터의 스냅샷 저장 (Fail-safe).
- **Auditing**: 클릭 수, CTR, API 성공률 등 시스템 건전성 지표 상시 수집.

---

## 5. 단계별 로드맵 (Execution Roadmap)

1.  **Phase 1 (MVP)**: 구글 시트 기반의 링크 허브(Catalog) 구축 및 채널별 필터링 기능 구현.
2.  **Phase 2 (Scalability)**: 클릭 이벤트 수집, 스냅샷 폴백, 파트너사 전용 UI 배포 자동화.
3.  **Phase 3 (Intelligence)**: Vertex AI 기반 RAG 연동 및 전문가 전용 프로토콜(0-A/B) 탑재 답변 엔진 고도화.

---

## 결론
이 시스템은 단순한 챗봇이 아니라, **"구축은 쉽고(One Source), 배포는 무한하며(Multi Hub), 보안은 완벽한(Private Loop)"** 최상위 전문가 비즈니스 플랫폼입니다.
