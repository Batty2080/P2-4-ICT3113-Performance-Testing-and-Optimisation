# Assignment 2 – fixed tickets (S, warm-up, speed test)

Produced by `scripts/pick_a2_tickets.py` (seed 3113). Source: `team_rows_4000_4999.csv`, rows 4150–4999 (outside the golden set), excluding rows [4500, 4501, 4502, 4503] used by the memory check. Pool: 846 tickets, median length 813 characters.

## S measurement (sent once each to qwen2.5:7b, one at a time)

| Row | Characters |
|---|---|
| 4444 | 813 |
| 4421 | 815 |
| 4987 | 816 |

## Warm-up (sent before every run, in this order; timings discarded)

| Row | Characters |
|---|---|
| 4791 | 814 |
| 4567 | 810 |
| 4936 | 818 |

## Speed-test workload (same tickets, same order, every run and every configuration)

40 tickets: 10 from each quarter of the pool's length distribution (Q1 201–501; Q2 501–810; Q3 813–1240; Q4 1245–1974 characters). Lengths in the list: min 212, median 809, max 1954. A run sends about 30, so it uses the first ~30 in this order. JMeter file: `jmeter/a2_speed_bodies.tsv`.

| # | Row | Characters | Length quarter |
|---|---|---|---|
| 1 | 4620 | 1406 | Q4 |
| 2 | 4192 | 1025 | Q3 |
| 3 | 4343 | 1079 | Q3 |
| 4 | 4815 | 1305 | Q4 |
| 5 | 4693 | 307 | Q1 |
| 6 | 4266 | 1389 | Q4 |
| 7 | 4486 | 1525 | Q4 |
| 8 | 4182 | 370 | Q1 |
| 9 | 4983 | 552 | Q2 |
| 10 | 4822 | 507 | Q2 |
| 11 | 4727 | 930 | Q3 |
| 12 | 4790 | 1384 | Q4 |
| 13 | 4951 | 836 | Q3 |
| 14 | 4479 | 1421 | Q4 |
| 15 | 4657 | 762 | Q2 |
| 16 | 4263 | 642 | Q2 |
| 17 | 4708 | 1954 | Q4 |
| 18 | 4267 | 727 | Q2 |
| 19 | 4367 | 302 | Q1 |
| 20 | 4897 | 546 | Q2 |
| 21 | 4440 | 1049 | Q3 |
| 22 | 4687 | 936 | Q3 |
| 23 | 4297 | 1082 | Q3 |
| 24 | 4242 | 620 | Q2 |
| 25 | 4907 | 848 | Q3 |
| 26 | 4887 | 212 | Q1 |
| 27 | 4504 | 468 | Q1 |
| 28 | 4215 | 1820 | Q4 |
| 29 | 4781 | 500 | Q1 |
| 30 | 4702 | 380 | Q1 |
| 31 | 4329 | 977 | Q3 |
| 32 | 4947 | 298 | Q1 |
| 33 | 4253 | 492 | Q1 |
| 34 | 4975 | 360 | Q1 |
| 35 | 4707 | 1167 | Q3 |
| 36 | 4739 | 1488 | Q4 |
| 37 | 4283 | 584 | Q2 |
| 38 | 4662 | 654 | Q2 |
| 39 | 4619 | 1307 | Q4 |
| 40 | 4575 | 782 | Q2 |
