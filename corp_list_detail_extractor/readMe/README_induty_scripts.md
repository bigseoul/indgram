# KSIC 산업 분류 코드 추가 스크립트

이 폴더에는 `dart_corp_list.csv` 파일에 KSIC 산업 분류 코드를 기반으로 `induty_name` 컬럼을 추가하는 Python 스크립트들이 있습니다.

## 스크립트 설명

### 1. `add_induty_name_level2_only.py`
- **사용 레벨**: `level_2.csv`만 사용
- **특징**: 가장 기본적인 대분류(2자리 코드)만 매핑
- **매칭률**: 약 7.4%
- **출력 파일**: `dart_corp_list_with_induty_name.csv`

### 2. `add_induty_name_levels_3_4_5.py`
- **사용 레벨**: `level_3.csv`, `level_4.csv`, `level_5.csv`
- **특징**: 세부적인 산업 분류 (3,4,5자리 코드) 매핑
- **매칭률**: 약 92.0%
- **출력 파일**: `dart_corp_list_with_detailed_induty_name.csv`

### 3. `add_induty_name_complete_levels.py`
- **사용 레벨**: `level_2.csv`, `level_3.csv`, `level_4.csv`, `level_5.csv` 모두 사용
- **특징**: 완전한 산업 분류 매핑 (우선순위: 5자리 > 4자리 > 3자리 > 2자리)
- **매칭률**: 약 99.3%
- **출력 파일**: `dart_corp_list_complete_induty_name.csv`

## 사용법

```bash
# 각 스크립트 실행
python add_induty_name_level2_only.py
python add_induty_name_levels_3_4_5.py
python add_induty_name_complete_levels.py
```

## 출력 결과 비교

| 스크립트 | 매칭 개수 | 매칭률 | 특징 |
|---------|-----------|--------|------|
| Level 2 Only | 8,422개 | 7.4% | 대분류만 |
| Levels 3,4,5 | 105,142개 | 92.0% | 세부 분류 |
| Complete | 113,564개 | 99.3% | 완전 매핑 |

## 예시 결과

### Level 2 Only
```
(주)연방건설산업: 42 -> 전문직별 공사업
```

### Levels 3,4,5
```
(주)다코: 25931 -> 날붙이 제조업
브룩스피알아이: 2612 -> 다이오드, 트랜지스터 및 유사 반도체 소자 제조업
```

### Complete Levels
```
(주)연방건설산업: 42 -> 전문직별 공사업
(주)다코: 25931 -> 날붙이 제조업
브룩스피알아이: 2612 -> 다이오드, 트랜지스터 및 유사 반도체 소자 제조업
```

## 주의사항

- 입력 파일: `dart_corp_list.csv` (KSIC 폴더에 있어야 함)
- 모든 스크립트는 `induty_code` 컬럼 다음에 `induty_name` 컬럼을 추가합니다
- 기존 파일을 덮어쓰지 않도록 서로 다른 출력 파일명을 사용합니다
