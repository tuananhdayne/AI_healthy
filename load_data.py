import os

def load_documents(folder):
    """
    Đọc toàn bộ file .txt trong thư mục data và trả về danh sách các đoạn văn.
    Mỗi dòng = 1 đoạn.
    """
    documents = []
    
    for filename in os.listdir(folder):
        if filename.endswith(".txt"):
            file_path = os.path.join(folder, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.read().split("\n")
                for line in lines:
                    line = line.strip()
                    if line != "":
                        documents.append(line)
    
    return documents


if __name__ == "__main__":
    folder = r"D:\CHAT BOT TTCS\data"
    docs = load_documents(folder)
    print("Tổng số đoạn tìm thấy:", len(docs))
