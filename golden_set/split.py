"""Assignment 2, Step 1: split the frozen golden set.

Sort by row number. Odd rows -> tuning set (design the escalation rule).
Even rows -> test set (every reported accuracy number).
Run from this folder: python split.py
"""
import pandas as pd

df = pd.read_csv("golden_set.csv").sort_values("row")
assert df["row"].is_unique, "duplicate row numbers in golden set"

tuning = df[df["row"] % 2 == 1]
test = df[df["row"] % 2 == 0]
tuning.to_csv("tuning.csv", index=False, lineterminator="\r\n")
test.to_csv("test.csv", index=False, lineterminator="\r\n")

print(f"golden: {len(df)}  tuning: {len(tuning)}  test: {len(test)}\n")
counts = pd.DataFrame({
    "golden": df["label"].value_counts(),
    "tuning": tuning["label"].value_counts(),
    "test": test["label"].value_counts(),
}).fillna(0).astype(int)
print(counts)
