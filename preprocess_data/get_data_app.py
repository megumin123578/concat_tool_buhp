import pandas as pd
import os
from tkinter import filedialog, Tk, Button, Label, Frame, messagebox
from datetime import datetime
from moviepy import VideoFileClip
import warnings
import threading
import subprocess


# Suppress the specific moviepy subtitle warning
warnings.filterwarnings("ignore", message="Subtitle stream parsing is not supported by moviepy")

# Constants
OUTPUT_FILE = r"C:\Users\Admin\Documents\concatenate videos\ref\beca_data.csv"
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov'}

def get_file_list(folder_path, extensions=None):
    try:
        if not os.path.exists(folder_path):
            print(f"Folder '{folder_path}' does not exist.")
            return []
        file_list = []
        for root, _, files in os.walk(folder_path):
            if 'quay' in os.path.basename(root).lower():
                print("Skip folder:", root)
                continue
            for item in files:
                item_path = os.path.join(root, item)
                absolute_path = os.path.abspath(item_path)
                if extensions is None or os.path.splitext(item)[1].lower() in extensions:
                    file_list.append(absolute_path)
        return file_list
    except Exception as e:
        print(f"Error accessing folder '{folder_path}': {e}")
        return []

def get_video_duration(file_path):
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration", "-of",
                "default=noprint_wrappers=1:nokey=1", file_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=100  # tránh treo mãi
        )
        duration_sec = float(result.stdout.decode().strip())
        minute = int(duration_sec) // 60
        sec = int(duration_sec) % 60
        if sec < 10:
            sec = f"0{sec}"
        return f"{minute}:{sec}"
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

def get_last_stt(output_file):
    try:
        if not os.path.exists(output_file):
            return 0
        df = pd.read_csv(output_file, encoding='utf-8-sig')
        return int(df['stt'].max()) if 'stt' in df.columns and not df.empty else 0
    except Exception as e:
        print(f"Error reading CSV file '{output_file}': {e}")
        return 0

def append_to_csv(output_file, values):
    try:
        columns = ['stt', 'file_path', 'duration', 'lastest_used_value']
        new_row = pd.DataFrame([values], columns=columns)
        if os.path.exists(output_file):
            df = pd.read_csv(output_file, encoding='utf-8-sig')
            # Ensure only desired columns are kept
            if set(columns).issubset(df.columns):
                df = df[columns]  # Keep only the desired columns if they exist
            df = pd.concat([df, new_row], ignore_index=True)
        else:
            df = new_row
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
    except Exception as e:
        print(f"Error writing to CSV file '{output_file}': {e}")

def process_file(file_path, stt):
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration", "-of",
                "default=noprint_wrappers=1:nokey=1", file_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=100
        )
        duration_sec = float(result.stdout.decode().strip())
        if duration_sec < 60:
            print(f"Skipped (under 1 min): {file_path}")
            return
        minute = int(duration_sec) // 60
        sec = int(duration_sec) % 60
        if sec < 10:
            sec = f"0{sec}"
        duration_str = f"{minute}:{sec}"
        creation_time = get_creation_time(file_path)
        append_to_csv(OUTPUT_FILE, [
            stt,
            file_path,
            duration_str,
            creation_time
        ])
        print(f"Added to CSV: {file_path}")
    except Exception as e:
        print(f"Error processing file '{file_path}': {e}")


def run_mode(is_new_mode):
    folder_path = filedialog.askdirectory(title="Select Video Folder")
    if not folder_path:
        messagebox.showerror("Error", "No folder selected. Please select a folder containing videos.")
        return

    video_files = sorted(get_file_list(folder_path, VIDEO_EXTENSIONS), key=lambda x: os.path.basename(x).lower())

    if not video_files:
        messagebox.showinfo("Info", "No videos found in the selected folder.")
        return

    existing_paths = set()
    if not is_new_mode and os.path.exists(OUTPUT_FILE):
        try:
            df_existing = pd.read_csv(OUTPUT_FILE, encoding='utf-8-sig')
            if 'file_path' in df_existing.columns:
                existing_paths = set(df_existing['file_path'].dropna().tolist())
        except Exception as e:
            print(f"Error reading CSV to get existing files: {e}")

    if is_new_mode:
        if os.path.exists(OUTPUT_FILE):
            os.remove(OUTPUT_FILE)
            print("Deleted old CSV file.")
        stt = 1
    else:
        stt = get_last_stt(OUTPUT_FILE) + 1

    # Process files
    for file_path in video_files:
        if is_new_mode or file_path not in existing_paths:
            process_file(file_path, stt)
            stt += 1
        else:
            print(f"Skipped (already exists): {file_path}")

    messagebox.showinfo("Success", f"Processing complete! Data saved to {OUTPUT_FILE}")
    root.destroy()

def create_gui():
    global root
    root = Tk()
    root.title("Video Processing Tool")
    root.geometry("500x250")
    root.configure(bg="#f0f0f0")

    # Main frame
    main_frame = Frame(root, bg="#f0f0f0")
    main_frame.pack(pady=20, padx=20, fill="both", expand=True)

    # Title
    title_label = Label(main_frame, text="Video Processing Tool", font=("Arial", 16, "bold"), bg="#f0f0f0")
    title_label.pack(pady=10)

    # Mode buttons
    button_frame = Frame(main_frame, bg="#f0f0f0")
    button_frame.pack(pady=20)

    clear_button = Button(button_frame, text="Clear and Process", font=("Arial", 12),
                         command=lambda: threading.Thread(target=lambda: run_mode(True)).start(),
                         bg="#08fc5d", fg="white", relief="flat", width=15)
    clear_button.pack(side="left", padx=10)

    add_button = Button(button_frame, text="Add New Videos", font=("Arial", 12),
                       command=lambda: threading.Thread(target=lambda: run_mode(False)).start(),
                       bg="#2196F3", fg="white", relief="flat", width=15)
    add_button.pack(side="left", padx=10)


    # Instructions
    instructions = Label(main_frame, text="Clear: Replace all data\nAdd: Append new videos only",
                        font=("Arial", 10), bg="#f0f0f0", justify="center")
    instructions.pack(pady=10)

    root.mainloop()

if __name__ == '__main__':
    create_gui()