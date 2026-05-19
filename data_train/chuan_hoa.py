import pandas as pd

PATH = r"D:\TRAIN MODEL\data\data_shuffled2.csv"

df = pd.read_csv(PATH)

# in danh sách intent
print("📌 Các intent có trong file:")
print(df["intent"].unique())

# đếm số lượng mỗi intent
counts = df["intent"].value_counts()

print("\n📊 Số câu của từng intent:")
print(counts)

print("\n🔢 Tổng số dòng:", len(df))
