# CentricHub 핵심 로직 설계서 (역설계 기반)

## 0. 문서 목적
- `Tax_Hub` 계열 서비스와 동일한 운영 모델을 재구축하기 위한 핵심 로직을 정의한다.
- 구현 우선순위를 분리하여, `MVP(카탈로그 허브)`에서 `확장형(검증형 AI 응답)`까지 단계적으로 적용할 수 있게 한다.
- 본 문서는 기획 + 기술 설계를 동시에 다루며, 바로 개발 가능한 수준의 데이터 모델/플로우/API를 제시한다.

## 1. 근거 데이터 및 전제
- 시트 연결 정보:
  - `docs/centric/config.md:2`
  - `docs/centric/config.md:3`
  - `docs/centric/config.md:4`
- 허브별 컬럼 매핑:
  - `docs/centric/classification_analysis.md:8`
  - `docs/centric/classification_analysis.md:20`
- 계층 아키텍처 의도:
  - `docs/centric/system_architecture.md:15`
  - `docs/centric/system_architecture.md:24`
  - `docs/centric/system_architecture.md:29`
- 프롬프트/검증 정책:
  - `docs/centric/prompt_guideline.md:20`
  - `docs/centric/prompt_guideline.md:62`
  - `docs/centric/prompt_guideline.md:77`
  - `docs/centric/prompt_guideline.md:104`

## 2. 서비스 정의
- 서비스명: `CentricHub`
- 서비스 유형: `멀티 허브형 AI 서비스 카탈로그 + 링크 라우팅 플랫폼`
- 핵심 목표:
  - 비개발자(운영자)가 시트 편집만으로 메뉴를 운영
  - 허브별 다른 서비스 구성을 동일 데이터 원본에서 자동 생성
  - 장애 시에도 서비스 목록을 지속 제공

## 3. 핵심 설계 원칙
- `Single Source of Truth`: 서비스 메타데이터 원본은 Google Sheets.
- `Projection by Hub`: 허브별 화면은 동일 원본의 필터링 결과물.
- `Fail-Safe`: 원본 조회 실패 시 최근 스냅샷으로 제공.
- `Extensible`: 초기에는 링크 허브, 이후 검증형 AI 응답 엔진으로 확장.
의도는 거의 확실히 **“B2B2C 화이트라벨 프리미엄”**입니다.

즉,

신문사는 정회원 전용 혜택으로 서비스 제공
실제 서비스 엔진/운영은 당신 쪽이 담당
신문사 도메인 안에서 별도 프리미엄 메뉴로 노출
보통 이렇게 갑니다.

제공 형태
신문사 로그인(정회원 인증) 뒤 접근 가능한 전용 페이지
예: premium.news.co.kr/ai-tax 또는 신문사 앱 내 메뉴
권한 모델
비회원/일반회원: 일부 맛보기
정회원: 전체 도구(전문 에이전트, 문서분석, 포렌식 도구 등) 개방
운영 모델
신문사는 회원/결제/고객접점 담당
당신은 콘텐츠·에이전트·서비스 품질 담당
필요시 신문사 브랜드로 화이트라벨 UI 제공
수익/목적
신문사: 정회원 전환율·유지율 상승
당신: 제휴 수익(라이선스/구독 분배) + 신규 사용자 유입
지금 구조(허브+플래그 기반)상으로는, 신문사용 전용 허브 코드/테넌트를 추가해 같은 방식으로 쉽게 확장하려는 그림입니다.



## 4. 계층 구조

### 4.1 Management Layer (Control Plane)
- 역할: 메뉴/노출/우선순위 제어.
- 데이터: `제목`, `설명`, `링크 URL`, `아이콘`, `순서`, 허브 플래그(`KC..DD`), `Own`.
- 핵심: 코드 배포 없이 운영 정책 변경 가능.

### 4.2 Service Layer (Delivery)
- 역할: 허브 화면 렌더 + 링크 라우팅.
- 출력: 허브별 카드 목록, 검색, 클릭 이동.

### 4.3 Intelligence Layer (Optional)
- 역할: 문서에서 정의한 검증 프로토콜 기반 AI 응답.
- 핵심: `0-BETA` 선검증, `0-ALPHA` 오류 시 캐시 폐기.

## 5. 데이터 모델

### 5.1 ServiceItem
- `id: string` (제목+URL 해시 권장)
- `title: string`
- `description: string`
- `url: string`
- `icon: string`
- `order: number`
- `flags: { KC,HUB,SPK,CEN,TA,TR,TP,TX,DD }`
- `owner: string`
- `status: 'active' | 'hidden' | 'invalid'`

### 5.2 HubConfig
- `code: 'KC' | 'HUB' | ...`
- `columnIndex: number` (`CEN=8` 등)
- `displayName: string`
- `domainHint: string`

### 5.3 CatalogSnapshot
- `version: string`
- `fetchedAt: string`
- `sourceRange: string`
- `items: ServiceItem[]`
- `checksum: string`

### 5.4 ClickEvent
- `hubCode: string`
- `serviceId: string`
- `url: string`
- `timestamp: string`
- `clientMeta: object`

