#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fetching Company Overview Information (Full Data)
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Fix yaspin Unicode encoding issue on Windows
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

# Disable fancy spinner characters for Windows console (cp949 compatibility)
os.environ["YASPIN_DISABLE_UNIREST"] = "1"
os.environ["TERM"] = "dumb"  # Force simple output mode

import pandas as pd
import requests

# Patch yaspin to use safe characters on Windows
try:
    import sys
    from io import StringIO

    # Redirect stderr during yaspin initialization to suppress spinner errors
    old_stderr = sys.stderr
    sys.stderr = StringIO()

    # Monkey-patch yaspin's stream write to handle encoding errors
    from yaspin import core

    original_write = (
        core.Spinner._stream.write if hasattr(core.Spinner, "_stream") else None
    )

    def safe_write(text):
        """Safe write that handles encoding errors"""
        try:
            sys.stdout.write(text)
        except UnicodeEncodeError:
            # Fallback to safe ASCII characters
            safe_text = text.encode("ascii", "replace").decode("ascii")
            sys.stdout.write(safe_text)

    # Restore stderr
    sys.stderr = old_stderr
except Exception:
    pass  # If patching fails, continue anyway

import dart_fss as dart

# Get script directory (absolute path)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Settings
API_KEY = "82f7e55fddad2d097811929b56b5eaf6716825a3"
MAX_RETRIES = 5  # Increased from 3 to 5
RETRY_DELAY = 2  # Increased from 1 to 2 seconds
API_REQUEST_INTERVAL = 0.5  # Added request interval delay
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "fsdata")  # 절대 경로로 수정
STREAMING_CSV = os.path.join(
    OUTPUT_DIR, "dart_corp_list_streaming.csv"
)  # For real-time saving
PROGRESS_SAVE_INTERVAL = 100  # Changed from 500 to 100 for better accuracy
PROGRESS_FILE = os.path.join(
    SCRIPT_DIR, "dart_corp_list_full.progress.json"
)  # 절대 경로
SAMPLE_SIZE = 5  # 0 = Full collection, N = Sample N companies (for testing)
MAX_QUERY_LIMIT = 29000  # API daily limit (safeguard: up to 29,000)
CONTINUE_ON_FAILURE = True  # Changed from STOP_ON_FAILURE to CONTINUE_ON_FAILURE
MAX_CONSECUTIVE_FAILURES = 10  # Stop only after 10 consecutive failures


def setup_output_dir():
    """Create output directory"""
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def load_progress():
    """Load progress status"""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass

    # Initialize with timing information
    return {
        "completed": [],
        "total": 0,
        "errors": [],
        "start_time": datetime.now().isoformat(),
        "last_updated": None,
    }


def save_progress(progress):
    """Save progress status with timestamp"""
    progress["last_updated"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def load_corp_info_with_retry(corp, max_retries=MAX_RETRIES, progress=None):
    """Load company information with retry logic"""
    corp_code = corp.corp_code
    corp_name = corp.corp_name

    for attempt in range(max_retries):
        try:
            corp.load()
            time.sleep(API_REQUEST_INTERVAL)  # Delay after request
            return True
        except requests.Timeout:
            error_msg = f"Timeout (Attempt: {attempt + 1}/{max_retries})"
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY * 2)  # Longer wait for timeout
            else:
                log_error(corp_code, corp_name, "TIMEOUT", error_msg, progress)
                return False
        except requests.ConnectionError:
            error_msg = f"Connection Error (Attempt: {attempt + 1}/{max_retries})"
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY * 3)  # Much longer wait for connection error
            else:
                log_error(corp_code, corp_name, "CONNECTION_ERROR", error_msg, progress)
                return False
        except Exception as e:
            error_msg = str(e)[:100]
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
            else:
                log_error(corp_code, corp_name, type(e).__name__, error_msg, progress)
                return False
    return False


def format_time(seconds):
    """Convert seconds to a readable format"""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"


