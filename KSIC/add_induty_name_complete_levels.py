#!/usr/bin/env python3
"""
KSIC level_2,3,4,5.csv를 모두 사용하여 dart_corp_list.csv에 완전한 induty_name 컬럼을 추가하는 스크립트

사용법:
    python add_induty_name_complete_levels.py
"""

import csv


def main():
    # 모든 레벨 파일 로드하여 완전한 통합 매핑 생성
    complete_mapping = {}

    # 우선순위에 따라 로드: level_5 > level_4 > level_3 > level_2
    files_and_priorities = [
        ("level_5.csv", 5),
        ("level_4.csv", 4),
        ("level_3.csv", 3),
        ("level_2.csv", 2),
    ]

    for file_path, priority in files_and_priorities:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # 헤더 건너뛰기
            for row in reader:
                if len(row) >= 2:
                    code, name = row[0].strip(), row[1].strip()
                    if code and name and code not in complete_mapping:
                        complete_mapping[code] = name

    print(f"완전한 통합 매핑 로드 완료: {len(complete_mapping)}개")

    # dart_corp_list.csv 처리
    input_file = "dart_corp_list.csv"
    output_file = "dart_corp_list_complete_induty_name.csv"

    with (
        open(input_file, "r", encoding="utf-8") as infile,
        open(output_file, "w", encoding="utf-8", newline="") as outfile,
    ):
        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        # 헤더 처리
        header = next(reader)
        header.insert(16, "induty_name")
        writer.writerow(header)

        # 데이터 행 처리
        processed_count = 0
        matched_count = 0

        for row in reader:
            if len(row) >= 17:
                induty_code = row[15].strip()
                induty_name = complete_mapping.get(induty_code, "")

                row.insert(16, induty_name)
                writer.writerow(row)

                processed_count += 1
                if induty_name:
                    matched_count += 1

                if processed_count % 10000 == 0:
                    print(f"처리된 행: {processed_count}, 매칭된 행: {matched_count}")

    print(
        f"완료! 총 처리: {processed_count}, 매칭: {matched_count}, 매칭률: {matched_count / processed_count * 100:.1f}%"
    )


if __name__ == "__main__":
    main()
