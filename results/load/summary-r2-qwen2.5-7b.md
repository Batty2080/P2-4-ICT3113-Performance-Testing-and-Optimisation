# Load test summary: r2 · qwen2.5:7b

Runs pooled: 3 (load-r2-qwen2.5-7b-r1, load-r2-qwen2.5-7b-r2, load-r2-qwen2.5-7b-r4)

## Per run

| Run | Request | n | errors | p50 s | p95 s | p99 s | mean s | max s |
|---|---|---|---|---|---|---|---|---|
| load-r2-qwen2.5-7b-r1 | POST /tickets | 55 | 0 | 12.23 | 20.64 | 24.35 | 12.18 | 27.36 |
| load-r2-qwen2.5-7b-r2 | POST /tickets | 55 | 0 | 12.23 | 28.76 | 32.53 | 14.10 | 33.14 |
| load-r2-qwen2.5-7b-r4 | POST /tickets | 55 | 0 | 11.65 | 23.82 | 25.96 | 12.81 | 27.10 |

## Pooled over all runs

| Request | n | errors | error % | p50 s | p95 s | p99 s | mean s | max s |
|---|---|---|---|---|---|---|---|---|
| POST /tickets | 165 | 0 | 0.0 | 11.68 | 24.73 | 30.02 | 13.03 | 33.14 |

## Spread across runs (per-run values)

| Request | metric | mean | min | max | stdev |
|---|---|---|---|---|---|
| POST /tickets | p50 s | 12.04 | 11.65 | 12.23 | 0.34 |
| POST /tickets | p95 s | 24.41 | 20.64 | 28.76 | 4.09 |
| POST /tickets | p99 s | 27.61 | 24.35 | 32.53 | 4.33 |

## R2 checks (per run)

| Run | sent | completed ok | offered /h | completed /h | error % | median first 10 min s | median last 10 min s | ratio | throughput | errors | no build-up |
|---|---|---|---|---|---|---|---|---|---|---|---|
| load-r2-qwen2.5-7b-r1 | 55 | 55 | 110.0 | 110.0 | 0.0 | 13.04 (n=13) | 9.69 (n=24) | 0.74 | PASS | PASS | PASS |
| load-r2-qwen2.5-7b-r2 | 55 | 55 | 110.0 | 110.0 | 0.0 | 13.23 (n=24) | 8.85 (n=16) | 0.67 | PASS | PASS | PASS |
| load-r2-qwen2.5-7b-r4 | 55 | 55 | 110.0 | 110.0 | 0.0 | 14.58 (n=19) | 10.52 (n=18) | 0.72 | PASS | PASS | PASS |

- **R2** (every run must pass all three checks): **PASS**
- Throughput check: completed ≥ 99% of sent, and sent ≥ 98% of 110/h × duration (JMeter rounds the arrival count down).

## Reconciliation with the service log

- load-r2-qwen2.5-7b-r1: 55 JMeter requests; 0 missing in the service log; 0 status mismatches; 0 service-log entries not in the JTL; POST time before the service started handling it (queueing): mean 1.60 s, p95 11.04 s, max 14.90 s
- load-r2-qwen2.5-7b-r2: 55 JMeter requests; 0 missing in the service log; 0 status mismatches; 0 service-log entries not in the JTL; POST time before the service started handling it (queueing): mean 3.44 s, p95 17.19 s, max 19.73 s
- load-r2-qwen2.5-7b-r4: 55 JMeter requests; 0 missing in the service log; 0 status mismatches; 0 service-log entries not in the JTL; POST time before the service started handling it (queueing): mean 2.33 s, p95 14.42 s, max 21.65 s
