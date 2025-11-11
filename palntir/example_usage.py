"""
Palantir Foundry 다운로더 사용 예제
"""

from download import download_dataset
from pathlib import Path


def example_basic_download():
    """기본 다운로드 예제"""
    print("=== 기본 다운로드 예제 ===\n")

    dataset_rid = "ri.foundry.main.dataset.a60255aa-23e1-41ce-a0f0-448337578971"

    df = download_dataset(
        dataset_rid=dataset_rid,
        output_path="./data/my_dataset.csv",
        output_format="csv",
    )

    print(f"\n다운로드 완료! {len(df)} 행이 저장되었습니다.")
    return df


def example_multiple_formats():
    """여러 포맷으로 저장하는 예제"""
    print("\n=== 여러 포맷 저장 예제 ===\n")

    dataset_rid = "ri.foundry.main.dataset.a60255aa-23e1-41ce-a0f0-448337578971"

    # CSV로 저장
    print("1. CSV 형식으로 저장...")
    df = download_dataset(
        dataset_rid=dataset_rid, output_path="./data/dataset.csv", output_format="csv"
    )

    # Parquet으로 저장 (압축 효율이 좋음)
    print("\n2. Parquet 형식으로 저장...")
    download_dataset(
        dataset_rid=dataset_rid,
        output_path="./data/dataset.parquet",
        output_format="parquet",
    )

    # JSON으로 저장
    print("\n3. JSON 형식으로 저장...")
    download_dataset(
        dataset_rid=dataset_rid, output_path="./data/dataset.json", output_format="json"
    )

    print("\n모든 형식으로 저장 완료!")
    return df


def example_data_analysis():
    """다운로드 후 데이터 분석 예제"""
    print("\n=== 데이터 분석 예제 ===\n")

    dataset_rid = "ri.foundry.main.dataset.a60255aa-23e1-41ce-a0f0-448337578971"

    # 데이터 다운로드
    df = download_dataset(
        dataset_rid=dataset_rid,
        output_path="./data/analysis_data.csv",
        output_format="csv",
    )

    # 기본 정보 출력
    print("\n--- 데이터 기본 정보 ---")
    print(f"행 개수: {len(df)}")
    print(f"열 개수: {len(df.columns)}")
    print(f"\n열 이름: {list(df.columns)}")

    # 데이터 타입 출력
    print("\n--- 데이터 타입 ---")
    print(df.dtypes)

    # 처음 5행 출력
    print("\n--- 데이터 미리보기 (처음 5행) ---")
    print(df.head())

    # 기술 통계
    print("\n--- 기술 통계 ---")
    print(df.describe())

    return df


def example_custom_credentials():
    """커스텀 인증 정보 사용 예제"""
    print("\n=== 커스텀 인증 정보 예제 ===\n")

    # 참고: 실제 사용시에는 환경변수나 안전한 방법으로 토큰을 관리하세요
    dataset_rid = "ri.foundry.main.dataset.a60255aa-23e1-41ce-a0f0-448337578971"

    df = download_dataset(
        dataset_rid=dataset_rid,
        output_path="./data/custom_auth_data.csv",
        output_format="csv",
        # foundry_token="your_custom_token_here",  # 주석 해제하고 실제 토큰 사용
        # foundry_hostname="your-company.palantirfoundry.com"  # 주석 해제하고 실제 호스트명 사용
    )

    return df


if __name__ == "__main__":
    import sys

    print("Palantir Foundry 다운로더 예제\n")
    print("실행하려는 예제를 선택하세요:")
    print("1. 기본 다운로드")
    print("2. 여러 포맷으로 저장")
    print("3. 데이터 분석")
    print("4. 커스텀 인증 정보")

    try:
        choice = input("\n선택 (1-4): ").strip()

        if choice == "1":
            example_basic_download()
        elif choice == "2":
            example_multiple_formats()
        elif choice == "3":
            example_data_analysis()
        elif choice == "4":
            example_custom_credentials()
        else:
            print("잘못된 선택입니다. 기본 다운로드를 실행합니다.")
            example_basic_download()

    except KeyboardInterrupt:
        print("\n\n프로그램이 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        print("\n확인사항:")
        print("- FOUNDRY_TOKEN 환경변수가 설정되어 있나요?")
        print("- FOUNDRY_HOSTNAME 환경변수가 올바른가요?")
        print("- 네트워크 연결이 정상인가요?")
        print("- 데이터셋에 대한 접근 권한이 있나요?")
        sys.exit(1)