def log_error(corp_code, corp_name, error_type, error_msg, progress=None):
    """Log errors and save to progress file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    error_log = {
        "timestamp": timestamp,
        "corp_code": corp_code,
        "corp_name": corp_name,
        "error_type": error_type,
        "error_msg": error_msg,
    }

    print(f"  [ERROR] {corp_code} | {error_type} | {error_msg[:50]}")

    # Save to progress file
    if progress is not None:
        if "errors" not in progress:
            progress["errors"] = []
        progress["errors"].append(error_log)


def check_api_health():
    """Check API server status"""
    try:
        response = requests.get("https://dart.fss.or.kr/api/", timeout=5)
        return response.status_code == 200
    except requests.Timeout:
        return False
    except requests.ConnectionError:
        return False
    except Exception:
        return False


def load_existing_csv_codes():
    """Load already saved company codes from CSV"""
    if not os.path.exists(STREAMING_CSV):
        return set()

    try:
        df = pd.read_csv(STREAMING_CSV, encoding="utf-8-sig", encoding_errors="ignore")
        if "corp_code" in df.columns:
            return set(df["corp_code"].astype(str).values)
        return set()
    except Exception as e:
        print(f"[WARN] Could not load existing CSV: {str(e)[:50]}")
        return set()


def save_to_streaming_csv(corp_dict, is_first=False):
    """Save data to CSV in real-time"""
    try:
        df = pd.DataFrame([corp_dict])
        mode = "w" if is_first else "a"
        header = is_first
        df.to_csv(
            STREAMING_CSV, mode=mode, header=header, index=False, encoding="utf-8-sig"
        )
        return True
    except Exception as e:
        print(f"  CSV saving failed: {str(e)[:50]}")
        return False


def print_progress(i, total, success, fail, elapsed, eta):
    """Print progress status in one line (overwrite effect)"""
    progress_pct = (i / total) * 100
    bar_length = 30
    filled = int(bar_length * i / total)
    bar = "=" * filled + "-" * (bar_length - filled)

    status = f"[{bar}] {i:,}/{total:,} ({progress_pct:.1f}%) | Success: {success:,} | Failed: {fail:,} | ETA: {eta}"
    sys.stdout.write(f"\r{status:<130}")
    sys.stdout.flush()


def main():
    """Main function"""
    print("=" * 130)
    print("Fetching Company Overview Information (Full Data)")
    print("=" * 130)

    # Initialize
    setup_output_dir()

    # Reset dart_fss singleton to clear any cached issues
    try:
        from dart_fss.auth.auth import DartAuth
        from dart_fss.utils.singleton import Singleton

        if DartAuth in Singleton._instances:
            del Singleton._instances[DartAuth]
    except:
        pass

    dart.set_api_key(api_key=API_KEY)
    progress = load_progress()

    start_time = time.time()

    try:
        # Load company list
        print("\n[1/3] Loading company list...", flush=True)
        corp_list = dart.get_corp_list()
        corps = list(corp_list.corps)  # All companies

        # Load existing CSV data
        print("[INFO] Checking existing CSV data...", flush=True)
        csv_saved_codes = load_existing_csv_codes()
        print(f"[OK] Already in CSV: {len(csv_saved_codes):,} companies")

        # Filter out already saved companies
        corps_to_process = [c for c in corps if c.corp_code not in csv_saved_codes]

        # Sample mode: process only specified number from remaining
        if SAMPLE_SIZE > 0:
            corps_to_process = corps_to_process[:SAMPLE_SIZE]
            print(f"[SAMPLE MODE] Processing {SAMPLE_SIZE} NEW companies only.")

        total_corps = len(corps_to_process)
        already_done = len(csv_saved_codes)
        remaining = total_corps

        print(f"[OK] Total to process: {total_corps:,}")
        print(f"[OK] Already in CSV: {already_done:,}")
        print(f"[OK] Will fetch: {remaining:,}\n")

        # Collect data
        print("[2/3] Fetching company overview information...", flush=True)
        corp_data = []
        success_count = 0
        fail_count = 0
        consecutive_failures = 0
        consecutive_api_failures = 0
        last_api_call_time = time.time()

        query_start = time.time()
        last_progress_save = time.time()
        last_output = time.time()

        # Determine if CSV is empty (need header)
        csv_is_empty = len(csv_saved_codes) == 0

        for i, corp in enumerate(corps_to_process, 1):
            corp_code = corp.corp_code
            corp_name = corp.corp_name

            # API call limit check
            if len(progress["completed"]) >= MAX_QUERY_LIMIT:
                print(
                    f"\n[LIMIT] API limit reached: {len(progress['completed']):,}/{MAX_QUERY_LIMIT:,}"
                )
                break

            # Load company overview information (ALL companies need API call)
            if load_corp_info_with_retry(corp, progress=progress):
                corp_dict = corp.to_dict()
                corp_data.append(corp_dict)
                progress["completed"].append(corp_code)
                success_count += 1
                consecutive_failures = 0

                # Save directly to CSV (prevent data loss)
                is_first = csv_is_empty and success_count == 1
                save_to_streaming_csv(corp_dict, is_first=is_first)

                # Update last API call time
                last_api_call_time = time.time()
                progress["last_updated"] = datetime.now().isoformat()

                # 100 items, 1 second break
                if success_count % 100 == 0:
                    time.sleep(1)
            else:
                fail_count += 1
                consecutive_failures += 1

                # Check consecutive failures threshold
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    print(
                        f"\n[STOP] Too many consecutive failures: {consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}"
                    )
                    print("[INFO] Saving progress...")
                    progress["total"] = total_corps
                    save_progress(progress)
                    print(f"[INFO] {len(progress['completed']):,} company info saved")
                    print("[STOP] Stopping due to excessive failures")
                    break

            # Periodic progress saving
            if len(progress["completed"]) % PROGRESS_SAVE_INTERVAL == 0:
                if time.time() - last_progress_save > 60:
                    progress["total"] = total_corps
                    save_progress(progress)
                    last_progress_save = time.time()

                    # Check API server status
                    if not check_api_health():
                        print(
                            "\n[WARNING] API server not responding. Checking status..."
                        )
                        time.sleep(5)
                        if not check_api_health():
                            print(
                                "[WARNING] API still unresponsive. Continuing with caution..."
                            )
                            consecutive_api_failures += 1
                            if consecutive_api_failures >= 3:
                                print(
                                    f"[ALERT] Multiple API failures detected: {consecutive_api_failures}"
                                )
                    else:
                        consecutive_api_failures = 0

            # Print progress (every 0.5 seconds)
            if time.time() - last_output > 0.5 or i % 100 == 0 or i == total_corps:
                elapsed = time.time() - query_start
                avg_time = (
                    elapsed / (success_count + fail_count)
                    if (success_count + fail_count) > 0
                    else 0
                )
                eta_remaining = (total_corps - i) * avg_time if avg_time > 0 else 0
                eta_str = format_time(eta_remaining)
                print_progress(
                    i, total_corps, success_count, fail_count, elapsed, eta_str
                )
                last_output = time.time()

        query_elapsed = time.time() - query_start
        print()  # New line

        # Final progress saving
        progress["total"] = total_corps
        save_progress(progress)

        # Result summary
        print(f"\n{'=' * 130}")
        print("Result Summary")
        print(f"{'=' * 130}")
        print(f"Success: {success_count:,}")
        print(f"Failed: {fail_count:,}")
        print(f"Total: {len(corp_data):,}")
        print(f"Query time: {format_time(query_elapsed)}")
        if (success_count + fail_count) > 0:
            print(
                f"Average query time: {(query_elapsed / (success_count + fail_count)):.3f} seconds/company"
            )

        # Error summary (new)
        if progress.get("errors"):
            print("\n[Error Summary]")
            error_types = {}
            for error in progress["errors"]:
                error_type = error.get("error_type", "Unknown")
                error_types[error_type] = error_types.get(error_type, 0) + 1

            for error_type, count in sorted(
                error_types.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  - {error_type}: {count}개")

        # Create DataFrame
        print("\n[3/3] Cleaning and saving data...", flush=True)
        if corp_data:
            # Load from streaming CSV (memory saving)
            print("Loading data from streaming CSV...", end=" ", flush=True)
            try:
                df = pd.read_csv(STREAMING_CSV, encoding="utf-8-sig")
                print("[OK]")
            except Exception as e:
                print(f"[FAILED] {str(e)[:50]}")
                print("Proceeding with data in memory...")
                df = pd.DataFrame(corp_data)

            print(f"[OK] Number of fields: {len(df.columns)}")
            print(f"[OK] Number of rows: {len(df):,}")

            # Field information
            print("\nIncluded fields:")
            for i, col in enumerate(sorted(df.columns), 1):
                marker = "[CEO]" if col == "ceo_nm" else "     "
                print(f"  {marker} {i:2}. {col}")

            # Save to Excel
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"dart_corp_list_full_{timestamp}.xlsx"
            output_path = os.path.join(OUTPUT_DIR, output_file)
            print(f"\nSaving Excel file: {output_file}...", end=" ", flush=True)

            # Convert numbers to text (prevent scientific notation)
            df_export = df.copy()
            for col in df_export.columns:
                if df_export[col].dtype in ["int64", "float64"]:
                    df_export[col] = df_export[col].astype(str)

            df_export.to_excel(output_path, index=False, sheet_name="Companies")
            print("[OK]")
            print(f"Saved: {output_path}")

            # Streaming CSV info
            print(f"\nStreaming CSV saved: {STREAMING_CSV}")
            print("  - Keeps real-time data (data persists even if stopped)")
            print(f"  - Final Excel: {output_path}")

            # Preview data
            print("\nData preview (first 5 rows):")
            print(df[["corp_code", "corp_name", "ceo_nm"]].head().to_string())

            # Clean up progress file on completion
            if fail_count == 0:
                os.remove(PROGRESS_FILE) if os.path.exists(PROGRESS_FILE) else None
                print("\n[COMPLETED] All data processing completed!")

        total_elapsed = time.time() - start_time
        print(f"\nTotal execution time: {format_time(total_elapsed)}")
        print("=" * 130)

        return 0

    except KeyboardInterrupt:
        print("\n\nUser interrupted")
        print(f"Progress so far: {len(progress['completed']):,}")
        save_progress(progress)
        return 1

    except Exception as e:
        print(f"\n\nError occurred: {str(e)}")
        import traceback

        traceback.print_exc()
        save_progress(progress)
        return 1


if __name__ == "__main__":
    sys.exit(main())


def export_collected_data():
    """Export collected data to a file"""
    print("\n" + "=" * 130)
    print("Exporting collected data")
    print("=" * 130)

    # Load progress file
    if not os.path.exists(PROGRESS_FILE):
        print("❌ Progress file not found. Please collect data first.")
        return 1

    progress = load_progress()
    completed_codes = progress["completed"]
    total_completed = len(completed_codes)

    if total_completed == 0:
        print("❌ No data collected yet.")
        return 1

    print(f"\n[1/3] Company information: {total_completed:,}")

    # Check streaming CSV
    if not os.path.exists(STREAMING_CSV):
        print(f"❌ Streaming CSV file not found: {STREAMING_CSV}")
        return 1

    print(f"[OK] Streaming CSV file found: {STREAMING_CSV}")

    # Load CSV into DataFrame
    print("\n[2/3] Loading data...", end=" ", flush=True)
    try:
        df = pd.read_csv(STREAMING_CSV, encoding="utf-8-sig")
        print(f"[OK] {len(df):,} rows loaded")
    except Exception as e:
        print(f"[FAILED] {str(e)}")
        return 1

    # Output data information
    print("\n[3/3] Final file generation...", end=" ", flush=True)
    print(f"   Number of fields: {len(df.columns)}")
    print(f"   Number of rows: {len(df):,}")

    # Field list
    print(f"\nIncluded fields ({len(df.columns)} fields):")
    for i, col in enumerate(sorted(df.columns), 1):
        marker = "[CEO]" if col == "ceo_nm" else "     "
        print(f"  {marker} {i:2}. {col}")

    # Save to Excel file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_file = f"dart_corp_list_full_{timestamp}.xlsx"
    excel_path = os.path.join(OUTPUT_DIR, excel_file)

    print(f"\nSaving Excel file: {excel_file}...", end=" ", flush=True)
    try:
        df.to_excel(excel_path, index=False, sheet_name="Companies")
        print("[OK]")
        print(f"   Saved location: {excel_path}")
    except Exception as e:
        print(f"[FAILED] {str(e)}")
        return 1

    # Preview data
    print("\nData preview (first 5 rows):")
    print(
        df[["corp_code", "corp_name", "ceo_nm"]].head().to_string()
        if "ceo_nm" in df.columns
        else df.head().to_string()
    )

    # Data statistics
    print("\nData statistics:")
    print(f"   Total rows: {len(df):,}")
    print(f"   Total columns: {len(df.columns)}")

    if "ceo_nm" in df.columns:
        ceo_count = df["ceo_nm"].notna().sum()
        print(f"  CEO name available: {ceo_count:,} ({ceo_count / len(df) * 100:.1f}%)")

    print("\n✅ Saved!")
    print(f"  Excel: {excel_path}")
    print(f"  CSV (streaming): {STREAMING_CSV}")

    return 0
