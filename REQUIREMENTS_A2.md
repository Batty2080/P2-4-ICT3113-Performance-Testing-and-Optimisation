# Assignment 2 – Revised requirements

The client has revised the requirements for Assignment 2. **Speed is now the primary concern.** A lower accuracy than the top Assignment 1 model is accepted, within the limits below. The Assignment 1 accuracy requirements (R4: 85% weighted accuracy, and 70% recall per category) **do not apply** in Assignment 2. See `REQUIREMENTS.md` for the Assignment 1 requirements.

Unchanged constraints: CPU-only Ollama on hardware the team controls, no hosted model APIs, and the same test machine (CPU and RAM) as Assignment 1.

## Goal

Recommend the **fastest configuration that passes both accuracy limits** on the test set, measured with the Assignment 1 test method.

## Accuracy limits

Reference (top model): **qwen2.5:7b**, the most accurate Assignment 1 model (115/150 on the full golden set).

Limits are derived from its accuracy on the **test set only** (`golden_set/test.csv`, even rows, 75 tickets), computed by `golden_set/floors.py` from its Assignment 1 accuracy run (`acc-qwen2.5-7b-20261009-035613`).

### Overall limit

7B on test set: **60/75 = 80.0%**. Limit = 80.0 − 10 = **70.0%**.
A configuration needs **at least 53/75 correct** (52/75 = 69.3% fails).

### Per-category limit

No category may be more than 15 points below the 7B's test-set accuracy on that category. A configuration must pass **every** category.

| Category | Test tickets | 7B on test | Limit | Min correct to pass |
|---|---|---|---|---|
| Bank account or service | 8 | 7/8 = 87.5% | 72.5% | 6/8 |
| Consumer loan | 8 | 6/8 = 75.0% | 60.0% | 5/8 |
| Credit card | 7 | 4/7 = 57.1% | 42.1% | 3/7 |
| Credit reporting | 16 | 15/16 = 93.8% | 78.8% | 13/16 |
| Debt collection | 10 | 9/10 = 90.0% | 75.0% | 8/10 |
| Money transfer or service | 13 | 11/13 = 84.6% | 69.6% | 10/13 |
| Mortgage | 13 | 8/13 = 61.5% | 46.5% | 7/13 |

### Small categories

Credit card (7), Bank account or service (8) and Consumer loan (8) have fewer than 10 test tickets, so one ticket moves accuracy by 12.5 to 14.3 points.

**The limit still applies to these categories.** A configuration below the minimum fails, the same as for any other category.

But with so few tickets, a pass or fail can come down to chance on one ticket. This note does not change any pass/fail decision. It is there so that anyone reading the results can see which passes and fails were close calls, as the brief requires. So for these three categories, every result is reported with:

- the count (for example 2/7), not just the percentage, and
- how many more correct answers it would have needed to pass, or how many fewer it would have needed to fail.

Example: *"Credit card: 2/7 (28.6%), FAIL. Needed 3/7. Only 7 tickets, so one more correct answer would have passed."*
