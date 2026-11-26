# Assignment 2 cascade implementation

This patch implements Person 2's category-based cascade in the existing POST /tickets endpoint. It includes two fixed settings, reproducible tuning evidence, and request logs. It does not run formal accuracy or speed tests or make the team's final recommendation.

## Pair and rule

Small model: qwen2.5:1.5b. Large model: qwen2.5:7b. Use the existing models.lock.json digests. Memory feasibility evidence: results/a2/memory_check_20261125-184905.txt on the original host, both models resident and CPU-only, with 6 CPUs and approximately 15.48 GiB Docker memory.

Every valid ticket goes to the small model first. Accept its answer only if its predicted category is on the selected list. Otherwise call the large model and use the large answer. No original dataset label is available to the runtime rule.

| Predicted category | strict | relaxed |
|---|---|---|
| Mortgage | Accept | Accept |
| Bank account or service | Accept | Accept |
| Money transfer or service | Accept | Accept |
| Debt collection | Escalate | Accept |
| Consumer loan | Escalate | Accept |
| Credit reporting | Escalate | Escalate |
| Credit card | Escalate | Escalate |

Strict uses the categories with 100% observed precision on tuning predictions. Support is only 6, 3 and 1 predictions respectively; those percentages are uncertain. Relaxed additionally accepts Debt collection (1/2) and Consumer loan (3/8), trading more accepted errors for fewer large-model calls. These settings were selected using tuning rows only. The team should review/adopt and commit this rule before held-out testing; no test-set result was used to select it.

Malformed/unrecognised small-model output escalates with reason invalid_small_output. A transport failure or timeout returns an error, with no retry. Invalid large-model output or a large-model request failure also returns an error and stores no ticket. No fallback to the rejected small answer occurs.

## Tuning evidence

Run from the repository root:

```powershell
py scripts/analyse_cascade_tuning.py
```

The script filters both saved A1 prediction files to the 75 odd tuning rows, checks their labels, and writes results/a2/cascade_tuning.json with source hashes. It never scores test.csv. This is a simulation from saved single-model predictions, not a measured cascade run or an accuracy pass/fail decision.

| Setting | Correct | Wrong accepted | Escalated |
|---|---|---|---|
| strict | 56/75 (74.7%) | 0/10 | 65/75 (86.7%) |
| relaxed | 53/75 (70.7%) | 6/20 | 55/75 (73.3%) |

7B alone: 55/75. Relaxed reduces Debt collection tuning correctness from 5/6 to 3/6. Its test-set per-category performance is unknown and must be reported even if it fails. Neither setting is promised to improve speed: the small-model cost applies to every ticket and escalation remains frequent.

## Apply the patch

Copy this archive's contents into the existing project root. It replaces service/app.py and compose.yaml and adds this guide, a tuning analysis script/output, a mock test file, and a configuration example. No existing .env, prompt, model lock, golden labels, predictions, raw logs, database, or JMeter plan is included/replaced.

Merge these values into the existing .env (do not remove other settings):

```text
TRIAGE_MODE=cascade
CASCADE_SETTING=strict
RUN_ID=a2-development-strict
```

Then rebuild on the development or hosting machine:

```powershell
docker compose up -d --build triage
docker compose logs --tail 30 triage
```

To select the other setting, change CASCADE_SETTING to relaxed and use a new RUN_ID, then run docker compose up -d triage. A plain docker compose restart does not apply environment changes.

For a single-model configuration:

```text
TRIAGE_MODE=single
OLLAMA_MODEL=qwen2.5:7b
RUN_ID=a2-development-single7b
```

Use llama3.2:3b or qwen2.5:1.5b for the other single-model cases. Apply with docker compose up -d triage. Default TRIAGE_MODE is single for compatibility with the existing service. The A1 helper scripts do not set TRIAGE_MODE: explicitly use single when running those scripts. Do not use their full-golden-set scoring or old load schedules as the A2 procedure.

## API and logs

POST /tickets still accepts {"narrative": "..."}, returns one category and the same JSON field names, and stores one ticket after successful classification. In cascade mode, the public model field (also stored in SQLite/search results) is cascade-strict or cascade-relaxed. It does not reveal which stage answered. In single mode it remains the model tag. final_model in the service log records the actual answering model.

Additional log fields:

- mode, cascade_setting: configuration used.
- small_prediction: validated small-model category, or null.
- escalated: routing decision to escalate, including a failed escalation attempt.
- escalation_reason: category_not_accepted or invalid_small_output, otherwise null.
- final_model: actual answering model, null if classification did not finish.
- model_calls: each attempted call, including model, category, duration_ms, load_duration_ms, prompt_eval_duration_ms, eval_duration_ms, and error class.
- model_ms: wall time for the entire classification sequence, including routing overhead.

Existing request IDs, prompt hash, narrative hash, HTTP status and errors remain. Filter POST /tickets by run_id when analysing. For successful-ticket escalation fraction, use escalated successful POSTs / all successful POSTs; separately report escalation attempts and failures across all submitted POSTs. Do not silently exclude errors or unfinished requests. model_calls records whether the large call was actually attempted.

The original 300-second model timeout becomes a shared approximate inference budget for cascade requests: the second read timeout is reduced by the first call's elapsed time. Connections have a separate 10-second timeout. This is not a queue-wait or end-to-end deadline. The existing 360-second Gunicorn worker timeout remains. Very slow runs can still produce failures; retain and report them.

## Residency and fixed settings

All A2 calls, including single-model calls, use keep_alive=-1 to prevent idle expiry. This changes residency policy, not classification prompt, temperature, CPU mode, thread count, parallelism, or context length. Record it as the common A2 residency policy. Ollama docs: https://docs.ollama.com/faq (How do I keep a model loaded in memory).

Restart Ollama between runs as the A2 brief requires; otherwise previously used models remain resident. Warm up the configured model(s) on three fixed non-golden tickets per the test procedure. Direct large-model warm-up calls must also use keep_alive=-1. Before a cascade run, confirm ollama ps lists both models with 100% CPU. The code cannot guarantee residency under memory pressure: monitor ollama ps and recorded load durations. Repeat the check after a run. Keep CPU/RAM allocations and all inference settings fixed across configurations. No new classification cache is introduced.

Person 4 must adapt the A2 JMeter plan to the new S-based schedule, response timeout and final drain pause in the brief. The server's model timeout is distinct from the client's response timeout. Commit Person 3's predictions before formal tests. Report only test-set accuracy as final evidence; speed tests use fixed non-golden tickets.

## Local routing checks

These checks mock Ollama and use a temporary database; they do not contact any model or touch your development database:

```powershell
py -m pip install -r service/requirements.txt
py -m unittest discover -s tests -p test_cascade.py -v
```

Validated during patch creation: 8 tests passed (strict accept/escalate, relaxed accept, single mode, invalid small output, large timeout, transport failure, invalid input). The prompt, Dockerfile, Python requirements and model lock were byte-identical to the supplied ZIP. No real cascade inference, memory recheck, formal accuracy measurement or speed benchmark was performed by the assistant.


