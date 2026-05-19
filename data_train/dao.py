import pandas as pd

input_path = r"D:\TRAIN MODEL\data\data_2.csv"
output_path = r"D:\TRAIN MODEL\data\data_shuffled2.csv"

df = pd.read_csv(input_path)

# SHUFFLE
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

df.to_csv(output_path, index=False)
print("Done! Saved to:", output_path)
