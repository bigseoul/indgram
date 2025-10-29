#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DART 회사 개요 수집 배치 (PRD 기반 v2)
"""

import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import dart_fss as dart
from dart_fss.corp import Corp

# ============================================================
# 설정
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "fsdata")

API_KEY = "82f7e55fddad2d097811929b56b5eaf6716825a3"
CORP_LIST_FILE = os.path.join(OUTPUT_DIR, "corp_list.csv")  # 입력
STREAMING_CSV = os.path.join(OUTPUT_DIR, "dart_corp_list_streaming.csv")  # 출력
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "dart_corp_list.progress.json")  # 진행상태

SAMPLE_SIZE = 100  # 0 = 전체, N = 샘플 N개
MAX_RETRIES = 3  # 재시도 횟수
RETRY_DELAY = 2  # 재시도 간격(초)

# PRD 요구 필드 (18개)
REQUIRED_FIELDS = [
    'corp_code', 'corp_name', 'corp_name_eng', 'stock_code',
    'modify_date', 'stock_name', 'ceo_nm', 'corp_cls',
    'jurir_no', 'bizr_no', 'adres', 'hm_url', 'ir_url',
    'phn_no', 'fax_no', 'induty_code', 'est_dt', 'acc_mt'
]

# ============================================================
# 유틸리티 함수
# ============================================================

def load_progress():
    """진행 상태 불러오기"""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        "completed": [],
        "failed": [],
        "start_time": datetime.now().isoformat(),
        "last_updated": None
    }


def save_progress(progress):
    """진행 상태 저장"""
    progress["last_updated"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def load_csv_completed_codes():
    """CSV에 이미 저장된 corp_code 목록"""
    if not os.path.exists(STREAMING_CSV):
        return set()
    
    try:
        # corp_code를 문자열로 읽기 (앞의 0 유지)
        df = pd.read_csv(STREAMING_CSV, encoding='utf-8-sig', dtype={'corp_code': str})
        if 'corp_code' in df.columns:
            # 8자리로 패딩 (혹시 모를 불일치 방지)
            return set(df['corp_code'].astype(str).str.zfill(8).values)
    except:
        pass
    return set()


def append_to_csv(corp_dict, is_first=False):
    """CSV에 한 줄씩 append (Streaming 저장)"""
    try:
        # PRD 요구 필드만 추출
        filtered = {k: corp_dict.get(k, '') for k in REQUIRED_FIELDS}
        
        # corp_code를 문자열로 명시적 변환 (앞의 0 유지)
        if 'corp_code' in filtered:
            filtered['corp_code'] = str(filtered['corp_code']).zfill(8)
        
        df = pd.DataFrame([filtered])
        
        mode = 'w' if is_first else 'a'
        header = is_first
        df.to_csv(STREAMING_CSV, mode=mode, header=header, index=False, 
                  encoding='utf-8-sig')
        return True
    except Exception as e:
        print(f"[ERROR] CSV 저장 실패: {str(e)[:50]}")
        return False


# ============================================================
# 메인 로직
# ============================================================

def main():
    print("=" * 80)
    print("DART 회사 개요 수집 배치 (PRD v2)")
    print("=" * 80)
    
    # 1. 초기화
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    dart.set_api_key(api_key=API_KEY)
    
    # 2. 입력 파일 읽기 (CSV - API 호출 없음)
    print("\n[1/4] 회사 목록 읽기...")
    if not os.path.exists(CORP_LIST_FILE):
        print(f"[ERROR] 파일 없음: {CORP_LIST_FILE}")
        return 1
    
    corp_codes = []
    with open(CORP_LIST_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            corp_codes.append(row['corp_code'])
    
    print(f"[OK] 총 {len(corp_codes):,}개 회사 (CSV 기반)")
    
    # 3. 이미 처리된 항목 제외
    print("\n[2/4] 진행 상태 확인...")
    progress = load_progress()
    csv_completed = load_csv_completed_codes()
    json_completed = set(progress["completed"])
    
    # CSV + JSON 모두 기반으로 스킵
    all_completed = csv_completed | json_completed
    
    remaining = [code for code in corp_codes if code not in all_completed]
    
    print(f"[OK] 이미 완료: {len(all_completed):,}개")
    print(f"[OK] 남은 작업: {len(remaining):,}개")
    
    # 샘플 모드
    if SAMPLE_SIZE > 0:
        remaining = remaining[:SAMPLE_SIZE]
        print(f"[SAMPLE MODE] {SAMPLE_SIZE}개만 처리")
    
    if len(remaining) == 0:
        print("\n✅ 모든 작업 완료!")
        return 0
    
    # 4. 회사 개요 수집
    print(f"\n[3/4] 회사 개요 수집 중... (총 {len(remaining):,}개)")
    print(f"[INFO] corp_list는 CSV 사용, 각 회사 상세 정보만 API 호출")
    
    success = 0
    fail = 0
    is_first = len(all_completed) == 0  # CSV가 비어있으면 헤더 생성
    
    start_time = time.time()
    
    for idx, corp_code in enumerate(remaining, 1):
        try:
            # Corp 객체 직접 생성 (get_corp_list() 사용 안 함)
            corp = Corp(corp_code=corp_code)
            
            # load() 호출하여 상세 정보 가져오기 (재시도 포함)
            load_success = False
            last_error = None
            
            for attempt in range(MAX_RETRIES):
                try:
                    corp.load()
                    load_success = True
                    break
                except Exception as e:
                    last_error = e
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
            
            if not load_success:
                raise Exception(f"load() 실패 (재시도 {MAX_RETRIES}회): {last_error}")
            
            # to_dict() 호출
            corp_dict = corp.to_dict()
            
            # Streaming CSV에 즉시 저장
            if append_to_csv(corp_dict, is_first=is_first):
                progress["completed"].append(corp_code)
                success += 1
                is_first = False
            else:
                # CSV 저장 실패 시 즉시 중단 (PRD 요구사항)
                print(f"\n[CRITICAL] CSV 저장 실패 - 중단")
                save_progress(progress)
                return 1
            
            # 진행률 표시
            if idx % 100 == 0 or idx == len(remaining):
                elapsed = time.time() - start_time
                avg_time = elapsed / idx
                eta = avg_time * (len(remaining) - idx)
                
                print(f"\r진행: {idx:,}/{len(remaining):,} "
                      f"({idx/len(remaining)*100:.1f}%) | "
                      f"성공: {success:,} | 실패: {fail:,} | "
                      f"예상 남은 시간: {eta/60:.1f}분", 
                      end='', flush=True)
                
                # 주기적으로 progress 저장
                if idx % 500 == 0:
                    save_progress(progress)
        
        except Exception as e:
            print(f"\n[ERROR] {corp_code} - {str(e)[:80]}")
            progress["failed"].append(corp_code)
            fail += 1
            
            # 실패 시 즉시 중단 (PRD 요구사항)
            print(f"[STOP] 오류 발생으로 중단. 재실행 시 이어서 진행됩니다.")
            save_progress(progress)
            return 1
    
    print()  # 줄바꿈
    
    # 5. 최종 저장 및 요약
    print("\n[4/4] 작업 완료")
    save_progress(progress)
    
    total_time = time.time() - start_time
    
    print(f"\n{'=' * 80}")
    print("결과 요약")
    print(f"{'=' * 80}")
    print(f"성공: {success:,}개")
    print(f"실패: {fail:,}개")
    print(f"소요 시간: {total_time/60:.1f}분")
    print(f"평균 처리 속도: {total_time/success:.3f}초/건" if success > 0 else "")
    print(f"\n출력 파일: {STREAMING_CSV}")
    print(f"진행 상태: {PROGRESS_FILE}")
    
    # 전체 완료 시 progress 파일 삭제
    if fail == 0 and len(remaining) == len(corp_codes):
        os.remove(PROGRESS_FILE) if os.path.exists(PROGRESS_FILE) else None
        print("\n✅ 전체 작업 완료!")
    
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[중단] 사용자가 중단했습니다.")
        print("재실행 시 중단된 지점부터 이어서 진행됩니다.")
        sys.exit(1)

