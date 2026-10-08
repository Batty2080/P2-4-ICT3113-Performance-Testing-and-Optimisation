# Test Environment (Step 5)

Team P2-4 · ICT3113 Assignment 1 · source for slide 7.

The conditions of each benchmark run are recorded under "Conditions of each run" below; add a row for the
load tests when they have been run.

## Machines

| | Machine A: system under test | Machine B: load generator |
|---|---|---|
| Role | Triage service (gunicorn/Flask) + SQLite + Ollama, in Docker | Apache JMeter only |
| Device | Lenovo 83DF laptop (Darren) | Desktop PC (Darren), Gigabyte B850M Eagle WiFi6E board |
| CPU | Intel Core i9-14900HX, 24 cores / 32 threads | AMD Ryzen 5 8400F, 6 cores / 12 threads, 4.20 GHz |
| RAM | 31.7 GB (Docker allowed ≈ 15.5 GB) | 32 GB (31.6 GB usable) |
| GPU | Not used (CPU-only inference; `num_gpu: 0`) | RTX 3070 Ti, not used |
| OS | Windows 11 Pro, build 26200 | Windows 11 Home 25H2, build 26200.9457 |
| Software | Docker Desktop 29.5.3 (Linux containers), Ollama 0.40.0 (`ollama/ollama:0.40.0`), Python 3.12 service image | Apache JMeter 5.6.3, Java 25.0.4.1 LTS (Oracle HotSpot 64-bit); JMeter 5.6.3 starts correctly on this Java version (checked 9 Oct 2026) |
| Network | Ethernet, 1 Gbps, 192.168.18.104 | Ethernet, 2.5 Gbps, 192.168.18.85 |
| Container limits | Ollama container limited to **6 CPUs** (`cpus: "6"`); service container unlimited | n/a |

**Load generator is a separate physical machine.** JMeter does not run on Machine A. No other test of ours runs on Machine A at the same time as a benchmark run, and the load generator is never co-hosted with it.

## Conditions of each run

| Run | When | Conditions on Machine A |
|---|---|---|
| Accuracy test, 3 models (`results/accuracy/acc-*`) | 9 Oct 2026, 03:34–04:25 | Windows **Balanced** power plan, on AC power. Classification accuracy does not depend on timing conditions; the per-ticket timings from this run are indicative only, not load-test evidence. |

## Network

Both machines are wired to the same home router (gateway 192.168.18.1) on the same 192.168.18.0/24 subnet, so
traffic is one hop through the router. Machine B reaches the service at `http://192.168.18.104:8000`
(verified from Machine B: `GET /stats` returns the category counts). ICMP ping from B to A is blocked by
Windows Firewall on A, so the network delay was measured as TCP connect time from B to `192.168.18.104:8000`
(20 attempts, idle service): **mean 2.0 ms, min 0.8 ms, max 14.8 ms**, a proxy for one round trip. Ollama's own port (11434) is published on localhost only and is not reachable from Machine B.

## Software configuration under test

- Service: Flask under gunicorn, **1 sync worker, 1 thread**; synchronous classification; no caching or queue.
- Ollama: `OLLAMA_NUM_PARALLEL=1`, temperature 0, model timeout 300 s.
- Models pinned by tag and digest in `models.lock.json`; `scripts/check_pins.py` is run at the start of every run.
- Every request is logged to `logs/requests.jsonl` with the run's `RUN_ID`.

## Factors that could make measurements unrepresentative

1. **Laptop hardware.** The i9-14900HX is a mobile chip with performance and efficiency cores. Long runs may
   thermally throttle, and results may drift with temperature. Mitigation: note the observed drift between runs.
2. **Power plan.** Machine A uses the Windows **Balanced** power plan, on AC power, for all runs (the plan is not changed
   between runs, so runs stay comparable). A performance plan might give slightly faster and steadier results.
3. **6-CPU limit is a stand-in.** The client's "commodity CPU servers" are not specified. The limit makes
   Machine A behave more like a 6-core server, but cache, memory bandwidth and clock speeds differ.
   Without the limit the same models ran about 3.5× faster in smoke tests.
4. **Docker overhead.** Containers run in Docker Desktop's Linux VM on Windows, which adds some overhead compared
   with bare-metal Linux.
5. **Home network.** Shared router and a single wired hop; other traffic on the home network is not controlled.
6. **Dataset.** Narratives are length-capped at 2,000 characters in the course extract; real tickets may be longer.
7. **Background load.** Windows services and everyday applications on Machine A are not shut down for runs, so background activity adds
   some noise to the timings. Mitigation: every load configuration is run three times and the spread across runs is reported.
8. **Small samples.** Short runs give few tickets per run; results are pooled over the three runs.

## How results scale to the client's deployment

- **CPU inference time scales roughly with core count and per-core speed.** If the client's server has fewer or
  slower cores than 6 effective cores, classification will take proportionally longer; per-ticket time scales
  roughly linearly with model size. The measured service times let the client estimate capacity as
  3600 ÷ mean service time tickets per hour per model.
- **The single-worker, single-request design does not change with hardware.** The bottleneck (Ollama processing one
  request at a time) and the head-of-line blocking of `/search` and `/stats` behind classification should
  carry over to any deployment of this baseline.
- **Absolute latencies will not carry over.** Treat our p95 values as indicative for a 6-core CPU server, not as
  guarantees for the client's hardware; the client should re-run the playbook on their own servers.
