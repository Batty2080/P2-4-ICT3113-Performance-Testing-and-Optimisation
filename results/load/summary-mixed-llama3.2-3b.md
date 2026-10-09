# Load test summary: mixed · llama3.2:3b

Runs pooled: 3 (load-mixed-llama3.2-3b-r1, load-mixed-llama3.2-3b-r2, load-mixed-llama3.2-3b-r3)

## Per run

| Run | Request | n | errors | p50 s | p95 s | p99 s | mean s | max s |
|---|---|---|---|---|---|---|---|---|
| load-mixed-llama3.2-3b-r1 | POST /tickets | 24 | 0 | 5.65 | 8.20 | 9.89 | 5.47 | 10.36 |
| load-mixed-llama3.2-3b-r1 | GET /search | 71 | 0 | 0.02 | 4.44 | 4.80 | 0.46 | 4.87 |
| load-mixed-llama3.2-3b-r1 | GET /stats | 152 | 0 | 0.02 | 1.69 | 3.86 | 0.24 | 5.74 |
| load-mixed-llama3.2-3b-r2 | POST /tickets | 24 | 0 | 5.25 | 8.54 | 9.31 | 5.41 | 9.50 |
| load-mixed-llama3.2-3b-r2 | GET /search | 71 | 0 | 0.02 | 2.59 | 5.06 | 0.35 | 5.25 |
| load-mixed-llama3.2-3b-r2 | GET /stats | 152 | 0 | 0.02 | 3.00 | 5.91 | 0.36 | 6.63 |
| load-mixed-llama3.2-3b-r3 | POST /tickets | 24 | 0 | 5.18 | 8.84 | 9.48 | 5.25 | 9.63 |
| load-mixed-llama3.2-3b-r3 | GET /search | 71 | 0 | 0.02 | 1.88 | 7.12 | 0.37 | 7.22 |
| load-mixed-llama3.2-3b-r3 | GET /stats | 152 | 0 | 0.02 | 2.28 | 4.14 | 0.27 | 5.37 |

## Pooled over all runs

| Request | n | errors | error % | p50 s | p95 s | p99 s | mean s | max s |
|---|---|---|---|---|---|---|---|---|
| POST /tickets | 72 | 0 | 0.0 | 5.37 | 8.82 | 9.84 | 5.38 | 10.36 |
| GET /search | 213 | 0 | 0.0 | 0.02 | 3.16 | 5.21 | 0.39 | 7.22 |
| GET /stats | 456 | 0 | 0.0 | 0.02 | 2.35 | 5.22 | 0.29 | 6.63 |

## Spread across runs (per-run values)

| Request | metric | mean | min | max | stdev |
|---|---|---|---|---|---|
| POST /tickets | p50 s | 5.36 | 5.18 | 5.65 | 0.25 |
| POST /tickets | p95 s | 8.53 | 8.20 | 8.84 | 0.32 |
| POST /tickets | p99 s | 9.56 | 9.31 | 9.89 | 0.30 |
| GET /search | p50 s | 0.02 | 0.02 | 0.02 | 0.00 |
| GET /search | p95 s | 2.97 | 1.88 | 4.44 | 1.32 |
| GET /search | p99 s | 5.66 | 4.80 | 7.12 | 1.27 |
| GET /stats | p50 s | 0.02 | 0.02 | 0.02 | 0.00 |
| GET /stats | p95 s | 2.33 | 1.69 | 3.00 | 0.65 |
| GET /stats | p99 s | 4.64 | 3.86 | 5.91 | 1.11 |

## Verdicts (pooled)

- **R1** POST p95 ≤ 15 s and p99 ≤ 30 s: p95 8.82 s, p99 9.84 s, **PASS**
- **R3** GET /search p95 ≤ 1 s: p95 3.16 s, **FAIL**

## Reconciliation with the service log

- load-mixed-llama3.2-3b-r1: 247 JMeter requests; 0 missing in the service log; 0 status mismatches; 0 service-log entries not in the JTL; POST time before the service started handling it (queueing): mean 0.28 s, p95 2.33 s, max 3.70 s
- load-mixed-llama3.2-3b-r2: 247 JMeter requests; 0 missing in the service log; 0 status mismatches; 0 service-log entries not in the JTL; POST time before the service started handling it (queueing): mean 0.01 s, p95 0.01 s, max 0.02 s
- load-mixed-llama3.2-3b-r3: 247 JMeter requests; 0 missing in the service log; 0 status mismatches; 0 service-log entries not in the JTL; POST time before the service started handling it (queueing): mean 0.01 s, p95 0.02 s, max 0.02 s
