# ICT3113 Assignment 1 · Team P2-4 · Ticket Triage Service

A complaint-ticket classifier for a financial services client: **POST /tickets** classifies a ticket into one of
7 categories using a local LLM (Ollama, CPU only, no public model API), and the service stores it. This repository
holds the baseline service, the golden test set, the requirements and predictions, and the test tooling for
Assignment 1 (performance requirements and testing).

The baseline is deliberately naive: classification is **synchronous**, with **no caching or queueing**, one
gunicorn worker and one Ollama request at a time.

## Run the service

Prerequisites: Docker Desktop (Linux containers) and Python 3.

```
# 1. Start Ollama (CPU only, limited to 6 CPUs, see compose.yaml)
docker compose up -d ollama

# 2. Pull the three candidate models into the Ollama container (once)
docker compose exec ollama ollama pull qwen2.5:1.5b
docker compose exec ollama ollama pull llama3.2:3b
docker compose exec ollama ollama pull qwen2.5:7b

# 3. Start the triage service with one model (PowerShell; use `OLLAMA_MODEL=... docker compose up -d` on Linux/macOS)
$env:OLLAMA_MODEL="qwen2.5:1.5b"; $env:RUN_ID="my-run"; docker compose up -d --build triage
```

The service listens on port 8000. The model is chosen by `OLLAMA_MODEL` at startup; restart to switch models.

| Endpoint | What it does |
|---|---|
| `POST /tickets` with JSON `{"narrative": "..."}` | Classifies the ticket (synchronously), stores it, returns `201` with `id` and `category` |
| `GET /search?q=word` | Returns stored tickets whose narrative contains the text |
| `GET /stats` | Returns counts of stored tickets by category |

Every request is logged as one JSON line in `logs/requests.jsonl` (with `run_id`, `duration_ms`, `model_ms`, category,
and the caller's `X-Request-ID`). The SQLite database is `data/tickets.db` (not committed); delete it to reset the service.

## Repository map

| Path | What it is |
|---|---|
| `service/` | The triage service: Flask app, classification prompt, Dockerfile |
| `compose.yaml` | Ollama (pinned version, 6-CPU limit) + triage service |
| `golden_set/` | **Step 1**: labelling protocol, independent label sheets, disagreement log, final labels, agreement statistic (see its own README) |
| `Step3_Workload_Model.xlsx` | **Step 3**: workload model with cited sources |
| `REQUIREMENTS.md` | **Step 4**: performance and accuracy requirements R1–R4 |
| `PREDICTIONS.md` | **Step 4**: prediction record, written before any benchmark |
| `models.lock.json` | **Step 4**: candidate models pinned by tag and digest |
| `scripts/` | Tooling: `pin_models.py` (writes the lock file), `check_pins.py` (verifies the pins before every run), `make_team_rows.py`, `accuracy_test.py` |
| `TEST_ENVIRONMENT.md` | **Step 5**: machines, network and limitations of the test setup |
| `team_rows_4000_4999.csv` | The team's 1,000 ticket rows (4000–4999) used as test traffic and for accuracy; regenerate with `python scripts/make_team_rows.py path/to/ict3113_tickets.csv` |
| `results/` | Outputs of test runs |
| `logs/` | Service request logs and pin-check reports (evidence for every reported number) |

## Run the accuracy test

```
python scripts/accuracy_test.py                       # all three models (about 45 minutes)
python scripts/accuracy_test.py --models qwen2.5:7b   # one model
```

It restarts the service for each model, resets the database, verifies the model pins, sends the 150 golden tickets
and writes `results/accuracy/<run_id>/` (predictions, confusion matrix, summary).

## Load tests

JMeter test plans (open-loop, run from a separate machine) and the playbook will be added under `jmeter/`.

## Data and licences

Ticket narratives come from the US CFPB Consumer Complaint Database (course extract). Models are run through Ollama;
see the project report for licence acknowledgements.
