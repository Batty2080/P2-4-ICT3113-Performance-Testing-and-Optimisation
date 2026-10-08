"""
Summarise load-test runs (JMeter results.jtl) and reconcile them with the service log.

Give it the run folder(s) of ONE test for ONE model; several folders (the 3 repeat runs) are pooled for the
pass/fail verdict, and per-run values with their spread are reported too.

Usage (from the repo root):
    python scripts/summarise_load.py results/load/load-mixed-qwen2.5-7b-r1 results/load/load-mixed-qwen2.5-7b-r2 ...
    python scripts/summarise_load.py results/load/load-stress-qwen2.5-7b-r1

Needs logs/requests.jsonl from the laptop (the service log) for the reconciliation; without it that part is skipped.
Percentiles use linear interpolation between ranked values. Standard library only.
Writes results/load/summary-<test>-<model>.md and .json
"""
import argparse, csv, json, re, statistics as st, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R1_P95, R1_P99, R3_P95 = 15.0, 30.0, 1.0           # seconds (REQUIREMENTS.md)
R2_RATE, R2_ERR, R2_RATIO, R2_WIN_MIN = 110, 0.01, 1.5, 10
STEP_TRIM_S = 30                                    # ignore the first seconds of each stress step (rate change)

POST, SEARCH, STATS = "POST /tickets", "GET /search", "GET /stats"
LABELS = (POST, SEARCH, STATS)
KIND = {POST: "post", SEARCH: "search", STATS: "stats"}   # as used in the X-Request-ID the plan sends


