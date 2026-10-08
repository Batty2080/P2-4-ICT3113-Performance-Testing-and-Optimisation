# Test Playbook (Step 5)

Team P2-4 · ICT3113 Assignment 1 · source for slide 8. Written so that a competent tester can repeat every test
without further information. Requirement numbers (R1–R4) refer to `REQUIREMENTS.md`; machines refer to
`TEST_ENVIRONMENT.md`.

| | Machine A: system under test (SUT) | Machine B: load generator |
|---|---|---|
| What runs | Docker: triage service + Ollama | Apache JMeter 5.6.3 (non-GUI) |
| Address | 192.168.18.104 (service on port 8000) | 192.168.18.85 |
| Repo copy | yes (service, scripts, logs) | yes (JMeter plan, run script, results) |

## 0. Rules that apply to every test

1. **Load tests are open-loop.** JMeter's *Open Model Thread Group* starts requests on a schedule (a fixed arrival
   rate with random arrival times), whether or not earlier requests have finished.
2. **The load generator never runs on Machine A.**
3. **One run = one model + one test.** The service runs one model at a time, chosen with `OLLAMA_MODEL`.
4. **Before every run** the service is restarted on an empty database, the pinned model digests are verified
   (`scripts/check_pins.py`, run for you by `scripts/prepare_run.py`), and one warm-up request is sent and excluded.
5. **Three runs per load configuration** (a configuration = a model under one test). Results are pooled over the
   three runs for the verdict; per-run values and their spread are also reported.
6. **Nothing is changed between runs** (service code, prompt, models, compose settings, Windows power plan).
   If anything has to change, repeat all affected runs.
7. **Never overwrite results.** Each run writes to its own folder `results/load/<run id>/`; a run that was aborted or
   went wrong is deleted from the report only with a note saying why, and repeated.
8. **Ticket data:** POST traffic uses the narratives of rows 4000–4999 in order (`jmeter/team_rows_bodies.tsv`),
   so every run starts again at row 4000 and every model sees the same tickets in the same order.
   Search terms come from a fixed list of 20 words (`jmeter/search_terms.csv`).

## 1. One-time setup

**Machine A (laptop)**
1. Docker Desktop running; `docker compose up -d ollama` and the three models pulled (see `README.md`).
2. `python scripts/check_pins.py` prints `RESULT: PASS`.
3. `team_rows_4000_4999.csv` exists (`python scripts/make_team_rows.py <course csv>` if not).

**Machine B (load generator)**
1. `git pull` the repo. Java is installed; JMeter 5.6.3 is unzipped next to the repo folder
   (`...\apache-jmeter-5.6.3`) or its location is passed with `-JMeterHome`.
2. `jmeter/team_rows_bodies.tsv` and `jmeter/search_terms.csv` are in the repo. To regenerate them:
   `python scripts/make_jmeter_data.py`.
3. Open `http://192.168.18.104:8000/stats` in a browser: it must show the category counts.
4. PowerShell may refuse to run scripts. Start the run script with
   `powershell -ExecutionPolicy Bypass -File .\jmeter\run_load_test.ps1 ...` as shown below.
5. Turn off anything that routes traffic differently between the two machines (for example a VPN) on both.

## 2. Load tests (JMeter): the procedure for one run

Run id format: `load-<test>-<model with : replaced by ->-r<run number>`, e.g. `load-mixed-qwen2.5-7b-r1`.

**On Machine A:**
```
python scripts/prepare_run.py --model qwen2.5:7b --run-id load-mixed-qwen2.5-7b-r1
```
It verifies the pins, stops the service, deletes the database, restarts the service with this model and run id,
and sends the warm-up request. It ends with `READY`.

**On Machine B** (repo folder):
```
powershell -ExecutionPolicy Bypass -File .\jmeter\run_load_test.ps1 -Test mixed -Model qwen2.5:7b -Run 1
```
The script checks the service is reachable and the database holds only the warm-up ticket, writes the settings to
`results\load\<run id>\run.properties`, and runs JMeter in non-GUI mode. When JMeter finishes it saves
`results.jtl` (every request), `jmeter.log`, `jmeter_stdout.txt` and `run_info.json` in that folder.

Add `-Dry` for a 2-minute rehearsal (run ids start with `dry-`; these are not results).

### The three tests

| Test (`-Test`) | Requirement | What JMeter sends | Duration |
|---|---|---|---|
| `mixed` | R1 and R3 | 72 `POST /tickets` + 214 `GET /search` + 458 `GET /stats` per hour, together | 20 min |
| `r2` | R2 | 110 `POST /tickets` per hour (nothing else) | 30 min |
| `stress` | stress test | `POST /tickets` stepped 120, 180, 240, 300, 360, 420, 480 per hour, 8 min per step, 10 s ramps between steps | about 57 min |

