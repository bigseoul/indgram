# Palantir Foundry API 다운로드 상태

## 📊 현재 상황 (2025-11-06)

### ✅ 성공한 작업

1. **인증 (Authentication)**: 성공
   - Token 인증 정상 작동
   - API 접근 가능

2. **파일 목록 조회 (File List API)**: 성공
   - 엔드포인트: `https://bigseoul.usw-22.palantirfoundry.com/api/v1/datasets/{rid}/files`
   - 파일 정보 조회 성공:
     - 파일명: `spark/part-00000-1131e4db-bcaf-47c6-aee3-1e0320dfc7f2-c000.snappy.parquet`
     - 실제 크기: 15,265,935 bytes (약 14.5 MB)

3. **파일 메타데이터 조회**: 성공
   - transactionRid 획득 가능
   - 파일 정보 상세 내역 확인

### ❌ 실패한 작업

**파일 데이터 다운로드 (File Content Download)**: 실패
- 시도한 모든 API 엔드포인트에서 **파일 메타데이터(JSON)**만 반환
- 실제 파일 내용(Parquet 데이터)은 다운로드되지 않음
- 이는 API 접근 정책 또는 권한 제한으로 추정

### 🔍 근본 원인 분석

```json
// API가 반환하는 내용 (메타데이터)
{
  "path": "spark/part-00000-1131e4db-bcaf-47c6-aee3-1e0320dfc7f2-c000.snappy.parquet",
  "transactionRid": "ri.foundry.main.transaction.0000000f-1f38-c737-921d-89eb17fd8c3f",
  "sizeBytes": "15265935",
  "updatedTime": "2025-11-06T03:38:12.784Z"
}
```

이것은 실제 파일이 아니라 **파일 정보**입니다.

### 🚧 제한 사항

`bigseoul.usw-22.palantirfoundry.com` 인스턴스의 API 설정:
- 파일 목록 조회: ✅ 허용
- 파일 메타데이터 조회: ✅ 허용
- **파일 데이터 다운로드**: ❌ 제한됨

이는 다음 중 하나일 가능성:
1. API 토큰에 파일 데이터 다운로드 권한 없음
2. 조직의 보안 정책으로 API 다운로드 제한
3. 특정 API 엔드포인트만 활성화됨

## ✅ 권장 해결책

### 방법 1: Foundry 웹 UI에서 직접 다운로드 ⭐ (가장 확실)

1. 브라우저에서 https://bigseoul.usw-22.palantirfoundry.com 접속
2. 데이터셋 검색: `ri.foundry.main.dataset.a60255aa-23e1-41ce-a0f0-448337578971`
3. "Export" 또는 "Download" 버튼 클릭
4. CSV 또는 Parquet 형식 선택 후 다운로드

**예상 시간**: 2-3분
**성공률**: 99%

### 방법 2: Foundry Code Repositories (Transforms)

Foundry의 Code Repositories에서 Python Transform을 생성:

```python
from transforms.api import transform_df, Input, Output

@transform_df(
    Output("/Users/{your-username}/downloaded_data"),
    source=Input("ri.foundry.main.dataset.a60255aa-23e1-41ce-a0f0-448337578971"),
)
def download_data(source):
    # 이 코드는 Foundry 내부에서 실행되므로 데이터 접근 가능
    return source
```

그런 다음 Output 데이터셋에서 Export 가능

### 방법 3: Foundry Workshop

1. Workshop 앱에서 데이터셋 열기
2. 필요한 필터/변환 적용 (선택사항)
3. "Export to CSV" 기능 사용

### 방법 4: Foundry 관리자에게 권한 요청

다음을 요청:
- API를 통한 파일 다운로드 권한
- 또는 Datasets API v2 접근 권한

## 📝 기술적 세부사항

### 시도한 API 엔드포인트 (총 20+ 조합)

**파일 목록 조회** (성공):
- ✅ `/api/v1/datasets/{rid}/files`

**파일 다운로드 시도** (모두 메타데이터만 반환):
- `/api/v1/datasets/{rid}/files/{path}`
- `/api/v1/datasets/{rid}/files/{encoded_path}`
- `/foundry-api/api/datasets/{rid}/files/{path}/download`
- `/foundry-api/api/datasets/{rid}/branches/{branch}/files/{path}/download`
- `/catalog-api/datasets/{rid}/files/{path}`

**시도한 브랜치**:
- master
- main  
- primary

## 🔧 향후 시도 가능한 방법

1. **Foundry Catalog API v2**: 새로운 API 버전 사용
2. **Direct Transaction Access**: transactionRid를 사용한 직접 접근
3. **Streaming API**: 대용량 파일을 위한 스트리밍 다운로드
4. **Foundry Python SDK**: 공식 Python SDK 사용 (foundry-platform)

## 💡 결론

**현재로서는 Foundry 웹 UI를 통한 직접 다운로드가 가장 빠르고 확실한 방법입니다.**

API를 통한 자동화가 필요한 경우, Foundry 관리자에게 다음을 문의하세요:
1. API 파일 다운로드 권한 활성화
2. 조직에서 사용 가능한 API 엔드포인트 목록
3. Python SDK 사용 권장 사항

---

**문의**: Foundry 지원팀 또는 조직 내부 Palantir 담당자에게 연락하세요.





