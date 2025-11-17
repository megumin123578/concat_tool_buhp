import pandas as pd
import numpy as np
import random
import os
import gspread
from google.oauth2.service_account import Credentials
from module6 import auto_concat, find_first_vid, excel_to_sheet 


EXCEL_FILE = r"C:\Users\Admin\Documents\concatenate videos\ref\temp.xlsx"
CSV_FILE = r"C:\Users\Admin\Documents\concatenate videos\ref\bluey_funtoys_data.csv"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
CREDS_FILE = r"C:\Users\Admin\Documents\concatenate videos\ref\sheet.json" 
SHEET_NAME = 'Auto_concat_vids_ver2'  
OUTPUT_DIR = r"E:\ghep_\bluey_funtoys"
MAX_AGE_SECONDS = 55 * 24 * 60 * 60  * 0 
USED_LOG_FILE = r"C:\Users\Admin\Documents\concatenate videos\log_file\bluey_funtoys.log"
SHEET_INDEX = 2


def load_used_videos():
    if os.path.exists(USED_LOG_FILE):
        with open(USED_LOG_FILE, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_used_videos(used_set):
    with open(USED_LOG_FILE, 'w', encoding='utf-8') as f:
        for path in used_set:
            f.write(f"{path}\n")

############ UPDATE EXCEL DATA #############
def clear_excel_file(excel_file):
    try:
        columns = ['first vids', 'desired length', 'output directory', 'number_of_vids', 'status']
        empty_df = pd.DataFrame(columns=columns)
        empty_df.to_excel(excel_file, index=False, engine='openpyxl')
        print(f"Cleared existing content in Excel file: {excel_file}")
    except Exception as e:
        print(f"Error clearing Excel file '{excel_file}': {e}")

def copy_from_ggsheet_to_excel(gspread_client, sheet_name, excel_file):
    try:
        spreadsheet = gspread_client.open(sheet_name)
        worksheet = spreadsheet.get_worksheet(SHEET_INDEX)
        data = worksheet.get_all_values()

        if not data:
            print("Google Sheet is empty!")
            return
        
        columns = data[0]  
        values = data[1:]  
        df = pd.DataFrame(values, columns=columns)
        clear_excel_file(excel_file)
        df.to_excel(excel_file, index=False, engine='openpyxl')
        print(f"Successfully copied data from Google {sheet_name} to Excel file {excel_file}")
    except Exception as e:
        print(f"Error copying data from Google Sheet to Excel: {e}")

############ PREPROCESS DATA #############
def pre_process_data(file):
    df = pd.read_excel(file)
    filtered_df = df[
        df['first vids'].notna() &
        df['desired length'].notna() &
        df['status'].str.lower().eq('auto')
    ]
    return filtered_df, df

def convert_time_to_seconds(time_str):
    try:
        if isinstance(time_str, (int, float)):
            return float(time_str)
        parts = time_str.strip().split(':')
        parts = [int(p) for p in parts]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 1:
            return int(parts[0])
        else:
            return 0
    except:
        return 0

def prepare_original_data():
    try:
        df = pd.read_csv(CSV_FILE, encoding='utf-8-sig')
        durations = np.array([convert_time_to_seconds(d) for d in df['duration']])
        last_used = np.array([convert_time_to_seconds(t) for t in df['lastest_used_value']])
        file_paths = df['file_path'].tolist()
        return durations, last_used, file_paths, df
    except FileNotFoundError:
        print(f"Error: CSV file '{CSV_FILE}' not found.")
        return None, None, None, None
    except KeyError as e:
        print(f"Error: Missing column {e} in the CSV file.")
        return None, None, None, None
    except Exception as e:
        print(f"Unexpected error reading CSV: {str(e)}")
        return None, None, None, None

def generate_video_lists(suitable_df, durations, last_used, file_paths):
    results = []
    for i in range(len(suitable_df)):
        num_lists = 1  # Force number_of_vids to 1
        desired_length = float(suitable_df.iloc[i]['desired length']) * 60
        first_vid_number = int(suitable_df.iloc[i]['first vids'])

        first_vd = find_first_vid(first_vid_number)
        first_path, first_duration = first_vd[0], convert_time_to_seconds(first_vd[1])
        if not first_path:
            print(f"Không tìm thấy video đầu tiên cho {first_vid_number}")
            continue

        for list_index in range(num_lists):
            available_indexes = [
                idx for idx in range(len(file_paths))
                if last_used[idx] >= MAX_AGE_SECONDS
            ]

            total_duration = first_duration
            selected_indexes = []
            selected_paths = [first_path]

            while available_indexes and total_duration < desired_length:
                chosen_index = random.choice(available_indexes)
                total_duration += durations[chosen_index]
                selected_indexes.append(chosen_index)
                selected_paths.append(file_paths[chosen_index])
                available_indexes.remove(chosen_index)

            results.append({
                'name': first_vid_number,
                'group_index': i,
                'list_number': list_index + 1,
                'selected_files': selected_paths,
                'total_duration': total_duration
            })

    return results

def format_and_print_results(results):
    for item in results:
        minutes = int(item['total_duration']) // 60
        seconds = int(item['total_duration']) % 60
        print(f"\nList {item['list_number']}:")
        print(f"Total duration: {minutes:02}:{seconds:02}")
        print("Files:")
        for f in item['selected_files']:
            print("  ", f)
    
def main():

    def load_used_videos():
        if os.path.exists(USED_LOG_FILE):
            with open(USED_LOG_FILE, 'r', encoding='utf-8') as f:
                return set(line.strip() for line in f if line.strip())
        return set()

    def save_used_videos(used_set):
        with open(USED_LOG_FILE, 'w', encoding='utf-8') as f:
            for path in used_set:
                f.write(f"{path}\n")

    
    try:
        creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
        gc = gspread.authorize(creds)
        copy_from_ggsheet_to_excel(gc, SHEET_NAME, EXCEL_FILE)
    except Exception as e:
        print(f"Error in main execution: {e}")
        return

    
    try:
        suitable_df, original_df = pre_process_data(EXCEL_FILE)
        if suitable_df.empty:
            print("No suitable data found for processing (status='auto' with non-null 'first vids' and 'desired length').")
            return

        durations, last_used, file_paths, csv_df = prepare_original_data()
        if csv_df is None:
            print("Failed to load data from CSV. Exiting.")
            return

        used_video_paths = load_used_videos()
        results = []
        newly_used_paths = set()

        for i in range(len(suitable_df)):
            num_lists = 1
            desired_length = float(suitable_df.iloc[i]['desired length']) * 60
            first_vid_number = int(suitable_df.iloc[i]['first vids'])

            first_vd = find_first_vid(first_vid_number)
            first_path, first_duration = first_vd[0], convert_time_to_seconds(first_vd[1])
            if not first_path:
                print(f"Không tìm thấy video đầu tiên cho {first_vid_number}")
                continue

            for list_index in range(num_lists):
                available_indexes = [
                    idx for idx in range(len(file_paths))
                    if file_paths[idx] not in used_video_paths
                ]

                # Reset nếu đã dùng hết
                if not available_indexes:
                    print("Đã dùng hết video, reset log.")
                    used_video_paths.clear()
                    available_indexes = list(range(len(file_paths)))

                total_duration = first_duration
                selected_paths = [first_path]
                newly_used_paths.add(first_path)

                while available_indexes and total_duration < desired_length:
                    chosen_index = random.choice(available_indexes)
                    path = file_paths[chosen_index]
                    if path not in used_video_paths:
                        total_duration += durations[chosen_index]
                        selected_paths.append(path)
                        newly_used_paths.add(path)
                    available_indexes.remove(chosen_index)

                results.append({
                    'name': first_vid_number,
                    'group_index': i,
                    'list_number': list_index + 1,
                    'selected_files': selected_paths,
                    'total_duration': total_duration
                })

        if not results:
            print("No video lists generated.")
            return

        format_and_print_results(results)

    except FileNotFoundError:
        print(f"Error: File '{EXCEL_FILE}' not found.")
        return
    except KeyError as e:
        print(f"Error: Missing column {e} in the Excel file.")
        return
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return

    # Bước 3: Ghép video + cập nhật Excel
    for ls in results:
        name = ls['name']
        filename = f"{name}_Bluey_funtoys_ghep.mp4"
        output_path = os.path.join(OUTPUT_DIR, filename)
        auto_concat(ls['selected_files'], output_path)

        group_index = ls['group_index']
        row_index = suitable_df.index[group_index]

        current_value = original_df.at[row_index, 'output directory']
        if pd.isna(current_value) or str(current_value).strip().lower() == 'nan' or current_value == "":
            original_df.at[row_index, 'output directory'] = output_path
        else:
            original_df.at[row_index, 'output directory'] = f"{current_value}\n{output_path}"

        original_df.at[row_index, 'status'] = 'Done'
        original_df.at[row_index, 'number_of_vids'] = 1

    #Lưu file Excel & cập nhật Google Sheet
    try:
        if 'number_of_vids' in original_df.columns:
            original_df = original_df.drop(columns=['number_of_vids'])
        original_df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')
        print("Saved all Excel content into Excel file")
        excel_to_sheet(EXCEL_FILE, SHEET_NAME,SHEET_INDEX)
        print("Updated Google Sheet.")
    except Exception as e:
        print(f"Error: {e}")

    #Lưu log video đã dùng
    used_video_paths.update(newly_used_paths)
    save_used_videos(used_video_paths)


if __name__ == '__main__':
    main()