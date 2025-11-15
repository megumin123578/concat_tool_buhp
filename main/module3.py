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
import shutil

# Suppress moviepy subtitle warning
warnings.filterwarnings("ignore", message="Subtitle stream parsing is not supported by moviepy")


def check_and_add_next_spidey_videos(batch_size=5):
    OUTPUT_FILE = r"C:\Users\Admin\Documents\concatenate videos\ref\spidey_data.csv"
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov'}
    BASE_PATH = r'\\nashp\DATABUHP\Nam SEO\.Spidey'

    # Lấy số thứ tự video cuối cùng từ CSV
    last_number = 0
    if os.path.exists(OUTPUT_FILE):
        try:
            df = pd.read_csv(OUTPUT_FILE, encoding='utf-8-sig')
            if not df.empty and 'stt' in df.columns:
                last_number = int(df['stt'].iloc[-1]) #get last number
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

    # Tạo set lưu path đã có
    existing_paths = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            df_existing = pd.read_csv(OUTPUT_FILE, encoding='utf-8-sig')
            if 'file_path' in df_existing.columns:
                existing_paths = set(df_existing['file_path'].dropna().tolist())
        except Exception as e:
            print(f"Error reading CSV to get existing files: {e}")
            return

    added_count = 0
    all_files = []
    for root, _, files in os.walk(BASE_PATH):
        for item in files:
            if os.path.splitext(item)[1].lower() in VIDEO_EXTENSIONS:
                all_files.append(os.path.abspath(os.path.join(root, item)))

    all_files = sorted(all_files, key=lambda x: x.lower())  # Sắp xếp để ưu tiên trật tự tên

    # Tìm và thêm batch_size video kế tiếp
    for i in range(1, batch_size + 1):
        next_number = last_number + i
        next_number_str = f"{next_number:03d}"

        matched_file = None
        for path in all_files:
            filename = os.path.basename(path).lower()
            if next_number_str in filename and 'spidey' in filename:
                matched_file = path
                break

        if not matched_file:
            print(f"[{next_number_str}] Không tìm thấy video chứa '{next_number_str}' và 'spidey'")
            continue

        if matched_file in existing_paths:
            print(f"[{next_number_str}] Đã tồn tại: {os.path.basename(matched_file)}")
            continue

        # Lấy thời lượng video
        try:
            with VideoFileClip(matched_file) as video:
                minute = int(round(video.duration)) // 60
                sec = int(round(video.duration)) % 60
                duration = f'{minute}:{sec:02d}'
        except Exception as e:
            print(f"[{next_number_str}] Lỗi đọc thời lượng video: {e}")
            duration = "0:00"

        # Thời gian tạo
        try:
            ctime = os.path.getmtime(matched_file)
            now = datetime.now().timestamp()
            creation_time = int(now - ctime)
        except Exception as e:
            print(f"[{next_number_str}] Lỗi lấy thời gian tạo file: {e}")
            creation_time = None

        # Ghi vào CSV
        try:
            columns = ['stt', 'file_path', 'duration', 'lastest_used_value']
            new_row = pd.DataFrame([[next_number, matched_file, duration, creation_time]], columns=columns)
            if os.path.exists(OUTPUT_FILE):
                df = pd.read_csv(OUTPUT_FILE, encoding='utf-8-sig')
                if set(columns).issubset(df.columns):
                    df = df[columns]
                df = pd.concat([df, new_row], ignore_index=True)
            else:
                df = new_row
            df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
            added_count += 1
            print(f"[{next_number_str}] Đã thêm: {matched_file}")
        except Exception as e:
            print(f"[{next_number_str}] Lỗi ghi vào CSV: {e}")

    print(f"\nTổng cộng đã thêm {added_count} video vào '{OUTPUT_FILE}'.")





def get_video_duration(file_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
             "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            capture_output=True, text=True
        )
        duration = float(result.stdout.strip())
        minute = int(duration) // 60
        sec = int(duration) % 60
        return f"{minute}:{sec:02}"
    except Exception as e:
        print(f"Error getting duration for '{file_path}': {e}")
        return "0:00"


def get_list_video(ls, data_csv):  # return [(path, duration), ...]
    try:
        if not os.path.exists(data_csv):
            print(f"CSV file '{data_csv}' not found.")
            return []

        # Đọc CSV
        df = pd.read_csv(data_csv, encoding='utf-8-sig')

        # Chuyển ls thành danh sách số nguyên
        stt_list = [int(x.strip()) for x in ls.split(',') if x.strip().isdigit()]

        result = []
        for val in stt_list:
            row = df[df['stt'] == val]
            if not row.empty:
                path = row.iloc[0]['file_path']
                result.append(path)
            else:
                print(f"stt {val} không tồn tại trong CSV.")

        return result

    except Exception as e:
        print(f"Error in get_list_video: {e}")
        return []


