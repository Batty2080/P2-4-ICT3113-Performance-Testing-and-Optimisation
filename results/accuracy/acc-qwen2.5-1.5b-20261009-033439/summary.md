# Accuracy: qwen2.5:1.5b

Run `acc-qwen2.5-1.5b-20261009-033439` · 2026-10-09T03:34:51+08:00 → 2026-10-09T03:42:17+08:00

- Tickets: 150 · correct: 64 · errors/invalid: 1
- **Weighted accuracy (R4): 41.5%** (need ≥ 85%)
- Unweighted accuracy: 42.7%
- Categories below 70% recall: Debt collection, Mortgage, Credit card, Bank account or service, Consumer loan, Money transfer or service
- **R4: FAIL**
- Reconciliation with service log: 0 mismatched, 0 missing of 150 requests

| Category | Support | Recall | Precision |
|---|---|---|---|
| Credit reporting | 31 | 96.8% | 39.0% |
| Debt collection | 16 | 37.5% | 75.0% |
| Mortgage | 24 | 33.3% | 100.0% |
| Credit card | 18 | 33.3% | 18.8% |
| Bank account or service | 21 | 19.0% | 100.0% |
| Consumer loan | 17 | 23.5% | 30.8% |
| Money transfer or service | 23 | 26.1% | 85.7% |