JMeter generates the expected number of arrivals (rounded down; observed in the rehearsals, for example 2 POSTs in
2 minutes at 72/h) at random times within the schedule. After the schedule ends JMeter waits for outstanding
responses (the client timeout is 330 s) before it stops.

### Run matrix

Run models in rounds, so that slow drift (temperature, background activity) affects every model alike:

| Order | Test | Model | Runs |
|---|---|---|---|
| 1 | `mixed` | qwen2.5:1.5b, llama3.2:3b, qwen2.5:7b (in this order) | round 1 |
| 2 | `mixed` | same three | round 2 |
| 3 | `mixed` | same three | round 3 |
| 4 | `r2` | qwen2.5:7b (slowest model: worst case) | 3 runs |
| 5 | `stress` | qwen2.5:7b | 1 run |
| 6 (if time) | `r2` | llama3.2:3b, qwen2.5:1.5b | 3 runs each |

Estimated wall-clock time per run, including preparation: `mixed` about 23 min, `r2` about 33 min, `stress` about 65 min.

### If something goes wrong
* `prepare_run.py` reports a pin mismatch, or the warm-up fails: do not start the test. Fix and prepare again.
* The run script refuses to start because the database is not empty: run `prepare_run.py` again.
* A run is interrupted (Ctrl+C, power loss, network drop): repeat that run from `prepare_run.py` under the same run
  id with `-Force`, after moving the old folder out of `results/load/`, and say so in the report.

## 3. After each run (or batch of runs)

1. Machine B: `git add results/load`, commit, push.
2. Machine A: `git pull --rebase` (to get the results), then:
   `python scripts/summarise_load.py results/load/<run id 1> results/load/<run id 2> results/load/<run id 3>`
   (all three runs of one test and one model). This reads `results.jtl` and `logs/requests.jsonl`,
   writes `results/load/summary-<test>-<model>.md/.json`, and reconciles every JMeter request with the service log.
3. Commit `results/load` and `logs/requests.jsonl` on Machine A, and push.

## 4. How results are judged

All statistics are computed from the raw `.jtl` files by `scripts/summarise_load.py`; percentiles use linear
interpolation. Pooled = the requests of the three runs combined.

* **R1** (mixed, pooled): `POST /tickets` p95 ≤ 15 s **and** p99 ≤ 30 s.
* **R3** (mixed, pooled): `GET /search` p95 ≤ 1 s.
* **R2** (r2, every run): completed ≥ 99% of sent and sent ≥ 98% of 110/h × 30 min; error rate < 1%; median latency
  in the last 10 minutes ≤ 1.5 × the median in the first 10 minutes.
* **Stress test:** requests are grouped by the step in which they started (the first 30 s of each step is ignored).
  The limit is the first step with errors, latency still rising inside the step, or a median more than 3× that of the
  first step. The queueing share of latency is read from the reconciliation (client time minus service time).
* **Throughput** is reported as requests sent and completed per hour; **error rate** as non-2xx or failed responses.

**Reconciliation.** Every JMeter request carries `X-Request-ID = <run id>-<post|search|stats>-<n>`; the service logs it
as `client_request_id`. The summary reports requests missing from the service log and status mismatches (both should
be 0), and the time a POST waited before the service started handling it (the single worker queues requests).

## 5. Accuracy test (R4), no JMeter

On Machine A, `python scripts/accuracy_test.py` (all three models, about 45 minutes) or `--models <tag>`.
For each model it verifies the pins, restarts the service on an empty database with run id
`acc-<model>-<timestamp>`, sends one warm-up request, then sends the 150 golden tickets one at a time through
`POST /tickets`, scores them against `golden_set/golden_set.csv` (an error or invalid answer counts as wrong), and
writes `results/accuracy/<run id>/` (predictions, confusion matrix, summary) after reconciling with the service log.
Weighted accuracy = per-category recall weighted by the real-world category mix in `REQUIREMENTS.md`.

## 6. Known limits of this procedure

* 20-minute mixed runs send only about 24 tickets per run (rows 4000–4023), so percentiles rest on the three pooled runs
  (about 72 requests, the same 24 tickets three times); the spread across runs shows system noise, not ticket variety.
* The warm-up ticket stays in the database during the run (one row).
* Step boundaries in the stress test are known to within a few seconds; the first 30 s of each step is ignored.
* Background activity on both machines is not controlled (see `TEST_ENVIRONMENT.md`).
