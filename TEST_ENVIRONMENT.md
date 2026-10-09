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

### Load tests (all on 9 Oct 2026; JMeter 5.6.3 on Machine B, service and Ollama on Machine A)

Conditions that were the same for every load run: Machine A on the Windows Balanced power plan and on AC power; the
Ollama container limited to 6 CPUs; the service, prompt and pinned models unchanged; each run started on an empty
database with a warm-up request (excluded); the Machine B command started within 5 minutes of the Machine A
preparation. The plan was changed once during the day (see the note below the table).

| Runs | Model | Time on 9 Oct (SGT) | Test plan version |
|---|---|---|---|
| Mixed load r1, r2, r3 (each 20 min arrivals) | qwen2.5:1.5b | r1 07:17–07:38, r2 08:36–08:57, r3 09:58–10:19 | without drain pause |
| Mixed load r1, r2, r3 | llama3.2:3b | r1 07:44–08:05, r2 09:01–09:22, r3 10:29–10:50 | without drain pause |
| Mixed load r1, r2, r3 | qwen2.5:7b | r1 08:10–08:31, r2 09:32–09:53, r3 10:57–11:18 | without drain pause |
| R2 r1, r2 (30 min arrivals) | qwen2.5:7b | r1 11:39–12:10, r2 12:12–12:43 | without drain pause |
| R2 r3 (excluded, see `results/load/EXCLUSIONS.md`) | qwen2.5:7b | 12:52–13:23 | without drain pause |
| Stress test (7 steps of 8 min, 120 to 480 per hour) | qwen2.5:7b | 14:16–15:26 | with 12 min drain pause |
| R2 r4 (replaces r3) | qwen2.5:7b | 15:47–16:20 | with 2 min drain pause |

Plan change: a schedule that simply ends makes JMeter interrupt requests still in flight, which cut off the last ticket
of R2 run 3. From the stress test onward every schedule ends with a drain pause (2 min for mixed and R2, 12 min for
stress). JMeter's logs show no interrupted request in any of the earlier runs. The mixed-load runs were done in rounds
(1.5B, 3B, 7B, then repeated) so that drift affects all models alike.

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
