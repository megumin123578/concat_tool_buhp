import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe
from module3 import *
import sys
sys.stdout.reconfigure(encoding='utf-8')

EXCEL_FILE = r"C:\Users\Admin\Documents\concatenate videos\ref\temp.xlsx"
CSV_FILE = r"C:\Users\Admin\Documents\concatenate videos\ref\spidey_data.csv"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
CREDS_FILE = r"C:\Users\Admin\Documents\concatenate videos\ref\sheet.json"
SHEET_NAME = 'Auto_concat_vids_ver2'
OUTPUT_DIR = r"\\n8n\D\output_spidey"


def clear_excel_file(excel_file):
    try:
        columns = ['input', 'first vids', 'desired length', 'output directory', 'status']
        empty_df = pd.DataFrame(columns=columns)
        empty_df.to_excel(excel_file, index=False, engine='openpyxl')
        print(f"Cleared existing content in Excel file: {excel_file}")
    except Exception as e:
        print(f"Error clearing Excel file '{excel_file}': {e}")

def copy_from_ggsheet_to_excel(gspread_client, sheet_name, excel_file, idx):
    try:
        spreadsheet = gspread_client.open(sheet_name)
        worksheet = spreadsheet.get_worksheet(idx)
        data = worksheet.get_all_values()

        if not data:
            print("Google Sheet is empty!")
            return

        columns = data[0]
        values = data[1:]
        df = pd.DataFrame(values, columns=columns)
        clear_excel_file(excel_file)
        df.to_excel(excel_file, index=False, engine='openpyxl')
        print(f"Successfully copied data from Google Sheet '{sheet_name}' to Excel file '{excel_file}'")
    except Exception as e:
        print(f"Error copying data from Google Sheet to Excel: {e}")

def pre_process_data(file):
    try:
        df = pd.read_excel(file)
        required_columns = ['input', 'status']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            raise ValueError(f"Missing required columns in Excel file: {missing}")
        filtered_df = df[
            df['input'].notna() &
            df['status'].str.lower().eq('auto')
        ]
        return filtered_df, df
    except Exception as e:
        print(f"Error in pre_process_data: {e}")
        return pd.DataFrame(), pd.DataFrame()



def main(worksheet_idx=2):

    check_and_add_next_spidey_videos()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(CSV_FILE):
        print(f"CSV file '{CSV_FILE}' không tồn tại. Thoát.")
        return

    try:
        creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
        gc = gspread.authorize(creds)
        copy_from_ggsheet_to_excel(gc, SHEET_NAME, EXCEL_FILE, worksheet_idx)
    except Exception as e:
        print(f"Lỗi xác thực Google hoặc tải sheet: {e}")
        return


    suitable_df, original_df = pre_process_data(EXCEL_FILE)
    if suitable_df.empty:
        print("Không có hàng nào status='auto' và input hợp lệ. Kết thúc.")
        return

    if 'output directory' not in original_df.columns:
        original_df['output directory'] = ""
    if 'status' not in original_df.columns:
        original_df['status'] = ""

    jobs = []
    for idx, row in suitable_df.iterrows():
        stt_string = str(row['input']).strip()
        if not stt_string:
            continue

        print(f"Processing row {idx}: {row.to_dict()}")
        paths = get_list_video(stt_string, CSV_FILE)  # list[str]
        if not paths:
            print(f"Row {idx}: không tìm thấy file hợp lệ trong CSV.")
            original_df.at[idx, 'status'] = 'Error'
            continue

        # Lấy tên file (không path) để làm tên output
        # Lấy số từ cột 'input' để làm tên file
        stt_list = [x.strip() for x in stt_string.split(',') if x.strip().isdigit()]
        base_name = "_".join(stt_list) + "_spidey_ghep"


        safe_base_name = "".join(c for c in base_name if c not in r'\/:*?"<>|').strip() or f"group_{idx}"
        output_path = os.path.join(OUTPUT_DIR, f"{safe_base_name}.mp4")

        jobs.append({
            "group_index": idx,
            "name": safe_base_name,
            "selected_files": paths,
            "output_path": output_path,
        })

    if not jobs:
        print("Không có job hợp lệ để xử lý. Kết thúc.")
        return

    for job in jobs:
        print(f"Concatenating {len(job['selected_files'])} video(s) -> {job['output_path']}")
        ok = auto_concat(job['selected_files'], job['output_path'])
        row_index = job['group_index']
        current_value = original_df.at[row_index, 'output directory']
        new_val = job['output_path'] if pd.isna(current_value) or str(current_value).strip().lower() in ('nan', '') else f"{current_value}\n{job['output_path']}"
        original_df.at[row_index, 'output directory'] = new_val
        original_df.at[row_index, 'status'] = 'Done'

    try:
        original_df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')
        print(f"Đã lưu Excel: {EXCEL_FILE}")
        excel_to_sheet(EXCEL_FILE, SHEET_NAME, idx=worksheet_idx)
        print("Đã cập nhật Google Sheet.")
    except Exception as e:
        print(f"Lỗi khi lưu hoặc cập nhật Google Sheet: {e}")

if __name__ == '__main__':

    main()