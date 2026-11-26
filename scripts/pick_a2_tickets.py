"""
Assignment 2: pick the fixed tickets used for measuring S, warm-up and the speed test.

All tickets come from rows 4150-4999 (outside the golden set, rows 4000-4149). Rows 4500-4503 are left out because
the A2 memory check (results/a2/memory_check_20261125-184905.txt) already sent them to the models.

  speed list   40 tickets: 10 from each quarter of the ticket-length distribution (so the list covers short, typical
               and long tickets, with 10 long ones), shuffled once into a fixed order. JMeter sends them in this order
               in every speed run, for every configuration.
  warm-up      3 typical-length tickets (closest to the median length), sent before every run, timings discarded.
  S            3 other typical-length tickets, sent once to qwen2.5:7b to measure S.

The three sets do not overlap. A fixed seed makes the choice reproducible: rerunning gives identical output.

Usage (from the repo root):  python scripts/pick_a2_tickets.py
Input:  team_rows_4000_4999.csv
Output: results/a2/workload_tickets.json   row numbers and lengths of all three sets
        results/a2/workload_tickets.md     the same, readable
        jmeter/a2_speed_bodies.tsv         row <TAB> JSON body for POST /tickets, speed list in run order
Standard library only.
"""
import csv, json, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = 3113
FIRST_ROW, LAST_ROW = 4150, 4999
EXCLUDE = {4500, 4501, 4502, 4503}  # used by the A2 memory check
PER_QUARTER = 10


def main():
    csv.field_size_limit(10**8)
    with open(ROOT / "team_rows_4000_4999.csv", encoding="utf-8", newline="") as f:
        text = {int(r["row"]): r["narrative"] for r in csv.DictReader(f)}
    pool = sorted((r for r in text if FIRST_ROW <= r <= LAST_ROW and r not in EXCLUDE), key=lambda r: (len(text[r]), r))
    n = len(pool)
    median_len = len(text[pool[n // 2]])
    rng = random.Random(SEED)

    # Typical tickets for S and warm-up: the 6 rows closest to the median length, split alternately.
    typical = sorted(pool, key=lambda r: (abs(len(text[r]) - median_len), r))[:6]
    s_rows, warmup_rows = typical[0::2], typical[1::2]
    used = set(typical)

    # Speed list: 10 per length quarter, then one fixed shuffle.
    quarters = [pool[i * n // 4:(i + 1) * n // 4] for i in range(4)]
    bounds = [(len(text[q[0]]), len(text[q[-1]])) for q in quarters]
    speed = []
    for q in quarters:
        speed += rng.sample([r for r in q if r not in used], PER_QUARTER)
    rng.shuffle(speed)

    def info(rows):
        return [{"row": r, "chars": len(text[r])} for r in rows]

    out = {
        "seed": SEED, "source": "team_rows_4000_4999.csv", "pool": f"rows {FIRST_ROW}-{LAST_ROW} minus {sorted(EXCLUDE)}",
        "pool_size": n, "pool_median_chars": median_len,
        "length_quarters_chars": [{"quarter": i + 1, "min": lo, "max": hi} for i, (lo, hi) in enumerate(bounds)],
        "s_tickets": info(s_rows), "warmup_tickets": info(warmup_rows), "speed_tickets_in_order": info(speed),
    }
    dest = ROOT / "results" / "a2"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "workload_tickets.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    lens = sorted(len(text[r]) for r in speed)
    md = [
        "# Assignment 2 – fixed tickets (S, warm-up, speed test)",
        "",
        f"Produced by `scripts/pick_a2_tickets.py` (seed {SEED}). Source: `team_rows_4000_4999.csv`, rows "
        f"{FIRST_ROW}–{LAST_ROW} (outside the golden set), excluding rows {sorted(EXCLUDE)} used by the memory check. "
        f"Pool: {n} tickets, median length {median_len} characters.",
        "",
        "## S measurement (sent once each to qwen2.5:7b, one at a time)",
        "",
        "| Row | Characters |", "|---|---|", *[f"| {r} | {len(text[r])} |" for r in s_rows],
        "",
        "## Warm-up (sent before every run, in this order; timings discarded)",
        "",
        "| Row | Characters |", "|---|---|", *[f"| {r} | {len(text[r])} |" for r in warmup_rows],
        "",
        "## Speed-test workload (same tickets, same order, every run and every configuration)",
        "",
        f"40 tickets: 10 from each quarter of the pool's length distribution "
        f"({'; '.join(f'Q{i+1} {lo}–{hi}' for i, (lo, hi) in enumerate(bounds))} characters). "
        f"Lengths in the list: min {lens[0]}, median {(lens[19] + lens[20]) // 2}, max {lens[-1]}. "
        f"A run sends about 30, so it uses the first ~30 in this order. JMeter file: `jmeter/a2_speed_bodies.tsv`.",
        "",
        "| # | Row | Characters | Length quarter |", "|---|---|---|---|",
        *[f"| {i} | {r} | {len(text[r])} | Q{next(k + 1 for k, q in enumerate(quarters) if r in q)} |" for i, r in enumerate(speed, 1)],
        "",
    ]
    (dest / "workload_tickets.md").write_text("\n".join(md), encoding="utf-8")

    with open(ROOT / "jmeter" / "a2_speed_bodies.tsv", "w", encoding="utf-8", newline="") as f:
        f.write("row\tbody\n")
        for r in speed:
            body = json.dumps({"narrative": text[r]}, ensure_ascii=True)
            assert "\t" not in body and "\n" not in body and "\r" not in body
            f.write(f"{r}\t{body}\n")

    print(f"S tickets: {s_rows}  warm-up: {warmup_rows}")
    print(f"Speed list ({len(speed)}): {speed}")
    print("Wrote results/a2/workload_tickets.json, results/a2/workload_tickets.md, jmeter/a2_speed_bodies.tsv")


if __name__ == "__main__":
    main()
