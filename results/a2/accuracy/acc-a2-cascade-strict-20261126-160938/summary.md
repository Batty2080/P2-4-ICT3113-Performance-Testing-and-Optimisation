# A2 accuracy: cascade-strict

Run `acc-a2-cascade-strict-20261126-160938` · 2026-11-26T16:11:13+08:00 → 2026-11-26T16:27:48+08:00 · test set (`golden_set/test.csv`, 75 even rows)

Rule: qwen2.5:1.5b first; accept its answer if it predicts Bank account or service, Money transfer or service, Mortgage; otherwise escalate to qwen2.5:7b (`docs/a2/CASCADE_A2.md`).

- **Overall: 59/75 = 78.7%**, limit 53/75 (70.0%) → **PASS** (qwen2.5:7b alone: 60/75 = 80.0%)
- Per-category limit: **PASS**
- **Configuration: PASSES both accuracy limits**
- Errors / invalid answers: 0

## Per category

| Category | Cascade | 7b alone | Min to pass | Result | Note |
|---|---|---|---|---|---|
| Credit reporting | 15/16 = 93.8% | 15/16 | 13/16 | PASS |  |
| Debt collection | 9/10 = 90.0% | 9/10 | 8/10 | PASS |  |
| Mortgage | 8/13 = 61.5% | 8/13 | 7/13 | PASS |  |
| Credit card | 4/7 = 57.1% | 4/7 | 3/7 | PASS | small category (7 tickets): 2 more wrong would fail |
| Bank account or service | 6/8 = 75.0% | 7/8 | 6/8 | PASS | small category (8 tickets): 1 more wrong would fail |
| Consumer loan | 6/8 = 75.0% | 6/8 | 5/8 | PASS | small category (8 tickets): 2 more wrong would fail |
| Money transfer or service | 11/13 = 84.6% | 11/13 | 10/13 | PASS |  |

## Escalation (from the service log)

- Escalated to qwen2.5:7b: **66/75 = 88.0%**  (reasons: category_not_accepted 65, invalid_small_output 1)
- Escalated tickets correct: 51/66 = 77.3%
- Not escalated (1.5b answer accepted) correct: 8/9 = 88.9% → 1 wrong answers slipped through
- Of the escalated tickets, the 1.5b's own answer was wrong on 42/66 (the rule caught these)

## Confusion matrix (rows: golden label; columns: cascade answer)

| Golden \ Predicted | Credit reporting | Debt collection | Mortgage | Credit card | Bank account or service | Consumer loan | Money transfer or service | ERROR |
|---|---|---|---|---|---|---|---|---|
| Credit reporting | 15 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| Debt collection | 1 | 9 | 0 | 0 | 0 | 0 | 0 | 0 |
| Mortgage | 2 | 0 | 8 | 0 | 1 | 2 | 0 | 0 |
| Credit card | 2 | 0 | 0 | 4 | 1 | 0 | 0 | 0 |
| Bank account or service | 0 | 0 | 0 | 1 | 6 | 0 | 1 | 0 |
| Consumer loan | 1 | 1 | 0 | 0 | 0 | 6 | 0 | 0 |
| Money transfer or service | 0 | 0 | 0 | 1 | 1 | 0 | 11 | 0 |

## Checks

- Service log reconciliation: 0 problems
- 1.5b answers differing from its saved A1 answers: 0
- Final answers differing from what the saved A1 answers predict for this rule: 0
