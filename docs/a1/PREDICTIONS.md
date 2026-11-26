# Prediction Record (Step 4)

Team P2-4 · ICT3113 Assignment 1

**This file is committed together with the golden set before the first benchmark run and will not be
revised afterwards.** Predictions are written to be specific enough to be proven wrong.

**Revision note (8 Oct 2026, before any benchmark run):** the first version of this file was written for a
different test PC (AMD Ryzen 5 5600, 7.9 GB RAM). The team then chose Darren's PC as the system under test,
so the hardware context and every latency-dependent prediction below were redone. The earlier version is
in the git history. Accuracy and hardest-category predictions do not depend on the PC and are unchanged.

## Context the predictions are based on

- **Hardware (system under test):** Intel Core i9-14900HX (24 cores / 32 threads), 31.7 GB RAM, Windows 11 Pro.
  Ollama and the triage service both run in Docker, CPU only (`num_gpu: 0`, no GPU passed to the container).
  Docker is allowed ≈ 15.5 GB RAM. **The Ollama container is limited to 6 CPUs (`cpus: "6"` in
  `compose.yaml`)** so that it behaves more like the client's commodity CPU servers than a 32-thread laptop.
  The load generator runs on a separate machine.
- **Software:** Ollama 0.40.0 (image `ollama/ollama:0.40.0`).
- **Service:** Flask under gunicorn with **1 sync worker, 1 thread**; Ollama with `OLLAMA_NUM_PARALLEL=1`.
  Every request is handled strictly one at a time.
- **Models (pinned in `models.lock.json`):** qwen2.5:1.5b, llama3.2:3b, qwen2.5:7b, all Q4_K_M.
- **Request size:** system prompt ≈ 400 tokens + ticket (median ≈ 200 tokens, p95 ≈ 450 tokens)
  → ≈ 600 input tokens median, ≈ 850 at p95; output ≈ 10 tokens (`{"category": "..."}`).
- **Observations the latency figures are scaled from:** informal development smoke tests on 8 Oct on this PC
  (`run_id` `smoke-nolimit` and `smoke-cpus6` in `logs/requests.jsonl`): 5 tickets of 411–1946 characters per
  model, taken from rows 4500–4504 (outside the golden set), one run each. With the 6-CPU limit the mean time
  per ticket was **2.7 s (1.5b), 5.2 s (3b), 10.1 s (7b)**, with medians of 2.2 s, 4.3 s and 8.3 s and the
  longest ticket (1946 chars) taking 4.3 s, 8.0 s and 16.7 s. These are five points per model, not a benchmark,
  so the ranges below are wide. No benchmark has been run.

Method: on CPU, time is dominated by reading the prompt (prompt evaluation), which scales with model size ×
input tokens. Queueing predictions use utilisation ρ = arrival rate × mean service time, with arrivals
treated as random (open-loop) and a single server.

## 1. Where the bottleneck will be, and why

**Prediction:** the bottleneck is **Ollama prompt evaluation on the CPU**. During any POST /tickets,
the Ollama container will use > 80% of its 6-CPU allowance (≥ 480% in `docker stats`); the Flask service
and SQLite will use < 5% of one core. `model_ms` will be ≥ 95% of `duration_ms` for every successful POST
at low load.

Because the service has **one sync gunicorn worker** and Ollama processes **one request at a time**,
requests queue in front of the service. Specific consequences we predict:

1. **Latency grows without bound** once the arrival rate exceeds 3600 ÷ (mean service time):
   ≈ **1300/h** for qwen2.5:1.5b, ≈ **690/h** for llama3.2:3b, ≈ **360/h** for qwen2.5:7b (±25%).
2. **GET /search and GET /stats queue behind classification** (head-of-line blocking in the single worker).
   A search is delayed only if it arrives while a classification is running, which happens with probability
   ≈ ρ: **5% (1.5b), 10% (3b), 20% (7b)** at the 72 tickets/h peak. Under the R3 mixed load, search p95 is therefore:
   **≈ 0.3 s (1.5b, passes narrowly, since only ≈ 5% of searches wait)**, **≈ 3 s (3b)** and **≈ 6 s (7b)**
   (each ±50%). **R3 fails for 3b and 7b**, even though a search on an idle service takes < 50 ms.
   The 1.5b result is the most likely to be wrong: ρ is almost exactly at the 5% that p95 cares about.
