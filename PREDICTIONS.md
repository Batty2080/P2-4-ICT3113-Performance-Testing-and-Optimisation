# Prediction Record (Step 4)

Team P2-4 · ICT3113 Assignment 1

**This file is committed together with the golden set before the first benchmark run and will not be
revised afterwards.** Predictions are written to be specific enough to be proven wrong.

## Context the predictions are based on

- **Hardware:** AMD Ryzen 5 5600 (6 cores / 12 threads), 7.9 GB RAM, Windows 11 Home. Ollama and the
  triage service both run in Docker (WSL2), CPU only (`num_gpu: 0`, no GPU passed to the container).
- **Service:** Flask under gunicorn with **1 sync worker, 1 thread**; Ollama with `OLLAMA_NUM_PARALLEL=1`.
  Every request is handled strictly one at a time.
- **Models (pinned in `models.lock.json`):** qwen2.5:1.5b, llama3.2:3b, qwen2.5:7b, all Q4_K_M.
- **Request size:** system prompt ≈ 400 tokens + ticket (median ≈ 200 tokens, p95 ≈ 450 tokens)
  → ≈ 600 input tokens median, ≈ 850 at p95; output ≈ 10 tokens (`{"category": "..."}`).
- **Only prior observation:** one development smoke test (`run_id: development`, 5 Oct) –
  qwen2.5:1.5b took 4.1 s for a 266-character ticket. No benchmark has been run.

Method: on CPU, time is dominated by reading the prompt (prompt evaluation), which scales roughly with
parameter count × input tokens. We scale the one observed point by model size (×2.1 for 3B, ×5 for 7.6B)
and by ticket length.

## 1. Where the bottleneck will be, and why

**Prediction:** the bottleneck is **Ollama prompt evaluation on the CPU**. During any POST /tickets,
Ollama will use > 80% of the CPU; the Flask service and SQLite will use < 5%. `model_ms` will be
≥ 95% of `duration_ms` for every successful POST at low load.

Because the service has **one sync gunicorn worker** and Ollama processes **one request at a time**,
requests queue in front of the service. Specific consequences we predict:

1. **Latency grows without bound** once the arrival rate exceeds 3600 ÷ (mean service time):
   ≈ **720/h** for qwen2.5:1.5b, ≈ **330/h** for llama3.2:3b, ≈ **145/h** for qwen2.5:7b (±25%).
2. **GET /search and GET /stats queue behind classification** (head-of-line blocking in the single worker).
   Under the R3 mixed load, search p95 will be close to one full classification time:
   ≈ **5 s (1.5b), ≈ 11 s (3b), ≈ 25 s (7b)** – **R3 will fail for every model**, even though a search
   on an idle service takes < 50 ms.
3. **Memory:** qwen2.5:7b needs ≈ 5 GB. If Docker/WSL2 has less than ≈ 6 GB available, the 7B model will
   either fail to load (HTTP 502 from the service) or swap, adding > 50% to its latency.

## 2. Per-model predictions

| Model | Single-request latency p50 | Single-request p95 | Max sustainable rate | Weighted accuracy (R4) | Unweighted accuracy | Invalid/error responses |
|---|---|---|---|---|---|---|
| qwen2.5:1.5b | **5 s** (4–7) | 8 s | ≈ 720/h | **68%** (±7) | 63% (±7) | 2–5% |
| llama3.2:3b | **11 s** (8–14) | 16 s | ≈ 330/h | **76%** (±6) | 70% (±7) | ≈ 1% |
| qwen2.5:7b | **25 s** (18–32) | 35 s | ≈ 145/h | **84%** (±5) | 80% (±6) | < 0.5% |

"Single-request" = one request at a time at the off-peak rate, model already loaded.
The first request after a model loads will take an extra **5–20 s** (excluded from steady-state results).

### Predicted outcome against each requirement

| Requirement | qwen2.5:1.5b | llama3.2:3b | qwen2.5:7b |
|---|---|---|---|
| R1 p95 ≤ 15 s at 72/h | **Pass** (p95 ≈ 9 s) | **Fail, narrowly** (p95 ≈ 18 s) | **Fail** (p95 ≈ 50 s with queueing) |
| R2 ≥ 110/h, no build-up | **Pass** | **Pass** | **Pass on throughput, fail on build-up** (utilisation ≈ 76%, p95 last 10 min > 1.2× first) |
| R3 search p95 ≤ 1 s | **Fail** | **Fail** | **Fail** |
| R4 ≥ 85% weighted, ≥ 70% each | **Fail** | **Fail** | **Fail, narrowly** (overall close; Consumer loan < 70%) |

**Overall prediction: no candidate meets all four requirements.** The 1.5B model meets the performance
requirements but not accuracy; the 7B model comes closest on accuracy but fails latency.

### Stress test prediction

For qwen2.5:7b, stepping the arrival rate up from 72/h: latency stays bounded up to ≈ 120/h and grows
without bound above ≈ **145/h (±25%)** – below the 214/h surge scenario. No HTTP errors until requests
exceed the 300 s model timeout, after which the service returns 504s.

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
Agreed by: ______________________ Date: __________ (sign before committing)
