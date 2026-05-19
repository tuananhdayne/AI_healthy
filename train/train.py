import os
import re
import numpy as np
import pandas as pd
import torch

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix

from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback
)

# =====================================
# 0) CONFIG
# =====================================

DATA_PATH = r"data/data_dao_moi.csv"   # <-- bạn sửa đường dẫn ở đây
MODEL_NAME = "vinai/phobert-base"
MAX_LEN = 128

OUTPUT_DIR = "intent_model"
SEED = 42

TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

assert abs((TRAIN_RATIO + VAL_RATIO + TEST_RATIO) - 1.0) < 1e-6

# =====================================
# 1) LOAD + CLEAN DATA
# =====================================

df = pd.read_csv(DATA_PATH)

assert "text" in df.columns and "intent" in df.columns, "CSV phải gồm cột: text,intent"

# basic clean
df["text"] = df["text"].astype(str).apply(lambda s: re.sub(r"\s+", " ", s).strip())
df["intent"] = df["intent"].astype(str).str.strip()

# drop empty
df = df[df["text"].str.len() > 0].copy()

# dedup exact duplicates text+intent
before = len(df)
df = df.drop_duplicates(subset=["text", "intent"]).reset_index(drop=True)
after = len(df)
print(f"🧹 Dedup: {before} -> {after} (removed {before-after})")

# label mapping
intents = sorted(df["intent"].unique())
label2id = {label: i for i, label in enumerate(intents)}
id2label = {i: label for label, i in label2id.items()}
df["label"] = df["intent"].map(label2id)

print("🔍 Found intents:", intents)
print("🔢 Mapping:", label2id)
print("\n📊 Counts by intent:\n", df["intent"].value_counts())

# =====================================
# 2) TRAIN / VAL / TEST SPLIT (STRATIFIED)
# =====================================

train_df, temp_df = train_test_split(
    df,
    test_size=(1.0 - TRAIN_RATIO),
    stratify=df["label"],
    random_state=SEED
)

# split temp into val/test
val_size_of_temp = VAL_RATIO / (VAL_RATIO + TEST_RATIO)
val_df, test_df = train_test_split(
    temp_df,
    test_size=(1.0 - val_size_of_temp),
    stratify=temp_df["label"],
    random_state=SEED
)

print(f"\n📘 Train: {len(train_df)}    📗 Val: {len(val_df)}    📕 Test: {len(test_df)}")

# =====================================
# 3) TOKENIZER + MODEL
# =====================================

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=len(intents),
    label2id=label2id,
    id2label=id2label
)

# =====================================
# 4) DATASET + TOKENIZE
# =====================================

def tokenize(batch):
    enc = tokenizer(
        batch["text"],
        truncation=True,
        padding="max_length",
        max_length=MAX_LEN
    )
    # PhoBERT doesn't use token_type_ids
    if "token_type_ids" in enc:
        enc.pop("token_type_ids")
    return enc

train_ds = Dataset.from_pandas(train_df[["text", "label"]]).map(tokenize, batched=True)
val_ds   = Dataset.from_pandas(val_df[["text", "label"]]).map(tokenize, batched=True)
test_ds  = Dataset.from_pandas(test_df[["text", "label"]]).map(tokenize, batched=True)

train_ds = train_ds.remove_columns(["text"])
val_ds   = val_ds.remove_columns(["text"])
test_ds  = test_ds.remove_columns(["text"])

train_ds.set_format("torch")
val_ds.set_format("torch")
test_ds.set_format("torch")

# =====================================
# 5) METRICS
# =====================================

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "f1_macro": f1_score(labels, preds, average="macro"),
        "f1_weighted": f1_score(labels, preds, average="weighted"),
    }

# =====================================
# 6) TRAINING CONFIG
# =====================================

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    learning_rate=2e-5,
    per_device_train_batch_size=32,
    per_device_eval_batch_size=32,
    num_train_epochs=10,
    warmup_ratio=0.1,
    weight_decay=0.01,

    evaluation_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,

    metric_for_best_model="f1_macro",
    greater_is_better=True,

    gradient_accumulation_steps=2,
    fp16=torch.cuda.is_available(),
    seed=SEED,
    logging_steps=50,

    # helps reduce overconfidence (good for intent + other)
    label_smoothing_factor=0.05
)

# =====================================
# 7) TRAINER
# =====================================

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    tokenizer=tokenizer,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=3)]
)

# =====================================
# 8) TRAIN
# =====================================

print("\n🚀 Training...")
trainer.train()

# =====================================
# 9) FINAL EVAL ON TEST
# =====================================

print("\n🧪 Evaluating on TEST...")
pred = trainer.predict(test_ds)
test_logits = pred.predictions
test_labels = pred.label_ids
test_preds = np.argmax(test_logits, axis=1)

print("\n✅ TEST metrics:")
print("Accuracy:", accuracy_score(test_labels, test_preds))
print("F1-macro:", f1_score(test_labels, test_preds, average="macro"))
print("F1-weighted:", f1_score(test_labels, test_preds, average="weighted"))

print("\n📄 Classification report (per intent):")
print(classification_report(test_labels, test_preds, target_names=[id2label[i] for i in range(len(intents))], digits=4))

print("\n🧩 Confusion matrix (rows=true, cols=pred):")
print(confusion_matrix(test_labels, test_preds))

# =====================================
# 10) SAVE
# =====================================

os.makedirs(OUTPUT_DIR, exist_ok=True)
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print("\n🎉 DONE! Model saved to:", OUTPUT_DIR)
print("👉 id2label =", id2label)
