# 🔢 Tiktoken 토큰 카운터

tiktoken 라이브러리를 사용하여 텍스트 파일의 토큰 수를 계산하는 Python 유틸리티입니다.

## 📋 기능

- **단일 파일 분석**: HTML, TXT, MD 등 텍스트 파일의 토큰 수 계산
- **디렉토리 전체 분석**: 지정된 확장자의 모든 파일을 일괄 분석
- **다양한 모델 지원**: GPT-4, GPT-3.5-turbo 등 OpenAI 모델의 토큰 인코딩
- **인코딩 자동 감지**: UTF-8, CP949 등 다양한 파일 인코딩 자동 처리
- **상세한 분석 정보**: 파일 크기, 문자 수, 토큰 수, 비율 등 제공

## 🚀 사용법

### 1. 단일 파일 분석

```bash
# 기본 사용 (GPT-4 모델)
python token_counter.py "주성엔지니어링.html"

# 특정 모델 지정
python token_counter.py "주성엔지니어링.html" --model gpt-3.5-turbo
```

### 2. 디렉토리 전체 분석

```bash
# 현재 디렉토리의 HTML 파일들 분석
python token_counter.py . --extensions .html

# 여러 확장자 파일들 분석
python token_counter.py ./docs --extensions .html .txt .md
```

### 3. Python 코드에서 사용

```python
from token_counter import count_tokens_from_text, count_tokens_from_file

# 텍스트에서 직접 토큰 수 계산
text = "안녕하세요. 주성엔지니어링입니다."
token_count = count_tokens_from_text(text)
print(f"토큰 수: {token_count}")

# 파일에서 토큰 수 계산
result = count_tokens_from_file("document.html")
if result['status'] == 'success':
    print(f"파일: {result['file_path']}")
    print(f"토큰 수: {result['token_count']:,}")
    print(f"파일 크기: {result['file_size_bytes']:,} bytes")
```

## 📊 분석 결과 예시

```
📄 파일: tokenizer\주성엔지니어링.html
   파일 크기: 60,480 bytes
   문자 수: 54,799 characters
   토큰 수: 21,989 tokens
   토큰/바이트 비율: 0.3636
   사용 모델: gpt-4
```

## 🔧 주요 함수

### `count_tokens_from_text(text, model_name="gpt-4")`
- 텍스트 문자열의 토큰 수를 직접 계산
- **매개변수**: `text` (문자열), `model_name` (모델명)
- **반환**: 토큰 수 (정수)

### `count_tokens_from_file(file_path, model_name="gpt-4", encoding="utf-8")`
- 파일에서 토큰 수를 계산하고 상세 정보 제공
- **매개변수**: `file_path` (파일 경로), `model_name` (모델명), `encoding` (파일 인코딩)
- **반환**: 분석 결과 딕셔너리

### `count_tokens_from_directory(directory_path, file_extensions=None, model_name="gpt-4")`
- 디렉토리 내 모든 파일의 토큰 수를 계산
- **매개변수**: `directory_path` (디렉토리 경로), `file_extensions` (확장자 리스트), `model_name` (모델명)
- **반환**: 분석 결과 리스트

## 💰 API 비용 예상

토큰 수를 기반으로 OpenAI API 사용 비용을 예상할 수 있습니다:

- **GPT-4**: 입력 토큰당 $0.03/1K
- **GPT-3.5-turbo**: 입력 토큰당 $0.001/1K

예시 파일 (21,989 토큰):
- GPT-4 비용: ~$0.66
- GPT-3.5-turbo 비용: ~$0.022

## 🔄 모델별 토큰 수 비교

동일한 텍스트라도 모델에 따라 토큰 수가 다를 수 있습니다:

```
📝 분석 텍스트: 180 문자
--------------------------------------------------
🤖 gpt-4          : 142 토큰
🤖 gpt-3.5-turbo  : 142 토큰
```

## 📝 예제 실행

전체 기능을 테스트하려면 예제 스크립트를 실행하세요:

```bash
python example_usage.py
```

## 🛠️ 요구사항

- Python 3.12+
- tiktoken >= 0.7.0

## 📄 지원 파일 형식

기본적으로 다음 파일 형식을 지원합니다:
- `.html` - HTML 문서
- `.txt` - 텍스트 파일
- `.md` - Markdown 문서
- `.py` - Python 소스 코드
- `.js` - JavaScript 파일
- `.css` - CSS 스타일시트

## 🎯 사용 사례

1. **AI 모델 입력 크기 계산**: LLM API 호출 전 토큰 수 확인
2. **문서 분석**: 대량의 문서들의 토큰 분포 분석
3. **비용 예산 계획**: API 사용 비용 사전 계산
4. **데이터 처리**: 텍스트 데이터의 토큰 기반 분할 계획

## ⚠️ 주의사항

- 파일 인코딩이 UTF-8이 아닌 경우 자동으로 CP949로 시도합니다
- 매우 큰 파일의 경우 메모리 사용량이 클 수 있습니다
- 토큰 수는 모델별로 다를 수 있으니 정확한 비용 계산시 주의하세요 