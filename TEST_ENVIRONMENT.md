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

---

# Assignment 2 test environment

Source for A2 slide 3. Everything below was recorded on 25–26 November 2026; times are Singapore time (SGT).

## Machines: unchanged from Assignment 1

The same two machines as in Assignment 1 (table at the top of this file), with the same limits. Checked on 26 Nov 2026:

| Item | Assignment 2 | Same as A1? |
|---|---|---|
| Machine A (service + Ollama) | Lenovo 83DF, Intel Core i9-14900HX, 31.7 GB RAM, Windows 11 Pro build 26200 | Yes |
| Docker | Docker Desktop 29.5.3, ≈ 15.5 GiB memory available (`docker info`: 16,623,935,488 bytes) | Yes |
| Ollama | `ollama/ollama:0.40.0`, container limited to 6 CPUs, `OLLAMA_NUM_PARALLEL=1`, context 4096, temperature 0, `num_gpu: 0` (CPU only) | Yes |
| Models | Same tags and digests as `models.lock.json`; `scripts/check_pins.py` PASS before every A2 run (`logs/pin_check_202611*.txt`) | Yes |
| Classification prompt | `service/classification_prompt.txt`, unchanged since 5 Oct 2026 | Yes |
| Machine B (load generator) | Desktop PC, Apache JMeter 5.6.3, Java 25.0.4.1; a separate physical machine from Machine A | Yes |
| Power | Machine A on AC power, Windows Balanced power plan | Yes |
| Network | Machine A on wired Ethernet (1 Gbps, 192.168.18.104), same router and subnet as Machine B. **Wi-Fi switched off on Machine A for all A2 runs** (see below) | Yes (Wi-Fi off now stated explicitly) |

## Changes from Assignment 1

1. **Service:** `POST /tickets` can run a cascade (`docs/a2/CASCADE_A2.md`): `TRIAGE_MODE=single` (one model, as in A1) or `TRIAGE_MODE=cascade` with `CASCADE_SETTING=strict|relaxed`. The service log records `escalated`, `final_model` and each model call per ticket.
2. **Model residency:** every model call sends `keep_alive: -1`, so loaded models stay in memory for the whole run (in A1 Ollama unloaded a model after 5 idle minutes). Applied identically to every A2 configuration. Thread count, parallelism and context length are unchanged.
3. **Load profile:** POST /tickets only (no GET /search or GET /stats traffic), at the rate set from S (below), instead of the A1 workload mix.
4. **Workload tickets:** a fixed list of 40 tickets from rows 4150–4999 (outside the golden set), sent in the same order in every run (`results/a2/workload_tickets.md`).
5. **Arrival pattern:** the Open Model Thread Group uses a fixed random seed (3113), so every speed run receives the same arrival times.
6. **Per-run reset:** Ollama is restarted before every run (clears its memory and prompt cache), as the A2 brief requires.

## Arrival rate and run length (from S)

Measured on 26 Nov at 15:18 (`results/a2/s_measurement.txt`, `scripts/measure_s.py`): after an Ollama restart and three warm-up tickets (rows 4791, 4567, 4936), three different median-length tickets were sent to qwen2.5:7b one at a time.

| Row | Characters | Time |
|---|---|---|
| 4444 | 813 | 12.22 s |
| 4421 | 815 | **11.16 s (middle = S)** |
| 4987 | 816 | 9.21 s |

| Setting | Value |
|---|---|
| S | 11.16 s |
| Arrival rate | one ticket every 2 × S = 22.32 s on average = **161.3 tickets/hour** (open model, random arrivals) |
| Arrival period | S minutes = **670 s** |
| HTTP response timeout | max(10 × S, 5 min) = **5 min** |
| End-of-schedule pause (drain) | **6 min** (timeout + 1 min) |
| Comparison with the client | 161.3/h is **above** the A1 design peak of 72 tickets/hour |

## Procedure for each speed run

