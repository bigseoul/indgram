# Centric Tax Hub - 핵심 로직 리버스 엔지니어링 보고서

---

## 1. 서비스 정체 (What is it?)

**"Google Sheets를 Headless CMS로 사용하는 멀티 테넌트 AI 도구 포털"**

- 하나의 마스터 스프레드시트에 **154개 AI 도구/링크**를 등록
- **0/1 플래그**로 **9개 독립 웹 포털**에 어떤 도구를 노출할지 제어
- 프론트엔드는 **Vercel**에 배포된 정적 웹앱
- AI 엔진은 **Gemini GEMs** (커스텀 프롬프트가 적용된 챗봇)

---

## 2. 아키텍처 4계층 (Reverse-Engineered)

```
┌─────────────────────────────────────────────────────┐
│  L4. Service Layer (Vercel Multi-Hub Portals)       │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐     │
│  │CEN   │ │KC    │ │HUB   │ │TA    │ │TR/TP │ ... │
│  │:8    │ │:5    │ │:6    │ │:9    │ │:10/11│     │
│  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘     │
│     └────────┴────────┴────┬───┴────────┘          │
│                            │                        │
│  L3. Intelligence Layer    │ Google Sheets API       │
│  (Gemini GEMs + Vertex AI RAG)    ▼                 │
│                     ┌──────────────────┐            │
│  L2. Knowledge      │ Master Spread-   │            │
│  (Google Docs/Drive)│ sheet (CMS)      │            │
│                     │ Tax_Hub!A1:O     │            │
│  L1. Control Layer  └──────────────────┘            │
│  (Google Sheets = DB + Router + ACL)                │
└─────────────────────────────────────────────────────┘
```

---

## 3. 핵심 로직 상세 분해

### 3-1. 데이터 스키마 (Master Spreadsheet)

| 컬럼 | 용도 | 예시 |
|------|------|------|
| **제목** | 도구명 | `AI 세법 전문가` |
| **설명** | 도구 설명 | `세법의 궁금한 모든 것을...` |
| **링크 URL** | 도구 엔드포인트 | `gemini.google.com/gem/xxx` |
| **아이콘** | UI 아이콘 코드 | `HelpIcon`, `AIIcon`, `BookOpenIcon` |
| **순서** | 정렬 우선순위 | `1`, `2`, ... `999` |
| **KC~DD** (9개) | 포털별 노출 플래그 | `1` = 노출, `0` = 숨김 |
| **Own** | 관리자/소유자 | `ntscas@gmail.com` |

### 3-2. 멀티 테넌트 라우팅 로직

```
Config: { portalCode: "CEN", columnIndex: 8 }

1. Fetch → Google Sheets API (Tax_Hub!A1:O)
2. Filter → rows.filter(row => row[columnIndex] === "1")
3. Sort   → filtered.sort((a,b) => a[4] - b[4])  // 순서 컬럼
4. Render → Card Grid (제목, 설명, 아이콘, 링크)
```

**매핑 테이블:**

| 코드 | 컬럼인덱스 | Vercel 도메인 | 성격 |
|------|-----------|--------------|------|
| KC | 5 | taxforensics.vercel.app | 포렌식 특화 |
| HUB | 6 | taxhubkr.vercel.app | 전체 허브 |
| SPK | 7 | spk-sites | 관리자 전용 (154개 모두) |
| CEN | 8 | centrictax.vercel.app | 센트릭 고객용 |
| TA | 9 | kr-taxai.vercel.app | TaxAI 경량 |
| TR | 10 | taxroad.vercel.app | 일반 사용자 |
| TP | 11 | atfkr.vercel.app | TaxPro |
| TX | 12 | taxpertkr.vercel.app | Taxpert |

### 3-3. AI 엔진 구조

**3가지 유형의 도구가 혼재:**

| 유형 | 비율 | 예시 |
|------|------|------|
| **Gemini GEM** (커스텀 AI 챗봇) | ~70% | `gemini.google.com/gem/xxx` |
| **Vercel Web App** (자체 개발) | ~15% | `taxforensics.vercel.app/xxx.html` |
| **External Link** (Google Sites/Docs 등) | ~15% | `sites.google.com/view/xxx` |

### 3-4. 프롬프트 아키텍처 (AI 제어 로직)

