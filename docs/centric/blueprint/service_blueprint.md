# New Service Logic & Architecture Blueprint

본 문서는 'Tax Hub' 시스템의 리버스 엔지니어링 결과를 바탕으로, 10년 차 풀스택 개발자 및 서비스 기획자 관점에서 설계한 **[서비스명/유형]**의 핵심 로직 아키텍처입니다.

---

## 1. 서비스 설계 철학 (Service Philosophy)

- **The Expert Proxy**: 인간 전문가의 지능을 AI가 안전하고 정확하게 대행하는 '전문가 프록시' 모델.
- **Private Loop Construction**: 데이터의 입력부터 처리, 출력까지 모든 단계가 고객사의 전용 보안 구역(GCP Tenant) 내에서만 순환하도록 설계.
- **Logic-Data Separation**: 실행 로직(Code)과 지식 데이터(CMS/Docs)를 완벽히 분리하여, 비개발자(세무사, 변호사 등)가 실시간으로 AI의 지식을 업데이트할 수 있는 구조.

---

## 2. 계층별 핵심 아키텍처 (Stacked Architecture)

### 🧩 A. 관리 계층 (Integrated Control Layer)
- **CMS**: **Google Sheets API** 기반.
- **로직**:
    - `0/1 Toggle Filtering`: 각 서비스 허브(Hub)별로 노출할 도구(Gems)를 실시간 제어.
    - `Metadata Routing`: 사용자의 질문 성격에 따라 어떤 지식 베이스(Docs)와 페르소나를 연결할지 결정하는 라우팅 테이블.

### 🧩 B. 지식 계층 (Knowledge Supply Chain)
- **Storage**: **Google Drive / Docs API**.
- **로직**:
    - **Dynamic RAG (Retrieval-Augmented Generation)**: Vertex AI Search를 사용하여 수만 페이지의 전문 자료를 벡터화(Vectorization).
    - **Living Knowledge**: 전문가가 구글 문서를 수정하면 별도의 배포 과정 없이 AI의 지식이 즉시 동기화됨.

### 🧩 C. 지능 계층 (Intelligence & Protocol Layer)
- **Engine**: **Gemini Enterprise (Private Endpoint)**.
- **핵심 프로토콜**:
    - **Protocol 0-ALPHA (Cache Purge)**: 데이터 불일치 또는 오류 인지 시, 기존의 고정 관념(Cache)을 즉시 파기하고 제로 베이스에서 다시 추론하도록 강제.
    - **Protocol 0-BETA (Grounding First)**: AI가 답변을 내놓기 전, 반드시 내부 지식 베이스와 공개 인터넷 정보를 교차 검증하도록 하는 선제적 조회 로직.

### 🧩 D. 서비스 계층 (Delivery & Edge Layer)
- **Hosting**: **Vercel (Next.js)**.
- **로직**:
    - **Headless CMS Interface**: 프론트엔드는 껍데기만 존재하며, 모든 메뉴 구성과 AI 연결은 스프레드시트 데이터에 따라 동적으로 생성(Dynamic Hydration).
    - **Multi-tenant Distribution**: 하나의 소스 코드로 여러 개의 서로 다른 브랜드(Hubs)를 운영하는 멀티 테넌트 전략.

---

## 3. 핵심 로직 플로우 (Core Logic Flow)

1.  **Trigger**: 사용자가 특정 도구(Gem)를 선택하여 질문 입력.
2.  **Config Fetch**: 시스템이 스프레드시트에서 해당 도구의 **`System Prompt`**, **`Knowledge Source ID`**, **`Admin ID`**를 파싱.
3.  **Knowledge Extraction**: Vertex AI가 지정된 `Knowledge Source`에서 질문과 가장 유사한 맥락(Context)을 추출.
4.  **Strict Inference**:
    - Gemini가 [추출된 맥락] + [제약 조건]을 기반으로 답변 설계.
    - **Protocol 0-BETA** 적용: 실시간 법령/뉴스 정보와 대조.
5.  **Formatted Output**: 가독성 강화 지침(불릿, 줄바꿈)과 고정 푸터(면책 고지, 추가 탐색 번호)를 결합하여 최종 응답 전달.

---

## 4. 인프라 구축 제언 (Implementation Stack)

- **AI Engine**: Google Cloud Vertex AI (Gemini 1.5 Pro/Flash)
- **Backend**: Vercel Serverless Functions (Node.js/Python)
- **Database/CMS**: Google Sheets API + Google Cloud Storage (Vector DB)
- **Security**: VPC Service Controls + Gemini Enterprise Encryption

---

## 결론 (Expert's Opinion)
이 설계는 **"전문가의 지식을 관리하는 것은 쉽고, AI의 답변은 전문가 수준으로 정교하며, 데이터 보안은 완벽하게 격리된"** 최상위 엔터프라이즈 AI 모델입니다. 

단순히 챗봇을 만드는 것이 아니라, **'데이터 관리 체계'**를 설계하는 것이 본 서비스의 핵심 성공 요인(KSF)입니다.
