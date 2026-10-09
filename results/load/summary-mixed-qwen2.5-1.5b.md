# Load test summary: mixed · qwen2.5:1.5b

Runs pooled: 3 (load-mixed-qwen2.5-1.5b-r1, load-mixed-qwen2.5-1.5b-r2, load-mixed-qwen2.5-1.5b-r3)

## Per run

| Run | Request | n | errors | p50 s | p95 s | p99 s | mean s | max s |
|---|---|---|---|---|---|---|---|---|
| load-mixed-qwen2.5-1.5b-r1 | POST /tickets | 24 | 1 | 2.66 | 4.57 | 5.16 | 2.70 | 5.30 |
| load-mixed-qwen2.5-1.5b-r1 | GET /search | 71 | 0 | 0.02 | 0.86 | 2.87 | 0.16 | 2.96 |
| load-mixed-qwen2.5-1.5b-r1 | GET /stats | 152 | 0 | 0.02 | 0.43 | 1.68 | 0.10 | 2.48 |
| load-mixed-qwen2.5-1.5b-r2 | POST /tickets | 24 | 1 | 2.61 | 4.81 | 4.87 | 2.73 | 4.87 |
| load-mixed-qwen2.5-1.5b-r2 | GET /search | 71 | 0 | 0.02 | 1.52 | 2.24 | 0.16 | 2.27 |
| load-mixed-qwen2.5-1.5b-r2 | GET /stats | 152 | 0 | 0.02 | 0.15 | 1.54 | 0.09 | 2.81 |
| load-mixed-qwen2.5-1.5b-r3 | POST /tickets | 24 | 1 | 3.00 | 4.62 | 4.81 | 2.80 | 4.81 |
| load-mixed-qwen2.5-1.5b-r3 | GET /search | 71 | 0 | 0.02 | 0.06 | 0.20 | 0.03 | 0.49 |
| load-mixed-qwen2.5-1.5b-r3 | GET /stats | 152 | 0 | 0.02 | 0.07 | 1.33 | 0.07 | 2.36 |

## Pooled over all runs

| Request | n | errors | error % | p50 s | p95 s | p99 s | mean s | max s |
|---|---|---|---|---|---|---|---|---|
| POST /tickets | 72 | 3 | 4.2 | 2.84 | 4.80 | 5.00 | 2.74 | 5.30 |
| GET /search | 213 | 0 | 0.0 | 0.02 | 0.09 | 2.26 | 0.12 | 2.96 |
| GET /stats | 456 | 0 | 0.0 | 0.02 | 0.16 | 1.68 | 0.09 | 2.81 |

## Spread across runs (per-run values)

| Request | metric | mean | min | max | stdev |
|---|---|---|---|---|---|
| POST /tickets | p50 s | 2.76 | 2.61 | 3.00 | 0.21 |
| POST /tickets | p95 s | 4.67 | 4.57 | 4.81 | 0.13 |
| POST /tickets | p99 s | 4.94 | 4.81 | 5.16 | 0.19 |
| GET /search | p50 s | 0.02 | 0.02 | 0.02 | 0.00 |
| GET /search | p95 s | 0.81 | 0.06 | 1.52 | 0.73 |
| GET /search | p99 s | 1.77 | 0.20 | 2.87 | 1.40 |
| GET /stats | p50 s | 0.02 | 0.02 | 0.02 | 0.00 |
| GET /stats | p95 s | 0.22 | 0.07 | 0.43 | 0.19 |
| GET /stats | p99 s | 1.51 | 1.33 | 1.68 | 0.18 |

## Verdicts (pooled)

- **R1** POST p95 ≤ 15 s and p99 ≤ 30 s: p95 4.80 s, p99 5.00 s, **PASS**
- **R3** GET /search p95 ≤ 1 s: p95 0.09 s, **PASS**

## Reconciliation with the service log

- load-mixed-qwen2.5-1.5b-r1: 247 JMeter requests; 0 missing in the service log; 0 status mismatches; 0 service-log entries not in the JTL; POST time before the service started handling it (queueing): mean 0.01 s, p95 0.01 s, max 0.02 s
- load-mixed-qwen2.5-1.5b-r2: 247 JMeter requests; 0 missing in the service log; 0 status mismatches; 0 service-log entries not in the JTL; POST time before the service started handling it (queueing): mean 0.01 s, p95 0.02 s, max 0.02 s
- load-mixed-qwen2.5-1.5b-r3: 247 JMeter requests; 0 missing in the service log; 0 status mismatches; 0 service-log entries not in the JTL; POST time before the service started handling it (queueing): mean 0.11 s, p95 0.76 s, max 1.23 s