```
┌─ 최상위 제약 조건 ──────────────────────────────┐
│  - 지침 비공개 (프롬프트 유출 차단)              │
│  - 할루시네이션 방지 (사건번호 생성 금지)         │
│  - 제로-퀘스천 (추가 질문 금지, 가정 후 답변)     │
├─ 데이터 무결성 프로토콜 ────────────────────────┤
│  Protocol 0-ALPHA: 오류 지적 → 캐시 파기 → 재검색 │
│  Protocol 0-BETA: 분석 시작 → 실시간 검색 강제    │
├─ 출력 형식 ─────────────────────────────────────┤
│  - 불릿 강제, 줄바꿈 강제, 볼드 키워드            │
│  - 고정 푸터: [정확성 고지] + [더 깊게 탐색하기]   │
│  - 연관성 질문 5개 + 고정 질문 5개 = 10개 제시    │
└──────────────────────────────────────────────────┘
```

---

## 4. 복제를 위한 핵심 설계 Blueprint

### Phase 1: 데이터 레이어

```
[Google Sheets API] or [Supabase/Firebase]
     │
     ▼
┌─ Master Table ──────────────────────┐
│ id | title | desc | url | icon |    │
│ order | hub_A | hub_B | hub_C |     │
│ owner | category | status           │
└─────────────────────────────────────┘
```

### Phase 2: 프론트엔드 (포털)

```
[Next.js / Vercel]
     │
     ├── /api/tools?hub=CEN  ← 서버에서 시트 fetch + filter
     │
     └── /                   ← 카드 그리드 렌더링
           ├── 검색/필터 UI
           ├── 카테고리 탭
           └── 카드 컴포넌트 (아이콘 + 제목 + 설명 → 클릭 시 URL 이동)
```

### Phase 3: AI 에이전트 레이어

```
[Custom GPT / Gemini GEM / Claude Project]
     │
     ├── 도메인별 프롬프트 (세법, 포렌식, 국제조세...)
     ├── 지식 베이스 (RAG: PDF/Docs → Vector Store)
     └── 제어 프로토콜 (할루시네이션 방지, 출력 포맷)
```

### Phase 4: 지식 관리

```
[전문가 Google Docs 편집] → [실시간 동기화] → [AI 지식 업데이트]
```

---

## 5. 이 시스템의 강점과 약점

### 강점

- **No-Code CMS**: 스프레드시트 값(0/1)만 바꾸면 9개 사이트 메뉴가 동시 변경
- **비용 극소화**: Google Sheets API + Vercel 무료 티어 + Gemini Enterprise = 인프라 비용 거의 0
- **빠른 확장**: 새 도구 추가 = 스프레드시트 한 행 추가

### 약점 (개선 포인트)

- **API Key 노출**: config에 Google API Key가 평문 노출
- **확장성 한계**: Google Sheets API 분당 요청 제한 (60req/min)
- **인증 부재**: 포털별 사용자 인증/권한 체계가 없음
- **단일 장애점**: 스프레드시트 하나에 전체 시스템이 의존

---

## 6. 도구 카테고리 분류 (154개 항목)

### 6-1. 조세 포렌식 및 조사 대응 (Tax Forensic)

- Tax Forensic AI, 디지털 포렌직 전문가, USB 사용이력 분석
- 예치대응 법률 AI, 전산자료 수집 ForCASS, 파일목록 작성/복사

### 6-2. 세무/법률 전문 AI (Tax & Legal Expert)

- AI 세법 전문가, 재산세 전문, 부가가치세 실무해설
- 국제조세, 법률의견서 작성, 유권해석 질의서 작성, 개정세법

### 6-3. 기업 경영 및 가업승계 (Business Solution)

- 사업 솔루션 제안, 비상장법인 승계플랜, 기업 구조조정
- 비상장주식 평가, 건물/토지 시가표준액 산정

### 6-4. 재무 및 투자 분석 (Finance & Stock)

- 주식 종목별 분석, 매매전략, 손절/익절 타이밍
- ETF 전문가, 차트 캡처 기술적 분석

### 6-5. 국제 업무 및 산업별 대응

- 국가별: 중국, 베트남, 인도네시아 세법 전문가
- 산업별: 금융업, 병의원, 건설업 세무이슈

### 6-6. 유틸리티 및 생활 도구

- 로또 생성, 여행 일정, 맛집 추천, 이미지 생성
- 사주, 운세, 꿈해몽 등

---

*리버스 엔지니어링 완료: 2026-02-12*