## 6. 핵심 처리 플로우

### 6.1 Ingestion
1. `Tax_Hub!A1:O` 조회.
2. 헤더 기반 인덱싱.
3. 행별 정규화:
   - `order`: 숫자 변환 실패 시 `9999`
   - `icon`: 공백이면 기본값
   - `url`: 공백이면 `status=invalid`
4. 검증:
   - 필수 필드(`title`) 누락 시 제외
   - URL 프로토콜 비정상 시 제외

### 6.2 Projection
1. 입력: `hubCode` (예: `CEN`)
2. `flags[hubCode] == 1` 필터
3. `url != ''` 필터
4. 정렬: `order ASC`, tie-breaker `title ASC`
5. 출력: 카드 렌더용 DTO

### 6.3 Delivery
1. `/hub/:code` 진입
2. 프론트가 `/api/catalog?hub=:code` 호출
3. 응답으로 카드 렌더
4. 클릭 시 새 탭 라우팅 + `ClickEvent` 기록

### 6.4 Fallback
1. API 실패
2. 최근 `CatalogSnapshot` 반환
3. 스냅샷도 없으면 최소 정적 메뉴 반환

## 7. 핵심 알고리즘 (의사코드)

```ts
function buildHubMenu(hubCode: HubCode): ServiceItem[] {
  const hubMap = loadHubMapping(); // CEN -> 8
  const rows = loadSheetRows("Tax_Hub!A1:O");
  const items = rows.map(normalize).filter(validate);

  const visible = items
    .filter((i) => i.flags[hubCode] === 1)
    .filter((i) => i.url.length > 0);

  return visible.sort((a, b) =>
    a.order !== b.order ? a.order - b.order : a.title.localeCompare(b.title)
  );
}
```

## 8. API 설계 (MVP)

### 8.1 `GET /api/catalog?hub=CEN`
- 기능: 허브별 메뉴 반환
- 응답:
  - `hubCode`
  - `fetchedAt`
  - `source` (`live` | `snapshot` | `fallback`)
  - `items[]`

### 8.2 `POST /api/events/click`
- 기능: 카드 클릭 이벤트 저장
- 입력:
  - `hubCode`, `serviceId`, `url`, `timestamp`, `clientMeta`

### 8.3 `GET /api/health/catalog`
- 기능: 시트 조회/스냅샷 상태 점검
- 응답:
  - `sheetReachable`
  - `lastSuccessAt`
  - `snapshotAgeSec`

## 9. 운영 배치 로직

### 9.1 링크 품질 점검 (주기 배치)
- 점검:
  - 2xx/3xx 여부
  - 도메인별 실패율
  - 빈 URL 항목
- 출력:
  - 운영 리포트(`dead links`, `invalid rows`)

### 9.2 데이터 정합성 검사
- 점검:
  - 중복 제목/중복 URL
  - 비정상 순서값
  - 허브 플래그 미설정 행
  - 미등록 아이콘 키

## 10. 보안/권한 설계
- API 키는 브라우저에 노출하지 않고 서버에서만 사용.
- 허용 URL 도메인 화이트리스트 운영.
- 관리자 기능(편집/배치 실행)은 OAuth 기반 계정 제한.
- 감사로그는 삭제 불가 스토리지(append-only) 권장.

## 11. 관측성(Observability)
- 필수 지표:
  - 허브별 노출 항목 수
  - 클릭 수/CTR
  - 조회 실패율
  - snapshot fallback 비율
- 알림 조건:
  - 시트 연속 실패 N회
  - 핵심 도메인 링크 실패율 임계치 초과

## 12. AI 응답 엔진 확장 로직 (옵션)

### 12.1 상태머신
1. `Claim Input`
2. `Protocol 0-BETA`: 실시간 사실 조회
3. `Evidence Validation`: 법령/판례/예규 교차 검증
4. `Compose`: 답변 + 고정 푸터
5. `Protocol 0-ALPHA`: 오류 지적 시 오염 캐시 파기 후 재실행

### 12.2 강제 규칙
- 임의 사건번호/판례번호 생성 금지
- 내부 프롬프트/운영 지침 노출 금지
- 불확실 시 `명시적 규정 없음` 명시

## 13. 구현 로드맵

### Phase 1 (1주)
- `catalog` 정규화 모듈
- `GET /api/catalog` + CEN 허브 UI
- 기본 캐시(메모리)

### Phase 2 (2주)
- 스냅샷 fallback + health endpoint
- 클릭 이벤트 저장
- 링크 헬스체크 배치

### Phase 3 (3주+)
- 운영 대시보드
- 권한 체계
- AI 응답형 상태머신(0-A/0-B) 적용

## 14. 즉시 개발 체크리스트
- [ ] 시트 헤더 기반 파서 구현
- [ ] 허브 코드 enum/검증기 구현
- [ ] 정렬/필터 유닛 테스트
- [ ] snapshot fallback 테스트
- [ ] 링크 점검 배치와 알림 채널 연결

---
작성일: 2026-02-12  
버전: v1.0  
작성기준: `docs/centric` 분석 결과 + 역설계 결과
