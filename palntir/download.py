"""
Palantir Foundry Dataset Downloader

이 스크립트는 Palantir Foundry에서 데이터셋을 다운로드합니다.
Foundry REST API를 사용합니다.
"""

import os
import json
from pathlib import Path
import requests
import pandas as pd


def download_dataset(
    dataset_rid: str,
    output_path: str = None,
    output_format: str = "csv",
    foundry_token: str = None,
    foundry_hostname: str = None,
    branch: str = "master",
):
    """
    Palantir Foundry에서 데이터셋을 다운로드합니다.

    Args:
        dataset_rid: Foundry 데이터셋 RID (예: ri.foundry.main.dataset.xxx)
        output_path: 저장할 파일 경로 (기본값: 현재 디렉토리에 dataset_rid.csv)
        output_format: 출력 형식 ('csv', 'parquet', 'json')
        foundry_token: Foundry API 토큰 (없으면 환경변수 FOUNDRY_TOKEN 사용)
        foundry_hostname: Foundry 호스트명 (없으면 환경변수 FOUNDRY_HOSTNAME 사용)
        branch: 데이터셋 브랜치 (기본값: master)
    """
    # 인증 정보 설정
    # 1. 파라미터로 전달된 토큰 사용
    # 2. 환경변수 사용
    # 3. token.txt 파일에서 읽기
    token = foundry_token or os.getenv("FOUNDRY_TOKEN")

    if not token:
        # token.txt 파일이 있으면 읽기
        token_file = Path(__file__).parent / "token.txt"
        if token_file.exists():
            token = token_file.read_text().strip()
            print("token.txt 파일에서 인증 토큰을 로드했습니다.")

    hostname = foundry_hostname or os.getenv(
        "FOUNDRY_HOSTNAME", "bigseoul.usw-22.palantirfoundry.com"
    )

    if not token:
        raise ValueError(
            "Foundry API 토큰이 필요합니다. "
            "환경변수 FOUNDRY_TOKEN을 설정하거나 foundry_token 파라미터를 제공하세요."
        )

    # 요청 헤더 설정
    headers = {
        "Authorization": f"Bearer {token}",
    }

    # 데이터셋 다운로드
    print(f"Foundry에 연결 중... (hostname: {hostname})")
    print(f"데이터셋 다운로드 중: {dataset_rid}")
    print(f"브랜치: {branch}\n")

    try:
        # 1. Foundry REST API로 파일 목록 조회
        files_url = f"https://{hostname}/foundry-api/api/datasets/{dataset_rid}/branches/{branch}/files"
        print("파일 목록 조회 중...")
        print(f"URL: {files_url}")

        # 시도할 브랜치 목록
        branches_to_try = [branch, "master", "main", "primary"]
        # 중복 제거
        branches_to_try = list(dict.fromkeys(branches_to_try))

        # 시도할 API 엔드포인트 패턴
        api_patterns = [
            "/foundry-api/api/datasets/{rid}/branches/{branch}/files",
            "/foundry-api/api/datasets/{rid}/files",
            "/api/v1/datasets/{rid}/branches/{branch}/files",
            "/api/v1/datasets/{rid}/files",
            "/catalog-api/api/datasets/{rid}/branches/{branch}/files",
        ]

        files_response = None
        successful_url = None
        successful_branch = None

        for branch_name in branches_to_try:
            if files_response and files_response.status_code == 200:
                break

            for pattern in api_patterns:
                # 브랜치가 필요한 패턴인지 확인
                if "{branch}" in pattern:
                    files_url = f"https://{hostname}{pattern.format(rid=dataset_rid, branch=branch_name)}"
                else:
                    files_url = f"https://{hostname}{pattern.format(rid=dataset_rid)}"

                print(f"\n시도: {files_url}")

                try:
                    response = requests.get(files_url, headers=headers, timeout=30)

                    if response.status_code == 200:
                        files_response = response
                        successful_url = files_url
                        successful_branch = (
                            branch_name if "{branch}" in pattern else "N/A"
                        )
                        print("✅ 성공!")
                        break
                    else:
                        print(f"❌ 실패 (상태 코드: {response.status_code})")

                except Exception as e:
                    print(f"❌ 오류: {str(e)}")
                    continue

        if not files_response or files_response.status_code != 200:
            raise ValueError(
                f"모든 API 엔드포인트에서 파일 목록 조회 실패\n\n"
                f"시도한 엔드포인트: {len(api_patterns) * len(branches_to_try)}개\n"
                f"시도한 브랜치: {', '.join(branches_to_try)}\n\n"
                f"다음을 확인해주세요:\n"
                f"1. 데이터셋 RID가 올바른지 확인\n"
                f"2. 토큰에 데이터셋 읽기 권한이 있는지 확인\n"
                f"3. hostname이 올바른지 확인 ({hostname})\n"
                f"4. Foundry 웹 UI에서 브랜치명 확인\n"
                f"5. 네트워크/VPN 연결 확인\n\n"
                f"대안: MANUAL_DOWNLOAD.md를 참조하여 웹 UI에서 직접 다운로드하세요."
            )

        print(f"\n✅ 성공한 엔드포인트: {successful_url}")
        if successful_branch != "N/A":
            print(f"✅ 사용된 브랜치: {successful_branch}")
            branch = successful_branch  # 성공한 브랜치로 업데이트

        files_data = files_response.json()

        # 응답 구조 디버깅
        print("\n응답 구조 확인:")
        print(
            f"응답 키: {list(files_data.keys()) if isinstance(files_data, dict) else 'Not a dict'}"
        )

        # 다양한 응답 구조 처리
        files = []
        if isinstance(files_data, dict):
            if "files" in files_data:
                files = files_data["files"]
            elif "data" in files_data:
                files = files_data["data"]
            elif "values" in files_data:
                files = files_data["values"]
        elif isinstance(files_data, list):
            files = files_data

        if not files:
            print(f"응답 내용 샘플: {str(files_data)[:500]}")
            raise ValueError(
                "데이터셋에 파일이 없거나 응답 구조를 파싱할 수 없습니다.\n"
                "위의 응답 구조를 확인해주세요."
            )

        # 로그 파일 제외 (실제 데이터 파일만)
        data_files = [f for f in files if not f.get("path", "").startswith("_/")]
        print(
            f"✓ 파일 목록 조회 완료: {len(files)}개 파일 (데이터 파일: {len(data_files)}개)\n"
        )

        if not data_files:
            print("경고: 데이터 파일이 없습니다. 모든 파일로 시도합니다.")
            data_files = files

        # 파일 정보 출력
        for i, file_info in enumerate(data_files[:10], 1):
            file_path = file_info.get("path", "")
            file_size = file_info.get("sizeInBytes", 0)
            print(f"  {i}. {file_path} ({file_size:,} bytes)")

        if len(data_files) > 10:
            print(f"  ... 외 {len(data_files) - 10}개 파일")

        # 2. 파일 다운로드
        from io import BytesIO

        all_dataframes = []

        for idx, file_info in enumerate(data_files[:20]):  # 최대 20개 파일 처리
            file_path = file_info.get("path")
            if not file_path:
                continue

            print(
                f"\n파일 다운로드 중 ({idx + 1}/{min(len(data_files), 20)}): {file_path}"
            )

            # 여러 다운로드 URL 패턴 시도
            from urllib.parse import quote

            encoded_path = quote(file_path, safe="")

            download_patterns = [
                f"/api/v1/datasets/{dataset_rid}/files/{encoded_path}",
                f"/api/v1/datasets/{dataset_rid}/files/{file_path}",
                f"/foundry-api/api/datasets/{dataset_rid}/files/{file_path}/download",
                f"/foundry-api/api/datasets/{dataset_rid}/branches/{branch}/files/{file_path}/download",
                f"/catalog-api/datasets/{dataset_rid}/files/{file_path}",
            ]

            file_response = None
            for download_pattern in download_patterns:
                download_url = f"https://{hostname}{download_pattern}"

                try:
                    response = requests.get(download_url, headers=headers, timeout=180)

                    if response.status_code == 200:
                        file_response = response
                        print("  ✅ 다운로드 성공")
                        break

                except Exception:
                    continue

            if not file_response or file_response.status_code != 200:
                print("  ✗ 모든 다운로드 URL 실패")
                continue

            # 파일 크기 확인
            file_size = len(file_response.content)
            print(f"  다운로드 완료: {file_size:,} bytes")

            # Content-Type 확인
            content_type = file_response.headers.get("Content-Type", "unknown")

            # JSON 응답인 경우 메타데이터일 수 있음
            if "json" in content_type.lower() or file_size < 1000:
                try:
                    metadata = json.loads(file_response.content)
                    if isinstance(metadata, dict) and "sizeBytes" in metadata:
                        print(
                            f"  ℹ️  메타데이터 응답 감지 (실제 크기: {metadata.get('sizeBytes')} bytes)"
                        )
                        print("  ⚠️  실제 파일 다운로드 엔드포인트를 찾을 수 없습니다")

                        # transactionRid를 사용한 다운로드 시도
                        transaction_rid = metadata.get("transactionRid")
                        if transaction_rid:
                            print("  🔄 transactionRid를 사용하여 재시도...")
                            # 추가 시도할 수 있는 다른 패턴들
                            continue
                except:
                    pass

            # 파일 형식에 따라 파싱
            try:
                # Parquet 파일 시도
                if file_path.endswith(".parquet") or file_path.endswith(
                    ".snappy.parquet"
                ):
                    df_chunk = pd.read_parquet(BytesIO(file_response.content))
                    all_dataframes.append(df_chunk)
                    print(
                        f"  ✓ Parquet 파싱 성공: {len(df_chunk):,} 행, {len(df_chunk.columns)} 열"
                    )
                # CSV 파일 시도
                elif file_path.endswith(".csv"):
                    df_chunk = pd.read_csv(BytesIO(file_response.content))
                    all_dataframes.append(df_chunk)
                    print(
                        f"  ✓ CSV 파싱 성공: {len(df_chunk):,} 행, {len(df_chunk.columns)} 열"
                    )
                else:
                    # 확장자 없는 경우 parquet 먼저 시도
                    try:
                        df_chunk = pd.read_parquet(BytesIO(file_response.content))
                        all_dataframes.append(df_chunk)
                        print(
                            f"  ✓ Parquet 파싱 성공: {len(df_chunk):,} 행, {len(df_chunk.columns)} 열"
                        )
                    except Exception:
                        # CSV로 재시도
                        df_chunk = pd.read_csv(BytesIO(file_response.content))
                        all_dataframes.append(df_chunk)
                        print(
                            f"  ✓ CSV 파싱 성공: {len(df_chunk):,} 행, {len(df_chunk.columns)} 열"
                        )

            except Exception as e:
                print(f"  ✗ 파일 파싱 실패: {str(e)}")
                continue

        if not all_dataframes:
            raise ValueError("다운로드 가능한 데이터가 없습니다.")

        # 모든 데이터프레임 병합
        if len(all_dataframes) == 1:
            df = all_dataframes[0]
        else:
            print(f"\n{len(all_dataframes)}개 파일 병합 중...")
            df = pd.concat(all_dataframes, ignore_index=True)

        print(f"\n✅ 다운로드 완료: {len(df):,} 행, {len(df.columns)} 열")
        print(f"컬럼: {list(df.columns)}")

        # 출력 경로 설정
        if output_path is None:
            dataset_name = dataset_rid.split(".")[-1]
            output_path = f"{dataset_name}.{output_format}"

        # 데이터 저장
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_format == "csv":
            df.to_csv(output_path, index=False, encoding="utf-8-sig")
        elif output_format == "parquet":
            df.to_parquet(output_path, index=False)
        elif output_format == "json":
            df.to_json(output_path, orient="records", force_ascii=False, indent=2)
        else:
            raise ValueError(f"지원하지 않는 형식: {output_format}")

        print(f"저장 완료: {output_path.absolute()}\n")
        return df

    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        raise


def main():
    """메인 함수"""
    # 다운로드할 데이터셋 RID
    DATASET_RID = "ri.foundry.main.dataset.a60255aa-23e1-41ce-a0f0-448337578971"

    # 저장할 경로 (현재 디렉토리 기준)
    output_dir = Path(__file__).parent / "data"
    output_file = output_dir / "downloaded_dataset.csv"

    try:
        df = download_dataset(
            dataset_rid=DATASET_RID,
            output_path=str(output_file),
            output_format="csv",
        )

        # 데이터 미리보기
        print("=== 데이터 미리보기 ===")
        print(df.head(10))
        print(f"\n데이터 형태: {df.shape}")
        print(f"\n데이터 타입:\n{df.dtypes}")

    except Exception as e:
        print(f"\n다운로드 실패: {str(e)}")
        print("\n설정 확인사항:")
        print("1. FOUNDRY_TOKEN 환경변수가 설정되어 있는지 확인")
        print("2. FOUNDRY_HOSTNAME 환경변수가 올바른지 확인")
        print("3. 데이터셋 RID가 올바른지 확인")
        print("4. 데이터셋에 대한 읽기 권한이 있는지 확인")


if __name__ == "__main__":
    main()
