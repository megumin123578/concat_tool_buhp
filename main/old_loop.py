# auto_runner.py
import os
import time
import subprocess
from datetime import datetime
from email.message import EmailMessage
import smtplib
import socket
import traceback

SLEEP_SECONDS = 30

TASKS = [
    ("be_ca.py",      ["python", "be_ca.py"]),
    ("bluey.py",      ["python", "bluey.py"]),
    ("spidey.py",     ["python", "spidey.py"]),
    ("maycay.py",     ["python", "maycay.py"]),
    ("findtoys.py",   ["python", "findtoys.py"]),
    ("bluey_funtoys.py", ["python", "bluey_funtoys.py"]),
]

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")    
SMTP_PASS = os.getenv("SMTP_PASS")     
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER or "")
EMAIL_TO = os.getenv("EMAIL_TO")       

MAX_BODY_CHARS = 15000  #max chars

def send_error_email(task_name: str, err_summary: str, stdout_text: str, stderr_text: str):
    """Gửi email khi lỗi."""
    if not (SMTP_USER and SMTP_PASS and EMAIL_FROM and EMAIL_TO):
        print("[WARN] Thiếu cấu hình SMTP/EMAIL_*, bỏ qua gửi email.")
        return

    hostname = socket.gethostname()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #shorten
    def _trim(s: str) -> str:
        if s is None:
            return ""
        s = s.strip()
        return (s[:MAX_BODY_CHARS] + "\n...[trimmed]") if len(s) > MAX_BODY_CHARS else s

    stdout_trim = _trim(stdout_text)
    stderr_trim = _trim(stderr_text)

    subject = f"[AutoRunner] Lỗi khi chạy {task_name} @ {now}"
    body = f"""\
Thời điểm : {now}
Máy      : {hostname}
Script   : {task_name}

Tóm tắt lỗi:
{err_summary}

=== STDOUT ===
{stdout_trim}

=== STDERR ===
{stderr_trim}
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

def run_task_once(task_name: str, cmd: list[str]):
    print(f"Running {task_name} ...")
    try:
        completed = subprocess.run(
            cmd,
            check=True,
            text=True,
            capture_output=True
        )

    except subprocess.CalledProcessError as e:
        # Lỗi do chương trình trả về mã khác 0
        err_summary = f"CalledProcessError: returncode={e.returncode}"
        stdout_text = e.stdout or ""
        stderr_text = e.stderr or ""
        print(f"[ERROR] {task_name} failed: {err_summary}")
        send_error_email(task_name, err_summary, stdout_text, stderr_text)
    except Exception as e:
        # Lỗi bất ngờ (ví dụ FileNotFoundError, OSError, TimeoutExpired nếu bạn dùng timeout)
        err_summary = f"Unexpected error: {type(e).__name__}: {e}"
        tb = traceback.format_exc()
        print(f"[ERROR] {task_name} failed: {err_summary}")
        send_error_email(task_name, err_summary, "", tb)



def main_loop():
    while True:

        for name, cmd in TASKS:
            run_task_once(name, cmd)
            time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    main_loop()
