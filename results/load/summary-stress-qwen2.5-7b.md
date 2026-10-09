# Load test summary: stress · qwen2.5:7b

Runs pooled: 1 (load-stress-qwen2.5-7b-r1)

## Per run

| Run | Request | n | errors | p50 s | p95 s | p99 s | mean s | max s |
|---|---|---|---|---|---|---|---|---|
| load-stress-qwen2.5-7b-r1 | POST /tickets | 282 | 32 | 82.65 | 330.00 | 330.00 | 127.40 | 330.00 |

## Pooled over all runs

| Request | n | errors | error % | p50 s | p95 s | p99 s | mean s | max s |
|---|---|---|---|---|---|---|---|---|
| POST /tickets | 282 | 32 | 11.3 | 82.65 | 330.00 | 330.00 | 127.40 | 330.00 |

## Stress steps (requests started in each step, first 30 s of each step ignored)

| Offered /h | n | errors | p50 s | p95 s | max s | median 1st half s | median 2nd half s | latency growing | p50 vs step 1 |
|---|---|---|---|---|---|---|---|---|---|
| 120 | 15 | 0 | 14.70 | 26.30 | 26.99 | 13.20 | 18.55 | no | 1.0× |
| 180 | 22 | 0 | 15.59 | 39.61 | 47.12 | 15.30 | 15.88 | no | 1.1× |
| 240 | 30 | 0 | 20.88 | 65.57 | 69.93 | 17.68 | 40.03 | YES | 1.4× |
| 300 | 33 | 0 | 64.97 | 95.20 | 106.91 | 88.20 | 29.41 | no | 4.4× |
| 360 | 44 | 0 | 46.06 | 85.84 | 97.96 | 35.85 | 72.28 | YES | 3.1× |
| 420 | 50 | 0 | 177.68 | 215.78 | 248.72 | 177.40 | 185.16 | no | 12.1× |
| 480 | 61 | 32 | 330.00 | 330.00 | 330.00 | 310.27 | 330.00 | no | 22.4× |

First step showing errors, growing latency within the step, or p50 > 3× step 1: **240** requests/hour.
(Indicative: a step is flagged when latency keeps rising during the step, so a queue is building.)

## Reconciliation with the service log

- load-stress-qwen2.5-7b-r1: 282 JMeter requests; 0 missing in the service log; 32 status mismatches; 0 service-log entries not in the JTL; POST time before the service started handling it (queueing): mean 116.02 s, p95 319.90 s, max 324.21 s
