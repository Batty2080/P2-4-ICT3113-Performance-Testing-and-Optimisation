"""Assignment 2, Step 1: accuracy limits from the top model on the test set.

Reuses the Assignment 1 accuracy-run records for qwen2.5:7b (same digest,
prompt, Ollama version and machine), scoring only the test-set rows.
Usage: python floors.py <path to qwen2.5:7b predictions.csv>
"""
import sys
import pandas as pd

OVERALL_MARGIN, CATEGORY_MARGIN = 10.0, 15.0

test = pd.read_csv("test.csv")
pred = pd.read_csv(sys.argv[1])[["row", "golden", "predicted"]]
df = test.merge(pred, on="row", how="left")

assert df["predicted"].notna().all(), "test rows missing from predictions file"
assert (df["label"] == df["golden"]).all(), "labels differ from frozen golden set"

df["correct"] = df["label"] == df["predicted"]
n, k = len(df), int(df["correct"].sum())
acc = 100 * k / n
print(f"Top model (qwen2.5:7b) on test set: {k}/{n} = {acc:.1f}%")
print(f"Overall limit: {acc:.1f} - {OVERALL_MARGIN:.0f} = {acc - OVERALL_MARGIN:.1f}%\n")

g = df.groupby("label")["correct"].agg(["sum", "count"])
g["acc"] = 100 * g["sum"] / g["count"]
g["limit"] = (g["acc"] - CATEGORY_MARGIN).clip(lower=0)
for cat, r in g.iterrows():
    print(f"{cat:28s} {int(r['sum']):2d}/{int(r['count']):2d} = {r['acc']:5.1f}%  "
          f"limit {r['limit']:5.1f}%  (1 ticket = {100 / r['count']:.1f} pts)")
