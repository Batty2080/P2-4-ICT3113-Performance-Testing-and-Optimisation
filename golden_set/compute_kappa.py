"""Compute Cohen's kappa between two independent label sheets.

Usage:
    python compute_kappa.py labels_beatrice.csv labels_darren.csv

Each CSV has two columns: row,label  (one line per golden-set ticket).
Label spelling is normalised (case and surrounding spaces) before comparison.
"""
import csv
import sys
from collections import Counter

CATEGORIES = {
    "credit reporting": "Credit reporting",
    "debt collection": "Debt collection",
    "mortgage": "Mortgage",
    "credit card": "Credit card",
    "bank account or service": "Bank account or service",
    "consumer loan": "Consumer loan",
    "money transfer or service": "Money transfer or service",
}


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return {int(float(r["row"])): CATEGORIES[r["label"].strip().lower()]
                for r in csv.DictReader(f) if r["label"].strip()}


a, b = load(sys.argv[1]), load(sys.argv[2])
rows = sorted(set(a) & set(b))
n = len(rows)

po = sum(a[r] == b[r] for r in rows) / n
ca, cb = Counter(a[r] for r in rows), Counter(b[r] for r in rows)
pe = sum((ca[c] / n) * (cb[c] / n) for c in CATEGORIES.values())
kappa = (po - pe) / (1 - pe)

print(f"Tickets compared: {n}")
print(f"Observed agreement Po = {po:.4f}")
print(f"Chance agreement   Pe = {pe:.4f}")
print(f"Cohen's kappa         = {kappa:.4f}")
print(f"Disagreements: {sum(a[r] != b[r] for r in rows)}")
