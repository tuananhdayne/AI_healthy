import re
from datetime import datetime, timedelta
import dateparser

WEEKDAYS = {
    "thứ 2": 0, "thứ hai": 0,
    "thứ 3": 1, "thứ ba": 1,
    "thứ 4": 2, "thứ tư": 2,
    "thứ 5": 3, "thứ năm": 3,
    "thứ 6": 4, "thứ sáu": 4,
    "thứ 7": 5, "thứ bảy": 5,
    "chủ nhật": 6
}

class MedicineTimeParser:

    def parse(self, text):
        text = text.lower().strip()

        # ---------------------------
        # 1) EVERY DAY / DAILY
        # ---------------------------
        if "mỗi ngày" in text or "hàng ngày" in text:
            time = self.extract_time(text)
            return {
                "type": "repeat",
                "repeat": "daily",
                "time": time
            }

        # ---------------------------
        # 2) WEEKLY (THỨ 2, THỨ 6…)
        # ---------------------------
        for weekday_name, weekday in WEEKDAYS.items():
            if weekday_name in text:
                time = self.extract_time(text)
                return {
                    "type": "repeat",
                    "repeat": "weekly",
                    "weekday": weekday,
                    "time": time
                }

        # ---------------------------
        # 3) RELATIVE TIME ("2 tiếng nữa")
        # ---------------------------
        rel = re.search(r"(\d+)\s*(tiếng|giờ|phút)\s*nữa", text)
        if rel:
            value = int(rel.group(1))
            unit = rel.group(2)

            if unit == "phút":
                delta = timedelta(minutes=value)
            else:
                delta = timedelta(hours=value)

            target = datetime.now() + delta

            return {
                "type": "once",
                "datetime": target
            }

        # ---------------------------
        # 4) SPECIAL DAYS ("mai", "tối nay")
        # ---------------------------
        if "mai" in text:
            time = self.extract_time(text)
            date = datetime.now() + timedelta(days=1)
            target = datetime(date.year, date.month, date.day, time["hour"], time["minute"])

            return {
                "type": "once",
                "datetime": target
            }

        if "tối nay" in text:
            return {
                "type": "once",
                "datetime": datetime.now().replace(hour=20, minute=0)
            }

        # ---------------------------
        # 5) ABSOLUTE (8h, 20:30…)
        # ---------------------------
        time = self.extract_time(text)
        if time:
            today = datetime.now()
            target = datetime(today.year, today.month, today.day, time["hour"], time["minute"])
            return {
                "type": "once",
                "datetime": target
            }

        return None

    # -----------------------------------------------------
    # EXTRA: time extractor
    # -----------------------------------------------------
    def extract_time(self, text):
        # match 20:30
        match = re.search(r"(\d{1,2}):(\d{1,2})", text)
        if match:
            return {"hour": int(match.group(1)), "minute": int(match.group(2))}

        # match 8h, 8 giờ
        match = re.search(r"(\d{1,2})\s*(h|giờ)", text)
        if match:
            return {"hour": int(match.group(1)), "minute": 0}

        # default time
        return {"hour": 8, "minute": 0}