# ---------------------------------------------------------------------------------------------- small helpers
def pctl(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def fmt(x, nd=2):
    return "n/a" if x is None else f"{x:.{nd}f}"


def pass_fail(ok):
    return "PASS" if ok else "FAIL"


def spread(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return {"mean": st.mean(vals), "min": min(vals), "max": max(vals), "stdev": st.stdev(vals) if len(vals) > 1 else 0.0}


def label_stats(rows):
    secs = [r["ms"] / 1000 for r in rows]
    ok = sum(1 for r in rows if r["ok"])
    return {"n": len(rows), "ok": ok, "errors": len(rows) - ok, "error_pct": 100 * (len(rows) - ok) / len(rows) if rows else None,
            "p50": pctl(secs, 50), "p95": pctl(secs, 95), "p99": pctl(secs, 99),
            "mean": st.mean(secs) if secs else None, "max": max(secs) if secs else None}


# ---------------------------------------------------------------------------------------------- loading
def read_test_start(stdout_file):
    """Epoch ms at which JMeter started the test, from its console output (None if not found)."""
    if not stdout_file.exists():
        return None
    m = re.search(r"Starting standalone test @ .*\((\d{12,14})\)", stdout_file.read_text(encoding="utf-8", errors="ignore"))
    return int(m.group(1)) if m else None


def load_run(d):
    d = Path(d)
    info = json.loads((d / "run_info.json").read_text(encoding="utf-8-sig"))
    rows = []
    with open(d / "results.jtl", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append({"ts": int(r["timeStamp"]), "ms": int(r["elapsed"]), "label": r["label"], "code": r["responseCode"],
                         "ok": r["success"].lower() == "true", "seq": r.get("seq", ""), "row": r.get("row", "")})
    t0 = read_test_start(d / "jmeter_stdout.txt")
    if t0 is None and rows:
        t0 = min(r["ts"] for r in rows)
    return {"dir": d, "info": info, "rows": rows, "t0": t0}


def read_service_log(run_id, log_path):
    """The service-log entries of one run, keyed by the client_request_id that JMeter sent."""
    recs = {}
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            if run_id not in line:
                continue
            r = json.loads(line)
            if r.get("run_id") == run_id and r.get("client_request_id"):
                recs[r["client_request_id"]] = r
    return recs


# ---------------------------------------------------------------------------------------------- reconciliation
def post_wait_summary(waits):
    if not waits:
        return None
    return {"mean": st.mean(waits) / 1000, "p95": pctl(waits, 95) / 1000, "max": max(waits) / 1000}


def reconcile(run, log_path):
    if not log_path.exists():
        return {"skipped": f"{log_path} not found"}
    run_id = run["info"]["run_id"]
    recs = read_service_log(run_id, log_path)
    missing = status_bad = 0
    waits, seen = [], set()
    for r in run["rows"]:
        rid = f"{run_id}-{KIND.get(r['label'], 'x')}-{r['seq']}"
        s = recs.get(rid)
        if s is None:
            missing += 1
            continue
        seen.add(rid)
        status_bad += str(s["status"]) != r["code"]
        if r["label"] == POST:
            waits.append(r["ms"] - s["duration_ms"])      # time before the service started handling it + network
    extra = [k for k in recs if k not in seen and not k.endswith("-warmup")]
    return {"jtl_requests": len(run["rows"]), "missing_in_service_log": missing, "status_mismatch": status_bad,
            "in_service_log_not_in_jtl": len(extra), "post_wait_before_service_s": post_wait_summary(waits)}


def reconcile_line(run_id, rc):
    if "skipped" in rc:
        return f"- {run_id}: skipped ({rc['skipped']})"
    w = rc["post_wait_before_service_s"]
    queue = (f"; POST time before the service started handling it (queueing): mean {fmt(w['mean'])} s, "
             f"p95 {fmt(w['p95'])} s, max {fmt(w['max'])} s") if w else ""
    return (f"- {run_id}: {rc['jtl_requests']} JMeter requests; {rc['missing_in_service_log']} missing in the service log; "
            f"{rc['status_mismatch']} status mismatches; {rc['in_service_log_not_in_jtl']} service-log entries not in the JTL" + queue)


# ---------------------------------------------------------------------------------------------- R2 and stress analysis
def window_median(rows, lo_ms, hi_ms):
    xs = [r["ms"] / 1000 for r in rows if lo_ms <= r["ts"] < hi_ms]
    return (st.median(xs) if xs else None), len(xs)


def r2_checks(run):
    info, t0 = run["info"], run["t0"]
    posts = [r for r in run["rows"] if r["label"] == POST]
    dur_min = info["duration_min"]
    sent, ok = len(posts), sum(1 for r in posts if r["ok"])
    w = R2_WIN_MIN * 60000
    first, n1 = window_median(posts, t0, t0 + w)
    last, n2 = window_median(posts, t0 + dur_min * 60000 - w, t0 + dur_min * 60000 + 1)
    ratio = (last / first) if first and last else None
    err = (sent - ok) / sent if sent else 1
    return {"sent": sent, "completed_ok": ok, "offered_per_hour": sent / (dur_min / 60), "completed_per_hour": ok / (dur_min / 60),
            "error_rate": err, "median_first_window_s": first, "n_first": n1, "median_last_window_s": last, "n_last": n2,
            "ratio_last_over_first": ratio,
            "pass_throughput": ok >= 0.99 * sent and sent >= 0.98 * R2_RATE * dur_min / 60,
            "pass_error": err < R2_ERR, "pass_no_buildup": ratio is not None and ratio <= R2_RATIO}


def half_medians(rows):
    """Median latency (s) of the first and second half of a step's requests, in start order."""
    half = len(rows) // 2
    first = st.median([r["ms"] for r in rows[:half]]) / 1000 if half else None
    second = st.median([r["ms"] for r in rows[half:]]) / 1000 if rows[half:] else None
    return first, second


def step_stats(posts, t0, step, base_median):
    lo = t0 + (step["start_s"] + STEP_TRIM_S) * 1000
    rows = [r for r in posts if lo <= r["ts"] < t0 + step["end_s"] * 1000]
    secs = [r["ms"] / 1000 for r in rows]
    first, second = half_medians(rows)
    med = st.median(secs) if secs else None
    base = base_median if base_median is not None else med      # step 1 is compared with itself
    return {"rate_per_hour": step["rate_per_hour"], "n": len(rows), "errors": sum(1 for r in rows if not r["ok"]),
            "p50": med, "p95": pctl(secs, 95), "max": max(secs) if secs else None,
            "median_first_half": first, "median_second_half": second,
            "growing": bool(first and second and second / first > 1.5),
            "vs_first_step": (med / base) if med and base else None}


def stress_steps(run):
    posts = sorted((r for r in run["rows"] if r["label"] == POST), key=lambda r: r["ts"])
    out, base_median = [], None
    for step in run["info"]["steps"]:
        s = step_stats(posts, run["t0"], step, base_median)
        if base_median is None:
            base_median = s["p50"]
        out.append(s)
    flagged = next((s["rate_per_hour"] for s in out if s["errors"] or s["growing"] or (s["vs_first_step"] or 0) > 3), None)
    return out, flagged


# ---------------------------------------------------------------------------------------------- report sections
def per_run_section(runs):
    lines = ["## Per run", "", "| Run | Request | n | errors | p50 s | p95 s | p99 s | mean s | max s |", "|---|---|---|---|---|---|---|---|---|"]
    per_run = {}
    for r in runs:
        for lab in LABELS:
            rows = [x for x in r["rows"] if x["label"] == lab]
            if rows:
                s = label_stats(rows)
                per_run.setdefault(lab, []).append(s)
                lines.append(f"| {r['info']['run_id']} | {lab} | {s['n']} | {s['errors']} | {fmt(s['p50'])} | {fmt(s['p95'])} | {fmt(s['p99'])} | {fmt(s['mean'])} | {fmt(s['max'])} |")
    return lines, per_run


def pooled_section(runs):
    lines = ["", "## Pooled over all runs", "", "| Request | n | errors | error % | p50 s | p95 s | p99 s | mean s | max s |", "|---|---|---|---|---|---|---|---|---|"]
    pooled = {}
    for lab in LABELS:
        rows = [x for r in runs for x in r["rows"] if x["label"] == lab]
        if rows:
            s = pooled[lab] = label_stats(rows)
            lines.append(f"| {lab} | {s['n']} | {s['errors']} | {fmt(s['error_pct'], 1)} | {fmt(s['p50'])} | {fmt(s['p95'])} | {fmt(s['p99'])} | {fmt(s['mean'])} | {fmt(s['max'])} |")
    return lines, pooled


def spread_section(per_run):
    lines = ["", "## Spread across runs (per-run values)", "", "| Request | metric | mean | min | max | stdev |", "|---|---|---|---|---|---|"]
    for lab, ss in per_run.items():
        for m in ("p50", "p95", "p99"):
            sp = spread([s[m] for s in ss])
            if sp:
                lines.append(f"| {lab} | {m} s | {fmt(sp['mean'])} | {fmt(sp['min'])} | {fmt(sp['max'])} | {fmt(sp['stdev'])} |")
    return lines


def mixed_section(pooled):
    p, s = pooled.get(POST) or {}, pooled.get(SEARCH) or {}
    r1 = p.get("p95") is not None and p["p95"] <= R1_P95 and p["p99"] <= R1_P99
    r3 = s.get("p95") is not None and s["p95"] <= R3_P95
    lines = ["", "## Verdicts (pooled)", "",
             f"- **R1** POST p95 ≤ {R1_P95:g} s and p99 ≤ {R1_P99:g} s: p95 {fmt(p.get('p95'))} s, p99 {fmt(p.get('p99'))} s, **{pass_fail(r1)}**",
             f"- **R3** GET /search p95 ≤ {R3_P95:g} s: p95 {fmt(s.get('p95'))} s, **{pass_fail(r3)}**"]
    return lines, {"R1": bool(r1), "R3": bool(r3)}


def r2_row(run_id, c):
    return (f"| {run_id} | {c['sent']} | {c['completed_ok']} | {fmt(c['offered_per_hour'], 1)} | {fmt(c['completed_per_hour'], 1)} | "
            f"{fmt(100 * c['error_rate'], 1)} | {fmt(c['median_first_window_s'])} (n={c['n_first']}) | "
            f"{fmt(c['median_last_window_s'])} (n={c['n_last']}) | {fmt(c['ratio_last_over_first'])} | "
            f"{pass_fail(c['pass_throughput'])} | {pass_fail(c['pass_error'])} | {pass_fail(c['pass_no_buildup'])} |")


def r2_section(runs):
    lines = ["", "## R2 checks (per run)", "",
             "| Run | sent | completed ok | offered /h | completed /h | error % | median first 10 min s | median last 10 min s | ratio | throughput | errors | no build-up |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    checks = [r2_checks(r) for r in runs]
    lines += [r2_row(r["info"]["run_id"], c) for r, c in zip(runs, checks)]
    ok = all(c["pass_throughput"] and c["pass_error"] and c["pass_no_buildup"] for c in checks)
    lines += ["", f"- **R2** (every run must pass all three checks): **{pass_fail(ok)}**",
              f"- Throughput check: completed ≥ 99% of sent, and sent ≥ 98% of {R2_RATE}/h × duration (JMeter rounds the arrival count down)."]
    return lines, checks, {"R2": ok}


def stress_row(s):
    return (f"| {s['rate_per_hour']} | {s['n']} | {s['errors']} | {fmt(s['p50'])} | {fmt(s['p95'])} | {fmt(s['max'])} | "
            f"{fmt(s['median_first_half'])} | {fmt(s['median_second_half'])} | {'YES' if s['growing'] else 'no'} | {fmt(s['vs_first_step'], 1)}× |")


def stress_section(run):
    steps, flagged = stress_steps(run)
    lines = ["", f"## Stress steps (requests started in each step, first {STEP_TRIM_S} s of each step ignored)", "",
             "| Offered /h | n | errors | p50 s | p95 s | max s | median 1st half s | median 2nd half s | latency growing | p50 vs step 1 |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    lines += [stress_row(s) for s in steps]
    lines += ["", f"First step showing errors, growing latency within the step, or p50 > 3× step 1: **{flagged if flagged else 'none'}** requests/hour.",
              "(Indicative: a step is flagged when latency keeps rising during the step, so a queue is building.)"]
    return lines, {"steps": steps, "first_flagged_rate_per_hour": flagged}


def reconcile_section(runs, log_path):
    lines, results = ["", "## Reconciliation with the service log", ""], {}
    for r in runs:
        run_id = r["info"]["run_id"]
        results[run_id] = reconcile(r, log_path)
        lines.append(reconcile_line(run_id, results[run_id]))
    return lines, results


# ---------------------------------------------------------------------------------------------- main
def build_report(runs, log_path):
    test, model = runs[0]["info"]["test"], runs[0]["info"]["model"]
    lines = [f"# Load test summary: {test} · {model}", "", f"Runs pooled: {len(runs)} ({', '.join(r['info']['run_id'] for r in runs)})", ""]
    res = {"test": test, "model": model, "runs": [r["info"]["run_id"] for r in runs]}

    sec, per_run = per_run_section(runs)
    lines += sec
    res["per_run"] = per_run
    sec, pooled = pooled_section(runs)
    lines += sec
    res["pooled"] = pooled
    if len(runs) > 1:
        lines += spread_section(per_run)

    verdict = {}
    if test == "mixed":
        sec, verdict = mixed_section(pooled)
    elif test == "r2":
        sec, res["r2"], verdict = r2_section(runs)
    else:
        sec, res["stress"] = stress_section(runs[0])
    lines += sec
    res["verdict"] = verdict

    sec, res["reconciliation"] = reconcile_section(runs, log_path)
    lines += sec
    return test, model, lines, res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="+", help="run folder(s) under results/load/ (same test and model)")
    ap.add_argument("--service-log", default=str(ROOT / "logs" / "requests.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "results" / "load"))
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")   # the Windows console cannot print symbols such as ≤ otherwise

    runs = [load_run(d) for d in args.runs]
    tests = {(r["info"]["test"], r["info"]["model"]) for r in runs}
    if len(tests) != 1:
        sys.exit(f"Give runs of ONE test and ONE model; got {sorted(tests)}")

    test, model, lines, res = build_report(runs, Path(args.service_log))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"summary-{test}-{model.replace(':', '-')}"
    (out / f"{stem}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / f"{stem}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nWritten: {out / (stem + '.md')}")


if __name__ == "__main__":
    main()
