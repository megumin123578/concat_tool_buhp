import os
import sys
import csv
import subprocess
from datetime import datetime
import pandas as pd

OUTPUT_FILE = r"C:\Users\Admin\Documents\concatenate videos\ref\beca_data.csv"
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov'}

def log(msg: str):
    print(msg, flush=True)

def get_file_list(folder_path):
    try:
        file_list = []
        for root, _, files in os.walk(folder_path):
            if 'quay' in os.path.basename(root).lower():
                continue
            for item in files:
                if os.path.splitext(item)[1].lower() in VIDEO_EXTENSIONS:
                    file_list.append(os.path.abspath(os.path.join(root, item)))
        return file_list
    except Exception as e:
        log(f"Lỗi quét folder: {e}")
        return []

def ffprobe_duration_seconds(file_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60
        )
        return float(result.stdout.decode(errors="ignore").strip())
    except:
        return None

def format_mmss(seconds):
    s = int(seconds)
    return f"{s//60}:{s%60:02d}"

def get_creation_age_seconds(file_path):
    try:
        return int(datetime.now().timestamp() - os.path.getmtime(file_path))
    except:
        return None

def read_existing_csv(path):
    cols = ['stt', 'file_path', 'duration', 'lastest_used_value']
    if not os.path.exists(path):
        return pd.DataFrame(columns=cols)
    try:
        df = pd.read_csv(path, encoding='utf-8-sig')
        for c in cols:
            if c not in df.columns:
                df[c] = pd.NA
        return df[cols]
    except:
        return pd.DataFrame(columns=cols)

def write_csv(path, df):
    df.to_csv(path, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_MINIMAL)

def build_rows(folder):
    files = sorted(get_file_list(folder), key=lambda p: os.path.basename(p).lower())
    rows = []
    for fp in files:
        dur = ffprobe_duration_seconds(fp)
        if not dur or dur < 60:
            continue
        rows.append({
            'stt': None,
            'file_path': fp,
            'duration': format_mmss(dur),
            'lastest_used_value': get_creation_age_seconds(fp) or ""
        })
    return rows

def sync(folder):
    df_cur = read_existing_csv(OUTPUT_FILE)
    desired = build_rows(folder)
    desired_paths = {r['file_path'] for r in desired}
    cur_paths = set(df_cur['file_path'].dropna().tolist())

    to_add = desired_paths - cur_paths
    to_remove = cur_paths - desired_paths

    final = {r['file_path']: r for r in desired}

    rows = list(final.values())
    rows.sort(key=lambda r: os.path.basename(r['file_path']).lower())
    for i, r in enumerate(rows, 1):
        r['stt'] = i
    df_final = pd.DataFrame(rows, columns=['stt', 'file_path', 'duration', 'lastest_used_value'])
    write_csv(OUTPUT_FILE, df_final)

    log(f"Tổng: {len(rows)}, Thêm: {len(to_add)}, Xóa: {len(to_remove)}")
    if to_add: log(" + " + "\n + ".join(to_add))
    if to_remove: log(" - " + "\n - ".join(to_remove))

if __name__ == "__main__":
    folder = input("Nhập đường dẫn thư mục video: ").strip('"').strip("'")
    if not os.path.isdir(folder):
        log("Không phải thư mục hợp lệ.")
        sys.exit(1)
    sync(folder)
