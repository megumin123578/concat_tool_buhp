import os
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from moviepy import VideoFileClip
from datetime import datetime
import warnings




def check_and_add_next_spidey_video():
    """
    Tự động kiểm tra và thêm video Spidey tiếp theo vào CSV nếu tên file chứa số thứ tự và 'spidey'.
    """
    # Constants
    OUTPUT_FILE = 'data_spidey.csv'
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov'}
    BASE_PATH = r'\\nashp\DATABUHP\Nam SEO\.Spidey'

    # Lấy số thứ tự video cuối cùng từ CSV
    try:
        last_number = 0
        if os.path.exists(OUTPUT_FILE):
            df = pd.read_csv(OUTPUT_FILE, encoding='utf-8-sig')
            if not df.empty and 'stt' in df.columns:
                last_number = int(df['stt'].iloc[-1])  # Lấy số thứ tự từ cột 'stt'
            elif not df.empty and 'file_path' in df.columns:
                last_file = df['file_path'].iloc[-1]
                file_name = os.path.basename(last_file).lower()
                for part in file_name.split():
                    if part.isdigit():
                        last_number = int(part)
                        break
    except Exception as e:
        print(f"Error reading CSV file '{OUTPUT_FILE}': {e}")
        return

    # Tạo chuỗi số thứ tự tiếp theo
    next_number = last_number + 1
    next_number_str = f"{next_number:03d}"  # Định dạng: 050

    # Tìm video trong thư mục có chứa cả số thứ tự và 'spidey'
    next_video_path = None
    try:
        for root, _, files in os.walk(BASE_PATH):
            for item in files:
                if os.path.splitext(item)[1].lower() in VIDEO_EXTENSIONS:
                    item_lower = item.lower()
                    if next_number_str in item_lower and 'spidey' in item_lower:
                        next_video_path = os.path.abspath(os.path.join(root, item))
                        break
            if next_video_path:
                break
    except Exception as e:
        print(f"Error accessing folder '{BASE_PATH}': {e}")
        return

    if not next_video_path:
        print(f"Video containing '{next_number_str}' and 'spidey' not found in {BASE_PATH}")
        return

    # Kiểm tra xem video đã có trong CSV chưa
    existing_paths = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            df_existing = pd.read_csv(OUTPUT_FILE, encoding='utf-8-sig')
            if 'file_path' in df_existing.columns:
                existing_paths = set(df_existing['file_path'].dropna().tolist())
        except Exception as e:
            print(f"Error reading CSV to get existing files: {e}")
            return

    if next_video_path in existing_paths:
        print(f"Video '{os.path.basename(next_video_path)}' already exists in {OUTPUT_FILE}")
        return

    # Lấy thời lượng video
    try:
        with VideoFileClip(next_video_path) as video:
            minute = int(round(video.duration)) // 60
            sec = int(round(video.duration)) % 60
            duration = f'{minute}:{sec:02d}'
    except Exception as e:
        print(f"Error getting duration for '{next_video_path}': {e}")
        duration = "0:00"

    # Lấy thời gian tạo file
    try:
        ctime = os.path.getmtime(next_video_path)
        now = datetime.now().timestamp()
        creation_time = int(now - ctime)
    except Exception as e:
        print(f"Error getting creation time for '{next_video_path}': {e}")
        creation_time = None

    # Thêm vào CSV
    try:
        columns = ['stt', 'file_path', 'duration', 'lastest_used_value']
        new_row = pd.DataFrame([[next_number, next_video_path, duration, creation_time]], columns=columns)
        if os.path.exists(OUTPUT_FILE):
            df = pd.read_csv(OUTPUT_FILE, encoding='utf-8-sig')
            if set(columns).issubset(df.columns):
                df = df[columns]
            df = pd.concat([df, new_row], ignore_index=True)
        else:
            df = new_row
        df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        print(f"Added to CSV: {next_video_path}")
    except Exception as e:
        print(f"Error writing to CSV file '{OUTPUT_FILE}': {e}")


check_and_add_next_spidey_video()