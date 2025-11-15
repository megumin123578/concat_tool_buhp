import os
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import re
import shutil


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

def find_first_vid(first_vd):  # return path, duration
    base_folder = r'\\Fmc\E\may cay'
    video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.flv']

    try:
        pattern = re.compile(rf'(?<!\d){first_vd}(?!\d)')  
        matched_folders = [
            os.path.join(base_folder, name)
            for name in os.listdir(base_folder)
            if os.path.isdir(os.path.join(base_folder, name)) and pattern.search(name)
        ]

        if not matched_folders:
            print(f"\nKhông tìm thấy thư mục nào chứa đúng '{first_vd}' trong tên.")
            return None, 0

        for folder in matched_folders:
            for root, _, files in os.walk(folder):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in video_extensions):
                        full_path = os.path.join(root, file)
                        duration = get_video_duration(full_path)
                        return full_path, duration

        print(f"\nKhông tìm thấy video nào trong thư mục chứa '{first_vd}'.")
        return None, 0

    except Exception as e:
        print("Lỗi:", e)
        return None, 0
    


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