On Machine A: `python scripts/prepare_run_a2.py --config <config> --run-id a2-<config>-r<n>` (pin check, stop service, delete database, restart Ollama, start service in the configuration, 3 warm-up tickets plus, for a cascade, one direct call to qwen2.5:7b, check `ollama ps`, check GET /stats = 3). Then on Machine B: `.\jmeter\run_load_test.ps1 -Test a2 -Config <config> -Run <n>` (records GET /stats before and after). After JMeter finishes, on Machine A: the same prepare command with `--after` (records `ollama ps` and GET /stats). Evidence: `results/a2/load_prep/` (Machine A) and `results/a2/load/<run id>/` (Machine B).

## Conditions of each A2 run (all on 26 Nov 2026 unless stated)

| Run | When (SGT) | Notes |
|---|---|---|
| Memory check: qwen2.5:1.5b + qwen2.5:7b loaded together | 25 Nov, 18:49 | `results/a2/memory_check_20261125-184905.txt`; both resident, 6.1 GiB of 15.5 GiB |
| S measurement | 15:18 | See above |
| Accuracy test, cascade strict (75 test-set tickets) | 16:11–16:27 | `results/a2/accuracy/acc-a2-cascade-strict-20261126-160938/` |
| Accuracy test, cascade relaxed | 16:29–16:43 | `results/a2/accuracy/acc-a2-cascade-relaxed-20261126-162749/` |
| Practice run 1 (dry, not a result) | 17:51–17:55 | 1 connect timeout and 2 lost replies; see "Network finding" |
| Practice run 2 (dry, not a result) | 18:01–18:05 | After Wi-Fi off: 5 sent, 0 errors |
| single-7b r1 | 18:38–18:56 | Round 1 |
| cascade-strict r1 | 19:09–19:28 | Round 1 |
| cascade-relaxed r1 | 19:33–19:51 | Round 1 |
| single-7b r2 | 19:57–20:15 | Round 2 |
| cascade-strict r2 | 20:18–20:37 | Round 2 |
| cascade-relaxed r2 | 20:41–21:00 | Round 2; models ran ≈ 20–25% slower than in r1 for the first tickets (see below) |
| single-7b r3 | 21:04–21:22 | Round 3 |
| cascade-strict r3 | 21:25–21:44 | Round 3 |
| cascade-relaxed r3 | 22:08–22:26 | Round 3 |

Speed-run times are from Machine B's `run_info.json`. Every speed run: 30 tickets sent, 30 completed (GET /stats 3 → 33), 0 errors; `ollama ps` before and after each run shows the required model(s) loaded; the largest model `load_duration` inside any run was under 0.1 s (no reloads). The configurations were run in rotation (7b, strict, relaxed, repeated three times) so that drift over the evening affects all three alike.

## Network finding (practice runs)

In practice run 1 Machine A was connected to the network twice: by Ethernet (192.168.18.104) and by Wi-Fi (192.168.18.73) on the same subnet. JMeter recorded one connection timeout and two replies that never arrived (the service log shows those two tickets answered with HTTP 201 in 15–20 s). With Wi-Fi switched off, practice run 2 and all nine speed runs had no errors. Wi-Fi stayed off on Machine A for every A2 speed run.

## Factors that could make A2 measurements unrepresentative

In addition to the A1 factors above (laptop CPU, Docker on Windows, home network, background activity):

1. **Drift over the evening.** The nine runs took about four hours back to back. In cascade-relaxed r2 the same model calls took ≈ 20–25% longer than in r1 for the first tickets (identical routing, no reloads), and single-7b r3 averaged 13.5 s against 12.6–12.7 s in r1–r2. Likely causes are heat or background activity on the laptop. Mitigation: rotation of configurations, and three runs each, so the spread is visible.
2. **One arrival rate.** All speed results hold at 161.3 tickets/hour only (above the client's peak of 72/h). They do not show behaviour at higher rates.
3. **Small samples.** 30 requests per run, 90 per configuration; p95 is pooled over the 90.
4. **Same arrival pattern in every run.** The fixed seed makes runs directly comparable, but the three runs sample one arrival pattern, not three.
