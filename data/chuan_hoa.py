import os
import re

folder = r"D:\CHAT BOT TTCS\data"

for filename in os.listdir(folder):
    if filename.endswith(".txt"):
        path = os.path.join(folder, filename)

        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        # Xóa "Đoạn x", "[Đoạn x]", "Đoạn x:" ...
        cleaned = re.sub(r"Đoạn\s*\d+\s*[:\]]*\s*", "", text)

        # Xóa dấu ngoặc [] nếu còn sót
        cleaned = re.sub(r"\[+", "", cleaned)

        with open(path, "w", encoding="utf-8") as f:
            f.write(cleaned)

        print("Đã làm sạch:", filename)
