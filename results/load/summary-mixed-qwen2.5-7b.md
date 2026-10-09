# Load test summary: mixed · qwen2.5:7b

Runs pooled: 3 (load-mixed-qwen2.5-7b-r1, load-mixed-qwen2.5-7b-r2, load-mixed-qwen2.5-7b-r3)

## Per run

| Run | Request | n | errors | p50 s | p95 s | p99 s | mean s | max s |
|---|---|---|---|---|---|---|---|---|
| load-mixed-qwen2.5-7b-r1 | POST /tickets | 24 | 0 | 11.94 | 29.75 | 33.34 | 12.72 | 33.88 |
| load-mixed-qwen2.5-7b-r1 | GET /search | 71 | 0 | 0.02 | 11.47 | 27.94 | 2.39 | 29.77 |
| load-mixed-qwen2.5-7b-r1 | GET /stats | 152 | 0 | 0.02 | 10.80 | 15.36 | 1.72 | 24.95 |
| load-mixed-qwen2.5-7b-r2 | POST /tickets | 24 | 0 | 12.58 | 18.51 | 21.83 | 12.47 | 22.80 |
| load-mixed-qwen2.5-7b-r2 | GET /search | 71 | 0 | 0.03 | 12.34 | 15.67 | 2.32 | 16.48 |
| load-mixed-qwen2.5-7b-r2 | GET /stats | 152 | 0 | 0.02 | 11.91 | 16.05 | 1.78 | 16.90 |
| load-mixed-qwen2.5-7b-r3 | POST /tickets | 24 | 0 | 12.80 | 24.72 | 35.69 | 13.33 | 38.69 |
| load-mixed-qwen2.5-7b-r3 | GET /search | 71 | 0 | 0.03 | 13.38 | 18.16 | 1.80 | 21.43 |
| load-mixed-qwen2.5-7b-r3 | GET /stats | 152 | 0 | 0.02 | 8.19 | 14.66 | 1.23 | 15.89 |

## Pooled over all runs

| Request | n | errors | error % | p50 s | p95 s | p99 s | mean s | max s |
|---|---|---|---|---|---|---|---|---|
| POST /tickets | 72 | 0 | 0.0 | 12.46 | 24.09 | 35.28 | 12.84 | 38.69 |
| GET /search | 213 | 0 | 0.0 | 0.02 | 12.69 | 20.87 | 2.17 | 29.77 |
| GET /stats | 456 | 0 | 0.0 | 0.02 | 11.42 | 15.50 | 1.58 | 24.95 |

## Spread across runs (per-run values)

| Request | metric | mean | min | max | stdev |
|---|---|---|---|---|---|
| POST /tickets | p50 s | 12.44 | 11.94 | 12.80 | 0.45 |
| POST /tickets | p95 s | 24.33 | 18.51 | 29.75 | 5.63 |
| POST /tickets | p99 s | 30.28 | 21.83 | 35.69 | 7.42 |
| GET /search | p50 s | 0.02 | 0.02 | 0.03 | 0.00 |
| GET /search | p95 s | 12.40 | 11.47 | 13.38 | 0.96 |
| GET /search | p99 s | 20.59 | 15.67 | 27.94 | 6.48 |
| GET /stats | p50 s | 0.02 | 0.02 | 0.02 | 0.00 |
| GET /stats | p95 s | 10.30 | 8.19 | 11.91 | 1.91 |
| GET /stats | p99 s | 15.36 | 14.66 | 16.05 | 0.70 |

## Verdicts (pooled)

- **R1** POST p95 ≤ 15 s and p99 ≤ 30 s: p95 24.09 s, p99 35.28 s, **FAIL**
- **R3** GET /search p95 ≤ 1 s: p95 12.69 s, **FAIL**

## Reconciliation with the service log

- load-mixed-qwen2.5-7b-r1: 247 JMeter requests; 0 missing in the service log; 0 status mismatches; 0 service-log entries not in the JTL; POST time before the service started handling it (queueing): mean 1.68 s, p95 9.14 s, max 27.93 s
- load-mixed-qwen2.5-7b-r2: 247 JMeter requests; 0 missing in the service log; 0 status mismatches; 0 service-log entries not in the JTL; POST time before the service started handling it (queueing): mean 1.75 s, p95 10.51 s, max 12.55 s
- load-mixed-qwen2.5-7b-r3: 247 JMeter requests; 0 missing in the service log; 0 status mismatches; 0 service-log entries not in the JTL; POST time before the service started handling it (queueing): mean 1.79 s, p95 8.72 s, max 14.37 s