def normalize_video(
    input_path,
    output_path,
    width=1920,
    height=1080,
    fps=30,
    use_nvenc=True,
    cq=23,
    v_bitrate="12M",
    a_bitrate="160k",
):
     # Kiểm tra input/output có đúng định dạng string không
    if not isinstance(input_path, str) or not isinstance(output_path, str):
        raise TypeError(f"Đường dẫn input/output không hợp lệ: input={input_path}, output={output_path}")

    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg không được tìm thấy trong PATH.")

    if use_nvenc and shutil.which("nvidia-smi"):
        vcodec = "h264_nvenc"
        video_args = [
            "-c:v", vcodec,
            "-profile:v", "main",
            "-rc", "cbr",
            "-cq", str(cq),
            "-b:v", v_bitrate,
            "-maxrate", v_bitrate,
            "-bufsize", str(int(int(v_bitrate[:-1]) * 2)) + "M" if v_bitrate.endswith("M") else "16M",
            "-preset", "p4",
        ]
    else:
        vcodec = "libx264"
        video_args = [
            "-c:v", vcodec,
            "-preset", "medium",
            "-profile:v", "main",
            "-level", "4.2",
            "-crf", str(cq if isinstance(cq, int) else 20),
            "-maxrate", v_bitrate,
            "-bufsize", "16M",
        ]

    command = [
        "ffmpeg", "-y",
        "-fflags", "+genpts",
        "-i", input_path,
        "-vf", f"scale={width}:{height}:flags=lanczos,fps={fps}",
        *video_args,
        "-pix_fmt", "yuv420p",
        # "-vsync", "cfr",
        "-fps_mode", "cfr",     
        "-r", str(fps),         
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-ar", "48000",
        "-b:a", a_bitrate,
        output_path
    ]

    subprocess.run(command, check=True)



def concat_video(video_paths, output_path):
    list_file = "temp.txt"
    with open(list_file, 'w', encoding='utf-8') as f:
        for path in video_paths:
            abs_path = os.path.abspath(path).replace("\\", "/")
            f.write(f"file '{abs_path}'\n")

    command = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_path
    ]
    subprocess.run(command, check=True)
    os.remove(list_file)


def auto_concat(input_videos, output_path):
    normalized_paths = []

    def normalize_and_collect(i, path):
        fixed = f"normalized_{i}.mp4"
        normalize_video(path, fixed)
        return fixed

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(normalize_and_collect, i, path) for i, path in enumerate(input_videos)]
        for future in futures:
            normalized_paths.append(future.result())

    concat_video(normalized_paths, output_path)

    for path in normalized_paths:
        os.remove(path)

    print("Ghép video hoàn tất:", output_path)

# debug
def print_video_info(video_path):
    print(f"\nĐang kiểm tra: {video_path}")

    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", video_path],
            capture_output=True, text=True, check=True
        )
        info = json.loads(result.stdout)

        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                print(f"VIDEO:")
                print(f"  Codec: {stream.get('codec_name')}")
                print(f"  Resolution: {stream.get('width')}x{stream.get('height')}")
                print(f"  FPS: {eval(stream.get('r_frame_rate')):.2f}")
                print(f"  Pixel format: {stream.get('pix_fmt')}")
            elif stream.get("codec_type") == "audio":
                print(f"AUDIO:")
                print(f"  Codec: {stream.get('codec_name')}")
                print(f"  Sample rate: {stream.get('sample_rate')} Hz")
                print(f"  Channels: {stream.get('channels')}")
        
        format_info = info.get("format", {})
        duration = float(format_info.get("duration", 0))
        print(f"Duration: {duration:.2f} seconds")

    except Exception as e:
        print(f"Lỗi khi đọc thông tin video: {e}")


def excel_to_sheet(excel_file, sheet_file, idx):
    df = pd.read_excel(excel_file, engine="openpyxl")


    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    CREDS_FILE = r"C:\Users\Admin\Documents\concatenate videos\ref\sheet.json"

    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    gc = gspread.authorize(creds)

    spreadsheet = gc.open(sheet_file)
    worksheet = spreadsheet.get_worksheet(idx)  

    worksheet.clear()

    data = [df.columns.values.tolist()] + df.values.tolist()
    data = [df.columns.tolist()] + df.fillna('').astype(str).values.tolist()



    worksheet.update("A1", data)  # Ghi bắt đầu từ A1

    print("Đã ghi toàn bộ nội dung Excel vào Google Sheet!")