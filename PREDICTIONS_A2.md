# Prediction Record - Assignment 2 (Step 3)

Team P2-4, ICT3113 Assignment 2

We are committing this before the first Assignment 2 benchmark run. We will not change it after that.

## The cascade we are predicting for

This is Step 2's rule from `CASCADE_A2.md`. qwen2.5:1.5b classifies every ticket first. If it predicts a category on the accept list, we keep its answer. Otherwise the ticket goes to qwen2.5:7b and we use the 7b's answer.

| Setting | Keep the 1.5b answer for | Send to 7b |
|---|---|---|
| strict | Bank account, Money transfer, Mortgage | Credit reporting, Credit card, Debt collection, Consumer loan |
| relaxed | the strict ones plus Debt collection and Consumer loan | Credit reporting, Credit card |

## What we based this on

We used our A1 accuracy results and Step 2's tuning-set simulation (`results/a2/cascade_tuning.json`). We only looked at the tuning set (odd rows). We did not run the cascade on the test set.

Single-model accuracy on the test set is not really a prediction, since we can reuse our A1 records (same digest, prompt, Ollama version and machine). From those, qwen2.5:7b gets 60/75 (80.0%), llama3.2:3b gets 43/75 (57.3%) and qwen2.5:1.5b gets 32/75 (42.7%). The overall limit is 53/75, so both small models fail by themselves and won't be speed tested.

Timings from A1 with the 6-CPU limit: about 3 s per ticket for the 1.5b, 5.5 s for the 3b and 11.5 s for the 7b. In the A1 mixed-load runs the POST p50 was 2.84 s, 5.37 s and 12.46 s.

The memory check (`results/a2/memory_check_20261125-184905.txt`) already showed both models loaded together in `ollama ps`, using about 6.1 GiB out of 15.5 GiB.

What the tuning set gave us (cascade time = 1.5b time, plus 7b time if escalated):

| Setting | Escalated | Correct | Wrong answers kept | Estimated time per ticket |
|---|---|---|---|---|
| 7b alone | - | 55/75 (73.3%) | - | 12.0 s |
| relaxed | 55/75 (73.3%) | 53/75 (70.7%) | 6 of 20 | 12.2 s |
| strict | 65/75 (86.7%) | 56/75 (74.7%) | 0 of 10 | 13.6 s |

## 1. Which configuration will be fastest and still pass

We think qwen2.5:7b on its own will be the fastest configuration that passes. We don't think the cascade will beat it at either setting.

Our reasons:

- The small models fail on their own, so it is really 7b alone against the cascade.
- The 1.5b labels most tickets as Credit reporting or Credit card, and it is often wrong when it does, so 70 to 90% of tickets still have to go to the 7b. For the cascade to be faster on average it needs to escalate less than about 74% (1 - 3.0/11.5). Relaxed is right around that point and strict is above it.
- The median is worse than the average. When more than half the tickets get escalated, the middle ticket pays for both models (about 3 s + 11 s), so the cascade p50 should be higher than 7b alone even if the averages end up close.
- The extra 3 s on most tickets makes the machine busier at the same arrival rate, so there will be more queueing for the cascade.

## 2. Arrival rate and speed

We expect S (the middle of 3 typical tickets on the 7b) to be about 10 s, somewhere between 8 and 12 s. That gives one ticket every 20 s (180 per hour) and 10-minute runs with about 30 tickets each. This is higher than the 72 per hour peak from our A1 workload model.

We expect no errors or unfinished requests in any run, and both models should stay loaded the whole time (load_duration close to 0 after warm-up).

| Configuration | Escalated (test set) | Escalated (under load, from logs) | Test accuracy | Passes? | p50 per run | Pooled p95 |
|---|---|---|---|---|---|---|
| 7b alone | - | - | 60/75 (already known) | Yes, it's the reference | 14 s (11 to 18) | 30 s (22 to 40) |
| relaxed | 72% (62 to 80) | 75% (65 to 85) | 53/75 = 70.7% (51 to 56) | No. We think it fails Debt collection with 7/10 (needs 8/10), and overall is close | 17 s (14 to 22) | 35 s (25 to 45) |
| strict | 85% (78 to 92) | 87% (78 to 94) | 58/75 = 77.3% (55 to 60) | Yes, every category | 19 s (15 to 24) | 38 s (28 to 50) |

Other things we expect:

- The p50 of the three runs for each configuration should be within 15% of each other.
- The cascade p50 should be 20 to 40% slower than 7b alone, and neither setting should beat 7b alone in any run.
- The escalation rate under load should be within 10 points of the test-set rate.
- Tickets that are not escalated should be at least 90% correct for strict (it only keeps Bank, Money transfer and Mortgage answers) and around 70 to 80% for relaxed. Escalated tickets should be around 75 to 80%, close to the 7b alone.

## 3. Which categories will lose the most

1. Debt collection, at relaxed. We expect 7/10 instead of the 7b's 9/10. The 1.5b calls some debt collection complaints about car or personal loans "Consumer loan", and relaxed keeps that answer.
2. Mortgage, at relaxed, down 1 or 2 tickets. Some second-lien and payment-plan complaints also get called "Consumer loan".
3. Consumer loan, at relaxed. On the tuning set only 3 of the 1.5b's 8 Consumer loan answers were right.
4. Credit reporting and Credit card shouldn't lose anything, because they always go to the 7b.

At strict we don't expect any category to drop by more than 1 ticket compared to the 7b alone. If one does, it will probably be Bank account or Money transfer, because the "always right" result on the tuning set came from only 3 and 1 predictions.

---
Agreed by: Team P2-4, 25 November 2026
