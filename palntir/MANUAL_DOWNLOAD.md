# Palantir Foundry 데이터셋 수동 다운로드 가이드

API를 통한 자동 다운로드가 어려운 경우, Foundry 웹 인터페이스에서 직접 데이터를 다운로드할 수 있습니다.

## 방법 1: Foundry 웹 인터페이스에서 직접 다운로드 (권장)

### 단계별 가이드

1. **Foundry에 로그인**
   - 브라우저에서 `https://bigseoul.usw-22.palantirfoundry.com` 접속
   - 로그인

2. **데이터셋 찾기**
   - 왼쪽 메뉴에서 "Data" 또는 "Datasets" 클릭
   - 검색창에 데이터셋 RID 입력: `ri.foundry.main.dataset.a60255aa-23e1-41ce-a0f0-448337578971`
   - 또는 데이터셋 이름으로 검색

3. **데이터 내보내기**
   - 데이터셋 페이지에서 "Export" 또는 "Download" 버튼 클릭
   - 파일 형식 선택 (CSV, Parquet, Excel 등)
   - "Download" 클릭

4. **다운로드된 파일 확인**
   - 다운로드 폴더에서 파일 확인
   - `palntir/data/` 폴더로 이동

## 방법 2: Code Repositories에서 Python 코드 실행

Foundry의 Code Repositories에서 직접 Python 코드를 실행하여 데이터셋에 접근할 수 있습니다.

### Python 코드 예제

```python
from transforms.api import transform_df, Input, Output

@transform_df(
    Output("/path/to/output/dataset"),
    source=Input("ri.foundry.main.dataset.a60255aa-23e1-41ce-a0f0-448337578971"),
)
def compute(source):
    # 데이터 조회
    df = source
    
    # CSV로 저장 (로컬이 아닌 Foundry 내부)
    return df
```

## 방법 3: Foundry Workshop 사용

1. Foundry에서 "Workshop" 또는 "Contour" 앱 열기
2. 데이터셋을 Workshop에 추가
3. Workshop에서 "Export to CSV" 기능 사용

## 문제 해결

### Q: 데이터셋을 찾을 수 없습니다
- 데이터셋 RID가 올바른지 확인
- 데이터셋에 대한 읽기 권한이 있는지 확인
- 조직 관리자에게 권한 요청

### Q: Export 버튼이 없습니다
- 사용자 권한 확인
- 데이터셋이 너무 큰 경우 제한이 있을 수 있음
- Workshop을 통한 다운로드 시도

### Q: 다운로드가 너무 느립니다
- 더 작은 데이터셋 부분만 선택 (필터 적용)
- Parquet 형식 사용 (압축 효율이 좋음)
- 네트워크 연결 확인

## 추가 지원

- Palantir 문서: https://www.palantir.com/docs/foundry/
- 조직 내부 Foundry 지원팀에 문의
- Foundry 커뮤니티 포럼 검색

## 현재 데이터셋 정보

- **RID**: `ri.foundry.main.dataset.a60255aa-23e1-41ce-a0f0-448337578971`
- **Foundry URL**: `https://bigseoul.usw-22.palantirfoundry.com`
- **브랜치**: `master`

---

**참고**: API를 통한 자동 다운로드는 Foundry 인스턴스의 API 설정 및 권한에 따라 제한될 수 있습니다.





