# auto_runner.py
import os
import time
import subprocess
from datetime import datetime
from email.message import EmailMessage
import smtplib
import socket
import traceback
import sys
from pathlib import Path

SLEEP_SECONDS = 30

# ===== SMTP config (Gmail App Password hoặc SMTP khác) =====
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER or "")
EMAIL_TO = os.getenv("EMAIL_TO")  # hỗ trợ "a@x.com,b@y.com"

MAX_BODY_CHARS = 15000  # giới hạn nội dung log/email

# ===== Đảm bảo chạy các script từ cùng thư mục với auto_runner =====
SCRIPT_DIR = Path(__file__).resolve().parent

# Danh sách task: name, cmd, enabled
TASKS = [
    {"name": "be_ca.py",         "cmd": [sys.executable, str(SCRIPT_DIR / "be_ca.py")],         "enabled": True},
    {"name": "bluey.py",         "cmd": [sys.executable, str(SCRIPT_DIR / "bluey.py")],         "enabled": True},
    {"name": "spidey.py",        "cmd": [sys.executable, str(SCRIPT_DIR / "spidey.py")],        "enabled": True},
    {"name": "maycay.py",        "cmd": [sys.executable, str(SCRIPT_DIR / "maycay.py")],        "enabled": True},
    {"name": "findtoys.py",      "cmd": [sys.executable, str(SCRIPT_DIR / "findtoys.py")],      "enabled": True},
    {"name": "bluey_funtoys.py", "cmd": [sys.executable, str(SCRIPT_DIR / "bluey_funtoys.py")], "enabled": True},
]

def send_error_email(task_name: str, err_summary: str, stdout_text: str, stderr_text: str):
    if not (SMTP_USER and SMTP_PASS and EMAIL_FROM and EMAIL_TO):
        print("[WARN] Thiếu cấu hình SMTP/EMAIL_*, bỏ qua gửi email.")
        return

    hostname = socket.gethostname()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _trim(s: str) -> str:
        if s is None:
            return ""
        s = s.strip()
        return (s[:MAX_BODY_CHARS] + "\n...[trimmed]") if len(s) > MAX_BODY_CHARS else s

    subject = f"[AutoRunner] Lỗi khi chạy {task_name} @ {now}"
    body = f"""Thời điểm : {now}
Máy      : {hostname}
Script   : {task_name}

Tóm tắt lỗi:
{err_summary}

=== STDOUT ===
{_trim(stdout_text)}

=== STDERR ===
{_trim(stderr_text)}
"""

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print(f"[INFO] Đã gửi email lỗi cho '{task_name}' tới {EMAIL_TO}")
    except Exception as e:
        print(f"[ERROR] Gửi email thất bại: {e}")

def disable_task(task_name: str):
    for t in TASKS:
        if t["name"] == task_name:
            t["enabled"] = False
            return True
    return False

def run_task_once(task):
    name = task["name"]
    cmd = task["cmd"]
    print(f"Running {name} ...")

    # Nếu file không tồn tại thì disable luôn
    if not Path(cmd[-1]).exists():
        print(f"[ERROR] Không tìm thấy file: {cmd[-1]} → disable task {name}")
        send_error_email(name, "FileNotFound: script không tồn tại", "", "")
        disable_task(name)
        return

    try:
        completed = subprocess.run(
            cmd,
            check=True,
            text=True,
            capture_output=False,
            cwd=str(SCRIPT_DIR)  # đảm bảo cwd ổn định
        )

    except subprocess.CalledProcessError as e:
        err_summary = f"CalledProcessError: returncode={e.returncode}"
        print(f"[ERROR] {name} failed: {err_summary} → disable task {name}")
        send_error_email(name, err_summary, e.stdout or "", e.stderr or "")
        disable_task(name)

    except Exception as e:
        err_summary = f"Unexpected error: {type(e).__name__}: {e}"
        print(f"[ERROR] {name} failed: {err_summary} → disable task {name}")
        send_error_email(name, err_summary, "", traceback.format_exc())
        disable_task(name)

def main_loop():
    while True:
        active = [t for t in TASKS if t["enabled"]]
        if not active:
            print("[INFO] Không còn task nào đang bật. Dừng vòng lặp.")
            break

        for task in active:
            if task["enabled"]:
                run_task_once(task)
                time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    try:
        import sys
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    main_loop()
