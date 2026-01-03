"""
KSIC level 4 데이터 정리 스크립트

중복 제거 및 CSV 형식으로 정리합니다.
"""

import pandas as pd
import os


def clean_ksic_level4(input_file: str, output_file: str = None):
    """
    KSIC level 4 데이터를 정리합니다.

    Args:
        input_file: 입력 파일 경로
        output_file: 출력 파일 경로 (기본값: 입력파일명_cleaned.csv)
    """
    print(f"입력 파일: {input_file}")

    # 파일 존재 확인
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {input_file}")

    # 출력 파일 경로 설정
    if output_file is None:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_cleaned.csv"

    print(f"출력 파일: {output_file}")

    # 파일 읽기 (탭으로 구분)
    try:
        df = pd.read_csv(input_file, sep='\t', header=None, encoding='utf-8')
        print(f"원본 데이터 형태: {df.shape}")
        print(f"원본 컬럼 수: {len(df.columns)}")

        # 컬럼명 설정
        if len(df.columns) >= 2:
            df.columns = ['세분류코드', '세분류명']
        else:
            df.columns = [f'col_{i}' for i in range(len(df.columns))]

        print(f"설정된 컬럼명: {list(df.columns)}")

        # 데이터 미리보기
        print("\n=== 원본 데이터 미리보기 ===")
        print(df.head(10))

        # 중복 제거 전 통계
        print("\n=== 중복 제거 전 통계 ===")
        print(f"총 행 수: {len(df)}")
        print(f"중복 행 수: {len(df) - len(df.drop_duplicates())}")

        # 중복 제거
        df_cleaned = df.drop_duplicates()

        # 중복 제거 후 통계
        print("\n=== 중복 제거 후 통계 ===")
        print(f"총 행 수: {len(df_cleaned)}")
        print(f"제거된 중복 행 수: {len(df) - len(df_cleaned)}")

        # 정리된 데이터 미리보기
        print("\n=== 정리된 데이터 미리보기 ===")
        print(df_cleaned.head(10))

        # CSV로 저장
        df_cleaned.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n✅ 저장 완료: {output_file}")

        # 추가 통계
        print("\n=== 최종 결과 ===")
        print(f"파일 크기: {os.path.getsize(output_file):,} bytes")
        print(f"행 수: {len(df_cleaned)}")
        print(f"열 수: {len(df_cleaned.columns)}")

        # 세분류코드별 통계
        if '세분류코드' in df_cleaned.columns:
            print(f"\n세분류코드별 항목 수: {len(df_cleaned['세분류코드'].unique())}")

        return df_cleaned

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        raise


def main():
    """메인 함수"""
    # 현재 작업 디렉토리의 KSIC 폴더에서 level_4.csv 찾기
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, "KSIC", "level_4.csv")

    try:
        df = clean_ksic_level4(input_file)

        print("\n=== 추가 분석 ===")
        # 헤더 행 제외하고 숫자 코드만 추출
        numeric_codes = pd.to_numeric(df['세분류코드'], errors='coerce').dropna()
        if not numeric_codes.empty:
            print(f"세분류코드 범위: {int(numeric_codes.min())} - {int(numeric_codes.max())}")
        else:
            print("세분류코드 범위를 계산할 수 없습니다 (숫자가 아님)")

        # 중복된 세분류코드 확인
        duplicates = df[df.duplicated(subset=['세분류코드'], keep=False)]
        if not duplicates.empty:
            print("⚠️ 동일한 세분류코드를 가진 항목들:")
            print(duplicates.sort_values('세분류코드'))

    except Exception as e:
        print(f"처리 실패: {str(e)}")


if __name__ == "__main__":
    main()

