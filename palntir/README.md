# Palantir Foundry 데이터 다운로더

Palantir Foundry에서 데이터셋을 다운로드하는 스크립트입니다.

## ⚠️ 중요 안내

**현재 Foundry 인스턴스의 API 접근 설정으로 인해 자동 다운로드가 제한될 수 있습니다.**

자동 다운로드가 작동하지 않는 경우, `MANUAL_DOWNLOAD.md` 파일을 참조하여 Foundry 웹 인터페이스에서 직접 다운로드하세요.

## 설치

필요한 패키지를 설치합니다:

```bash
cd /Users/daegyunggang/Desktop/workspace/indgram
uv sync
```

또는 개별 설치:

```bash
pip install requests pandas pyarrow
```

## 설정

### 1. Foundry API 토큰 획득

1. Palantir Foundry 웹사이트에 로그인 (`https://bigseoul.usw-22.palantirfoundry.com`)
2. 사용자 설정 → API 토큰 생성
3. 토큰을 `palntir/token.txt` 파일에 저장 (이미 저장됨)

### 2. 환경 설정

현재 설정:
- **Foundry URL**: `https://bigseoul.usw-22.palantirfoundry.com`
- **데이터셋 RID**: `ri.foundry.main.dataset.a60255aa-23e1-41ce-a0f0-448337578971`

## 사용법

### 기본 사용

```bash
cd palntir
python download.py
```

### Python 코드에서 사용

```python
from download import download_dataset

# CSV 형식으로 다운로드
df = download_dataset(
    dataset_rid="ri.foundry.main.dataset.a60255aa-23e1-41ce-a0f0-448337578971",
    output_path="./data/my_data.csv",
    output_format="csv"
)

# Parquet 형식으로 다운로드
df = download_dataset(
    dataset_rid="ri.foundry.main.dataset.a60255aa-23e1-41ce-a0f0-448337578971",
    output_path="./data/my_data.parquet",
    output_format="parquet"
)
```

## 파라미터

- `dataset_rid`: Foundry 데이터셋 RID (필수)
- `output_path`: 저장할 파일 경로 (선택, 기본값: `{dataset_name}.{format}`)
- `output_format`: 출력 형식 (선택, 기본값: "csv")
  - `"csv"`: CSV 파일
  - `"parquet"`: Parquet 파일
  - `"json"`: JSON 파일
- `foundry_token`: Foundry API 토큰 (선택, 환경변수 또는 token.txt 사용 권장)
- `foundry_hostname`: Foundry 호스트명 (선택, 기본값: bigseoul.usw-22.palantirfoundry.com)
- `branch`: 데이터셋 브랜치 (선택, 기본값: "master")

## 출력

데이터는 `palntir/data/` 디렉토리에 저장됩니다.

## 문제 해결

### 인증 오류
- `token.txt` 파일에 올바른 토큰이 있는지 확인
- 토큰이 만료되지 않았는지 확인
- 토큰에 데이터셋 읽기 권한이 있는지 확인

### 404 오류 (파일을 찾을 수 없음)
- 데이터셋 RID가 올바른지 확인
- 데이터셋에 대한 접근 권한이 있는지 확인
- **API 접근이 제한된 경우**: `MANUAL_DOWNLOAD.md`의 수동 다운로드 가이드를 참조하세요

### 네트워크 오류
- `FOUNDRY_HOSTNAME`이 올바르게 설정되었는지 확인
- 네트워크 연결 상태 확인
- VPN 연결이 필요한지 확인

## 대안 방법

### 1. Foundry 웹 인터페이스에서 직접 다운로드 (권장)

가장 확실한 방법입니다. 자세한 내용은 `MANUAL_DOWNLOAD.md` 참조.

1. `https://bigseoul.usw-22.palantirfoundry.com`에 로그인
2. 데이터셋 검색: `ri.foundry.main.dataset.a60255aa-23e1-41ce-a0f0-448337578971`
3. "Export" 또는 "Download" 버튼 클릭
4. CSV 형식 선택 후 다운로드

### 2. Foundry Workshop 사용

1. Workshop에서 데이터셋 열기
2. "Export to CSV" 기능 사용

### 3. Foundry Code Repositories

Python Transforms를 사용하여 데이터에 접근:

```python
from transforms.api import Input, Output

@transform_df(
    Output("/my/output"),
    df=Input("ri.foundry.main.dataset.a60255aa-23e1-41ce-a0f0-448337578971")
)
def compute(df):
    return df
```

## 파일 구조

```
palntir/
├── download.py           # 메인 다운로더 스크립트
├── example_usage.py      # 사용 예제
├── README.md            # 이 파일
├── MANUAL_DOWNLOAD.md   # 수동 다운로드 가이드
├── requirements.txt     # 필요한 패키지 목록
├── token.txt           # API 토큰 (보안을 위해 .gitignore에 포함)
└── data/               # 다운로드된 데이터 저장 폴더
```

## 보안 주의사항

- `token.txt` 파일을 Git에 커밋하지 마세요 (이미 .gitignore에 포함됨)
- API 토큰을 다른 사람과 공유하지 마세요
- 토큰이 유출된 경우 즉시 Foundry에서 토큰을 무효화하세요

## 현재 설정된 데이터셋

```
RID: ri.foundry.main.dataset.a60255aa-23e1-41ce-a0f0-448337578971
Foundry URL: https://bigseoul.usw-22.palantirfoundry.com
```

이 RID를 변경하려면 `download.py`의 `DATASET_RID` 변수를 수정하거나, 함수를 직접 호출할 때 다른 RID를 전달하세요.

## 지원

- Foundry 공식 문서: https://www.palantir.com/docs/foundry/
- 조직 내부 Foundry 지원팀에 문의
- API 접근 권한이 필요한 경우 Foundry 관리자에게 문의

---

**문제가 지속되면** `MANUAL_DOWNLOAD.md`의 가이드를 따라 Foundry 웹 인터페이스에서 직접 다운로드하세요.