3. **Memory is not a constraint on this PC.** qwen2.5:7b needs ≈ 5 GB and Docker has ≈ 15.5 GB, so no 502s from
   failed loads and no swapping. The first request after a model loads will take an extra **1–3 s (1.5b),
   2–5 s (3b), 4–8 s (7b)** (excluded from steady-state results).

## 2. Per-model predictions

| Model | Single-request latency p50 | Single-request p95 | Max sustainable rate | Weighted accuracy (R4) | Unweighted accuracy | Invalid/error responses |
|---|---|---|---|---|---|---|
| qwen2.5:1.5b | **2.5 s** (1.8–3.5) | 4.5 s | ≈ 1300/h | **68%** (±7) | 63% (±7) | 2–5% |
| llama3.2:3b | **5 s** (3.5–7) | 9 s | ≈ 690/h | **76%** (±6) | 70% (±7) | ≈ 1% |
| qwen2.5:7b | **9 s** (6–13) | 17 s | ≈ 360/h | **84%** (±5) | 80% (±6) | < 0.5% |

"Single-request" = one request at a time at the off-peak rate, model already loaded, 6-CPU limit in place.

### Predicted outcome against each requirement

| Requirement | qwen2.5:1.5b | llama3.2:3b | qwen2.5:7b |
|---|---|---|---|
| R1 p95 ≤ 15 s and p99 ≤ 30 s at 72/h | **Pass** (p95 ≈ 5 s) | **Pass** (p95 ≈ 10 s) | **Fail narrowly on p95** (p95 ≈ 18 s, mean queueing at ρ = 20%; p99 ≈ 26 s passes) |
| R2 ≥ 110/h, no build-up | **Pass** (ρ ≈ 8%) | **Pass** (ρ ≈ 16%) | **Pass** (ρ ≈ 31%) |
| R3 search p95 ≤ 1 s | **Pass narrowly** (p95 ≈ 0.3 s) | **Fail** (≈ 3 s) | **Fail** (≈ 6 s) |
| R4 ≥ 85% weighted, ≥ 70% each | **Fail** | **Fail** | **Fail, narrowly** (overall close; Consumer loan < 70%) |

R2 detail: with ρ below 35% for every model there is no queue growth, so we predict the median latency in the
last 10 minutes will be within ±25% of the first 10 minutes (ratio 0.75–1.25) for every model, well inside
the 1.5× limit. Each 10-minute window holds only ≈ 18 requests, which is why R2 compares medians and not p95.

**Overall prediction: no candidate meets all four requirements.** The 1.5B model meets the performance
requirements (R1–R3) but not accuracy; the 7B model comes closest on accuracy but fails latency (R1, R3).
The 3B model fails R3 and R4. The prediction that every candidate fails at least one requirement rests mostly on R4.

### Stress test prediction

For qwen2.5:7b, stepping the arrival rate up from 72/h: latency stays bounded up to ≈ 250/h and grows
without bound above ≈ **360/h (±25%)**. At the 214/h surge scenario (ρ ≈ 60%) we predict POST p95 ≈ **35 s**
(20–60 s), still bounded. No HTTP errors until requests exceed the 300 s model timeout, after which the service
returns 504s; we do not expect to see them below ≈ 400/h.

## 3. Hardest categories, and why

Ranked from hardest to easiest (lowest predicted recall first), for all three models:

1. **Consumer loan** – lowest recall for every model (predicted < 60% for qwen2.5:1.5b, ≈ 65% for qwen2.5:7b).
   It is a catch-all of vehicle, student, payday and personal loans; narratives about missed payments
   get pulled to **Debt collection**, and installment-credit narratives to **Credit card**.
2. **Debt collection ↔ Credit reporting** – many complaints are about a collection account appearing on
   a credit report; we predict this is the **largest single off-diagonal cell** in every confusion matrix.
3. **Bank account or service ↔ Money transfer or service** – Zelle, wires and transfers go through
   checking accounts; we predict Money transfer tickets are misclassified as Bank account more often than the reverse.
4. **Credit card** – moderate; confused with Bank account for debit/fraud disputes.
5. **Mortgage** – easiest: distinctive vocabulary (escrow, servicer, foreclosure, refinance);
   predicted recall ≥ 90% for every model.

We also predict the smaller model will over-predict **Credit reporting** (the first category in the prompt
and the most common wording in the data).

---
Agreed by: Team P2-4 Date: 8 October 2026  (sign before committing)
