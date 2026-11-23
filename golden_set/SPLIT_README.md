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

Small categories: Credit card (7), Bank account or service (8) and Consumer loan (8) have fewer than 10 test tickets, so one ticket moves their accuracy by 12.5 to 14.3 points. The per-category limit still applies to them, but a result decided by one or two tickets is weak evidence, so it is reported with that caveat.

## Accuracy limits

The accuracy limits derived from this test set are in `REQUIREMENTS_A2.md` (repo root), computed by `floors.py`.
