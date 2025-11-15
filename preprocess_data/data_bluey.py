import pandas as pd
import os
from tkinter import filedialog, Tk, messagebox
from datetime import datetime
from moviepy import VideoFileClip
import gspread
from google.oauth2.service_account import Credentials

# Constants
EXCEL_FILE = 'Auto_edit_vids.xlsx'
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov'}
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
CREDS_FILE = "sheet.json"
SHEET_NAME = 'Auto_edit_vids'

def get_file_list(folder_path, extensions=None):
    try:
        if not os.path.exists(folder_path):
            print(f"Folder '{folder_path}' does not exist.")
            return []

        file_list = []
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isfile(item_path):
                absolute_path = os.path.abspath(item_path)
                if extensions is None or os.path.splitext(item)[1].lower() in extensions:
                    file_list.append(absolute_path)
        return file_list
    except Exception as e:
        print(f"Error accessing folder '{folder_path}': {e}")
        return []

def get_video_duration(file_path):
    try:
        with VideoFileClip(file_path) as video:
            minute = int(round(video.duration)) // 60
            sec = int(round(video.duration)) % 60
            if sec < 10:
                sec = f'0{sec}'
            return f'{minute}:{sec}'
    except Exception as e:
        print(f"Error getting duration for '{file_path}': {e}")
        return "0:00"

def get_creation_time(file_path):
    try:
        ctime = os.path.getmtime(file_path)
        now = datetime.now().timestamp()
        return int(now - ctime)
    except Exception as e:
        print(f"Error getting creation time for '{file_path}': {e}")
        return None

def get_last_stt(excel_file):
    try:
        if not os.path.exists(excel_file):
            return 0
        df = pd.read_excel(excel_file, engine='openpyxl')
        return int(df['stt'].max()) if 'stt' in df.columns and not df.empty else 0
    except Exception as e:
        print(f"Error reading Excel file '{excel_file}': {e}")
        return 0

def append_to_excel(excel_file, values):
    try:
        columns = ['stt', 'file_path', 'duration', 'lastest_used_value', 'first vids',
                   'desired length', 'output directory', 'number_of_vids', 'status']
        new_row = pd.DataFrame([values], columns=columns)
        if os.path.exists(excel_file):
            df = pd.read_excel(excel_file, engine='openpyxl')
            df = pd.concat([df, new_row], ignore_index=True)
        else:
            df = new_row
        df.to_excel(excel_file, index=False, engine='openpyxl')
    except Exception as e:
        print(f"Error writing to Excel file '{excel_file}': {e}")

def update_ggsheet(gspread_client, sheet_name):
    df = pd.read_excel(EXCEL_FILE, engine="openpyxl")
    spreadsheet = gspread_client.open(sheet_name)
    worksheet = spreadsheet.sheet1
    worksheet.clear()
    df_clean = df.fillna("")
    data = [df_clean.columns.tolist()] + df_clean.values.tolist()
    worksheet.update(range_name="A1", values=data)
    worksheet.format("1:1", {"textFormat": {"bold": True}})
    print("Saved all Excel content into Google Sheet!")

def process_file(file_path, stt):
    duration = get_video_duration(file_path)
    creation_time = get_creation_time(file_path)
    append_to_excel(EXCEL_FILE, [
        stt,
        file_path,
        duration,
        creation_time,
        None, None, None, 1, None
    ])
    print(f"Added to excel: {file_path}")

def main():
    # GUI để chọn chế độ
    root = Tk()
    root.withdraw()
    mode = messagebox.askquestion("Chọn chế độ", "Chọn Yes để chạy NEW (clear toàn bộ), No để chạy UPDATE (chỉ thêm video mới).")
    is_new_mode = (mode == 'yes')

    folder_path = filedialog.askdirectory(title="Chọn thư mục chứa video")
    if not folder_path:
        print("Không chọn thư mục.")
        return

    video_files = get_file_list(folder_path, VIDEO_EXTENSIONS)
    if not video_files:
        print("Không tìm thấy video nào.")
        return

    existing_paths = set()
    if not is_new_mode and os.path.exists(EXCEL_FILE):
        try:
            df_existing = pd.read_excel(EXCEL_FILE, engine='openpyxl')
            if 'file_path' in df_existing.columns:
                existing_paths = set(df_existing['file_path'].dropna().tolist())
        except Exception as e:
            print(f"Lỗi khi đọc Excel để lấy danh sách file cũ: {e}")

    if is_new_mode:
        if os.path.exists(EXCEL_FILE):
            os.remove(EXCEL_FILE)
            print("Đã xóa file Excel cũ.")
        stt = 1
    else:
        stt = get_last_stt(EXCEL_FILE) + 1

    # Ghi dữ liệu
    for file_path in video_files:
        if is_new_mode or file_path not in existing_paths:
            process_file(file_path, stt)
            stt += 1
        else:
            print(f"Bỏ qua (đã có): {file_path}")

    # Ghi lên Google Sheet
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    gc = gspread.authorize(creds)
    update_ggsheet(gc, SHEET_NAME)

if __name__ == '__main__':
    main()
