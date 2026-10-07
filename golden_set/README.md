# Golden Test Set (Step 1)

A hand-labelled answer key of **150 tickets** (team rows **4000–4149**), used to measure each candidate model's classification accuracy.

## Method

1. **Protocol first.** Category definitions and edge case rules were written before any labelling (`protocol.md`, version 1).
2. **Independent labelling.** Beatrice and Darren each labelled all 150 tickets separately, without conferring (`labels_beatrice.csv`, `labels_darren.csv`).
3. **Agreement measured.** Cohen's kappa was calculated on the two independent label sets (see below).
4. **Disagreements resolved.** All 43 disagreements were discussed and resolved, with each person's reasoning, who changed their label and why, and the final label recorded (`disagreement_log.csv`).
5. **Protocol revised.** Gaps revealed by disagreements were turned into rules P1–P12 (`protocol.md`, version 2).
6. **Frozen.** The final labels (`golden_set.csv`) were committed before any benchmark run.

## Inter-annotator agreement

| Measure | Value |
|---|---|
| Tickets compared | 150 |
| Observed agreement (Po) | 0.7133 (107 / 150) |
| Agreement expected by chance (Pe) | 0.1480 |
| **Cohen's kappa (κ)** | **0.66** (substantial agreement, Landis & Koch) |
| Disagreements | 43 |

Most common confusions: Bank account ↔ Money transfer (9), Credit reporting ↔ Debt collection (7), Bank account ↔ Credit card (6).

Reproduce it with:

```
python compute_kappa.py labels_beatrice.csv labels_darren.csv
```

The label files are kept **exactly as entered** by each labeller. Label spelling (capitalisation and spaces) is normalised only inside `compute_kappa.py` when comparing.

## Files

| File | Contents |
|---|---|
| `protocol.md` | Category definitions, edge case rules, revisions P1–P12, revision history |
| `protocol_questions.csv` | Full wording of each protocol question (P1–P12), both options considered, the decision and the rows it affected |
| `labels_beatrice.csv` | Beatrice's independent labels (`row,label`) |
| `labels_darren.csv` | Darren's independent labels (`row,label`) |
| `compute_kappa.py` | Recomputes the agreement statistic |
| `disagreement_log.csv` | All 43 disagreements: both labels, reasoning, protocol rule, who changed and why, final label |
| `golden_set.csv` | **Final labels** (`row,label`) for all 150 tickets; the frozen answer key |

Rows refer to the row numbers in the course dataset CSV.
