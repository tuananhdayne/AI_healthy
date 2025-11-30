"""
Scheduled task để kiểm tra và gửi thông báo nhắc nhở uống thuốc
Chạy định kỳ mỗi phút: python medicine_reminder_scheduler.py
Hoặc dùng cron/scheduler để chạy tự động
"""

import requests
import time
from datetime import datetime

# URL của API server
API_BASE_URL = "http://localhost:8000"


def check_and_send_reminders():
    """Kiểm tra và gửi thông báo nhắc nhở"""
    try:
        response = requests.post(f"{API_BASE_URL}/api/medicine-reminders/check")
        if response.status_code == 200:
            data = response.json()
            sent_count = data.get("sent", 0)
            if sent_count > 0:
                print(f"✅ Đã gửi {sent_count} thông báo nhắc nhở")
            return True
        else:
            print(f"❌ Lỗi khi kiểm tra reminders: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Lỗi khi gọi API: {e}")
        return False


def main():
    """Chạy scheduler liên tục"""
    print("🔔 Medicine Reminder Scheduler đã khởi động")
    print(f"⏰ Kiểm tra mỗi 60 giây...")
    print(f"🌐 API Server: {API_BASE_URL}")
    print("Nhấn Ctrl+C để dừng\n")

    while True:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] Đang kiểm tra reminders...")
            check_and_send_reminders()
            time.sleep(60)  # Chờ 60 giây trước khi kiểm tra lại
        except KeyboardInterrupt:
            print("\n👋 Đã dừng scheduler")
            break
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()

