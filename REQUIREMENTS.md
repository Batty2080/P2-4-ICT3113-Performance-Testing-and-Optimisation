# Performance and Accuracy Requirements (Step 4)

Team P2-4 · ICT3113 Assignment 1 · Committed before the first benchmark run.

All requirements are derived from the workload model in `Step3_Workload_Model.xlsx`
(see sheet **Slide3** for every number quoted below). Every requirement states a number,
a percentile where relevant, and the load condition under which it must hold.
All load tests are **open-loop** (JMeter Open Model Thread Group or Precise Throughput Timer),
**3 runs per configuration**, with the service database reset before each run and one
warm-up request (excluded) after the model is loaded. Each load requirement is judged on the requests of the
3 runs pooled together; per-run values and the spread across runs are also reported.

**Revision note (9 Oct 2026, before any benchmark run):** test durations were
shortened (R1 30 → 20 min, R2 60 → 30 min, R3 30 → 20 min) so that every configuration can be run three times
for all three models. R1 is now measured under the R3 mixed load, so one run per model yields both R1 and R3. This gives fewer tickets per run (≈ 24 POSTs in a 20-minute run at
72/h), which is why the percentiles are taken over the 3 pooled runs. The earlier version is in the git history.

## Workload figures used

| Quantity | Value | Source |
|---|---|---|
| Tickets per year | 160,940 | FCA firm-level complaints 2025 H2 (Barclays Bank UK) × 2 |
| Design peak day | 678 tickets | Busiest weekday × busiest month (CFPB, Bank of America 2024) |
| **Design peak hour** | **71.2 tickets/h → 72/h (0.020 req/s)** | Peak day × 70% in business hours ÷ 10 h × 1.5 peak-hour factor (estimate) |
| Off-peak hour (weekend) | 8.9 tickets/h | Weekend day ÷ 24 |
| Searches in peak hour | 214 /h | 3 searches per handled ticket (estimate) |
| GET /stats in peak hour | 458 /h | 38 dashboards refreshing every 5 min (estimate) |
| Surge hour (stress scenario) | 214 tickets/h | 3 × peak (estimate) – stress test only, not a requirement |

The workload model has a clear peak (peak hour ≈ 8× off-peak), so every requirement is set at the peak, not the average.

## Requirements

### R1 – Classification response time (POST /tickets)

> **p95 ≤ 15 s and p99 ≤ 30 s**, measured at the client (JMeter elapsed time),
> at an open-loop arrival rate of **72 tickets/hour** sustained for **20 minutes**
> while the service simultaneously receives the R3 search and stats load,
> using ticket narratives drawn in order from rows 4000–4999.

*Why:* 72/h is the design peak hour. Classification is synchronous, so the intake system waits for the
answer before routing. 15 s keeps routing effectively immediate relative to agent handling time (~20 min
per complaint) while acknowledging CPU-only inference. p99 bounds the tail so long tickets (p95 ≈ 450 tokens)
are not left waiting indefinitely.

### R2 – Sustained throughput

> The service must complete **≥ 110 tickets/hour** for **30 minutes** at an open-loop arrival rate of 110/h,
> with **error rate < 1%** (non-2xx responses) and **no queue build-up**: median latency in the last 10 minutes
> ≤ 1.5 × median latency in the first 10 minutes.

*Why:* 110/h is 1.5× the design peak, giving headroom for days busier than our two-week sample and for
growth. The "no build-up" clause distinguishes a system that keeps up from one whose queue grows slowly
(which open-loop testing exposes and closed-loop testing hides). The clause compares **medians**, not p95:
at 110/h a 10-minute window holds only ≈ 18 requests, so a p95 would just be the single longest ticket
(ticket lengths range from a few hundred to 2,000 characters) and could fail the test by chance. The median is
stable at that sample size, and a real queue build-up still shows up as a large rise in it.

### R3 – Search response time under mixed load (GET /search)

> **GET /search p95 ≤ 1 s**, while the service simultaneously receives the peak-hour mix:
> **72 POST /tickets + 214 GET /search + 458 GET /stats per hour** (open-loop, 20 minutes),
> with search terms drawn from a fixed list of 20 common complaint words.

*Why:* Agents search interactively while classification is running. A search that waits behind
classification would stall the people doing the work, so search must stay fast under realistic mixed load.

### R4 – Classification accuracy (measured on the golden test set)

> **Overall accuracy ≥ 85%**, computed as recall per category weighted by the expected real-world
> category mix below, **and recall ≥ 70% for every one of the 7 categories**,
> measured by sending every golden-set ticket through POST /tickets once per candidate model.
> A response that is an error or an invalid category counts as wrong.

| Category | Expected real share (CFPB, Bank of America 2024) |
|---|---|
| Bank account or service | 38.4% |
| Credit card | 23.6% |
| Credit reporting | 22.3% |
| Money transfer or service | 6.5% |
| Debt collection | 4.0% |
| Mortgage | 3.5% |
| Consumer loan | 1.7% |

Unweighted accuracy on the golden set is also reported.

*Why:* At the design peak day of 678 tickets, 85% accuracy still means ≈ 100 misrouted tickets per day
that an agent must spot and re-route. Weighting by the real mix measures what the client will actually
experience (the course extract is balanced at ~1/7 per category). The per-category floor stops a model
from looking good overall while effectively ignoring a rare category.

## Our position on the trade-off

The client has not said whether a misrouted ticket or a slow triage costs more. **We take the position
that a misroute costs more**: it consumes agent time, delays the customer and can breach complaint-handling
deadlines, whereas a classification that takes 10–15 s instead of 2 s is invisible to the customer.
Accuracy (R4) is therefore the requirement we weight most heavily, but latency must still hold at the peak
(R1), not merely on average.

## Pass/fail evidence

| Req | Evidence | Statistic |
|---|---|---|
| R1 | JMeter `.jtl` (elapsed) reconciled with `logs/requests.jsonl` (`duration_ms`) by `X-Request-ID` | p95, p99 over the 3 pooled runs (pass/fail); per run, with mean and spread across runs, also reported |
| R2 | `.jtl` + service log | completed/hour, error %, median first vs last 10 min |
| R3 | `.jtl` filtered to GET /search | p95 per run |
| R4 | service log `category` joined to `golden_set.csv` by row | per-category recall, weighted overall, confusion matrix |
