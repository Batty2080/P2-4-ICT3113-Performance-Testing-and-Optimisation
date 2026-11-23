# Assignment 2 – Golden set split (Step 1)

Source: `golden_set.csv` (150 tickets, rows 4000–4149, frozen in Assignment 1). Labels unchanged.

Method: sorted by `row`. Odd rows → `tuning.csv`. Even rows → `test.csv`. Produced by `split.py`.

- **tuning.csv (75 tickets):** used only to design and adjust the escalation rule and choose its two settings.
- **test.csv (75 tickets):** used for every accuracy number reported in Assignment 2. No tuning on these.

Caveat: every model already ran on all 150 tickets in Assignment 1, so the test set is not new data. It gives a fair comparison of all configurations on the same tickets, with the cascade rule not tuned on them.

## Tickets per category

| Category | Golden | Tuning | Test |
|---|---|---|---|
| Bank account or service | 21 | 13 | 8 |
| Consumer loan | 17 | 9 | 8 |
| Credit card | 18 | 11 | 7 |
| Credit reporting | 31 | 15 | 16 |
| Debt collection | 16 | 6 | 10 |
| Money transfer or service | 23 | 10 | 13 |
| Mortgage | 24 | 11 | 13 |
| **Total** | **150** | **75** | **75** |

Small categories: Credit card (7), Bank account or service (8) and Consumer loan (8) have fewer than 10 test tickets, so one ticket moves their accuracy by 12.5 to 14.3 points. The per-category limit is not a fair test for these on its own.

## Accuracy limits

Top model: **qwen2.5:7b**. Scored on test.csv only, by `floors.py`, reusing its Assignment 1 accuracy run (`acc-qwen2.5-7b-20261009-035613`, `predictions.csv`). Same digest, prompt, Ollama version and machine, so it was not re-run.

**Overall:** 7B scores **60/75 = 80.0%** on the test set (vs 76.7% on the full golden set in A1). **Limit = 70.0%**, so a configuration needs **at least 53/75 correct** (52/75 = 69.3% fails).

| Category | 7B on test | Limit | Min correct to pass |
|---|---|---|---|
| Bank account or service | 7/8 = 87.5% | 72.5% | 6/8 |
| Consumer loan | 6/8 = 75.0% | 60.0% | 5/8 |
| Credit card | 4/7 = 57.1% | 42.1% | 3/7 |
| Credit reporting | 15/16 = 93.8% | 78.8% | 13/16 |
| Debt collection | 9/10 = 90.0% | 75.0% | 8/10 |
| Money transfer or service | 11/13 = 84.6% | 69.6% | 10/13 |
| Mortgage | 8/13 = 61.5% | 46.5% | 7/13 |

Per-category limit = 7B's test-set accuracy on that category minus 15 points. With 7 to 16 tickets per category, a configuration may pass or fail a category on a single ticket; this is stated alongside every per-category result.
