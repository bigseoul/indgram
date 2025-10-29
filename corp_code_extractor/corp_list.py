#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DART 회사 리스트 수집 및 파일 저장
"""

import json
import os
import csv
from pathlib import Path

import dart_fss as dart

# 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "fsdata")
API_KEY = "82f7e55fddad2d097811929b56b5eaf6716825a3"

# 출력 파일 경로
JSON_FILE = os.path.join(OUTPUT_DIR, "corp_list.json")
CSV_FILE = os.path.join(OUTPUT_DIR, "corp_list.csv")


def setup_output_dir():
    """출력 디렉토리 생성"""
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def save_to_json(corp_list):
    """회사 리스트를 JSON 파일로 저장"""
    corp_data = []
    for corp in corp_list.corps:
        corp_data.append({
            "corp_code": corp.corp_code,
            "corp_name": corp.corp_name,
            "stock_code": corp.stock_code,
            "modify_date": corp.modify_date
        })
    
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(corp_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ JSON 저장 완료: {JSON_FILE}")
    print(f"  총 {len(corp_data):,}개 회사")


def save_to_csv(corp_list):
    """회사 리스트를 CSV 파일로 저장"""
    with open(CSV_FILE, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        # 헤더 작성
        writer.writerow(["corp_code", "corp_name", "stock_code", "modify_date"])
        
        # 데이터 작성
        count = 0
        for corp in corp_list.corps:
            writer.writerow([
                corp.corp_code,
                corp.corp_name,
                corp.stock_code,
                corp.modify_date
            ])
            count += 1
    
    print(f"✓ CSV 저장 완료: {CSV_FILE}")
    print(f"  총 {count:,}개 회사")


def main():
    """메인 함수"""
    print("=" * 60)
    print("DART 회사 리스트 수집 및 파일 저장")
    print("=" * 60)
    
    # 출력 디렉토리 생성
    setup_output_dir()
    
    # API 키 설정
    dart.set_api_key(api_key=API_KEY)
    
    # 회사 리스트 조회
    print("\n[1/3] 회사 리스트 조회 중...", flush=True)
    corp_list = dart.get_corp_list()
    print(f"[OK] 조회 완료: {len(list(corp_list.corps)):,}개 회사")
    
    # JSON 저장
    print("\n[2/3] JSON 파일로 저장 중...", flush=True)
    save_to_json(corp_list)
    
    # CSV 저장
    print("\n[3/3] CSV 파일로 저장 중...", flush=True)
    save_to_csv(corp_list)
    
    print("\n" + "=" * 60)
    print("✓ 모든 작업 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()