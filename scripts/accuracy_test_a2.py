"""
Assignment 2 accuracy test (Step 4): run the 75 test-set tickets through POST /tickets for one configuration and
score them against the golden labels and the A2 accuracy limits (docs/a2/REQUIREMENTS_A2.md).

For each configuration: verify the model pins, restart Ollama (clears memory and prompt cache), reset the database,
start the service in that configuration with a fresh run id, warm up on the 3 fixed warm-up tickets
(results/a2/workload_tickets.json) plus one direct call to qwen2.5:7b so both cascade models are resident, record
`ollama ps`, then send every test-set ticket (golden_set/test.csv) once, in row order, one at a time.

Reports: overall accuracy (count, %), per-category accuracy against the per-category limits (with counts and the
margin for small categories), a confusion matrix, and for the cascade: tickets escalated (from the service log),
accuracy of escalated and non-escalated tickets, and wrong answers accepted from the small model. Every answer is
reconciled with logs/requests.jsonl, and compared with the answer expected from the saved A1 single-model
predictions (both models run at temperature 0), as a consistency check.

Single models are not rerun: their test-set accuracy is taken from the saved A1 predictions (A2 brief, Step 4).

Usage (from the repo root, on the service machine, Docker running):
    python scripts/accuracy_test_a2.py --config cascade-strict
    python scripts/accuracy_test_a2.py --config cascade-relaxed
    python scripts/accuracy_test_a2.py --config cascade-strict --smoke    # 3 non-golden tickets, plumbing only
Output: results/a2/accuracy/<run_id>/{predictions.csv, confusion_matrix.csv, summary.json, summary.md}
Standard library only.
"""
import argparse, csv, datetime, json, os, subprocess, sys, time, urllib.error, urllib.request
from fractions import Fraction
from math import ceil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = "http://localhost:8000"
OLLAMA = "http://localhost:11434"
REQUEST_TIMEOUT = 400  # service model budget 300 s, gunicorn 360 s
SMALL, LARGE = "qwen2.5:1.5b", "qwen2.5:7b"
CATEGORIES = [
    "Credit reporting", "Debt collection", "Mortgage", "Credit card",
    "Bank account or service", "Consumer loan", "Money transfer or service",
]
# Must match service/app.py ACCEPT_CATEGORIES and docs/a2/CASCADE_A2.md
ACCEPT = {
    "strict": {"Mortgage", "Bank account or service", "Money transfer or service"},
    "relaxed": {"Mortgage", "Bank account or service", "Money transfer or service", "Debt collection", "Consumer loan"},
}
A1_PRED = {
    SMALL: ROOT / "results/accuracy/acc-qwen2.5-1.5b-20261009-033439/predictions.csv",
    LARGE: ROOT / "results/accuracy/acc-qwen2.5-7b-20261009-035613/predictions.csv",
}
# Minimum correct per category, as published in docs/a2/REQUIREMENTS_A2.md (recomputed below and checked).
PUBLISHED_MIN = {"Bank account or service": 6, "Consumer loan": 5, "Credit card": 3, "Credit reporting": 13,
                 "Debt collection": 8, "Money transfer or service": 10, "Mortgage": 7}
PUBLISHED_OVERALL_MIN = 53
SMOKE_ROWS = [4600, 4601, 4602]


def read_csv(path):
    csv.field_size_limit(10**9)
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def run(cmd, env=None, check=True):
    p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        sys.exit(f"Command failed: {' '.join(cmd)}\n{p.stdout}\n{p.stderr}")
    return p


def limits(test_rows, gold):
    """Overall and per-category minimum correct, from the 7b's saved A1 answers on the test set."""
    large = {int(r["row"]): r["predicted"] for r in read_csv(A1_PRED[LARGE])}
    n = len(test_rows)
    top_correct = sum(large[r] == gold[r] for r in test_rows)
    overall_min = ceil(Fraction(top_correct) - Fraction(10, 100) * n)
    per = {}
    for c in CATEGORIES:
        rows = [r for r in test_rows if gold[r] == c]
        top = sum(large[r] == c for r in rows)
        per[c] = {"n": len(rows), "top_correct": top, "min_correct": ceil(Fraction(top) - Fraction(15, 100) * len(rows))}
    assert overall_min == PUBLISHED_OVERALL_MIN, "overall limit differs from docs/a2/REQUIREMENTS_A2.md"
    assert {c: per[c]["min_correct"] for c in CATEGORIES} == PUBLISHED_MIN, "category limits differ from REQUIREMENTS_A2.md"
    return {"top_correct": top_correct, "n": n, "overall_min": overall_min, "per_category": per}


def wait_for(url, check, seconds=120):
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                body = json.load(r)
            if check(body):
                return body
        except Exception:
            pass
        time.sleep(2)
    sys.exit(f"{url} not ready within {seconds} s")


def prepare(mode, setting, model, run_id):
    p = run([sys.executable, str(ROOT / "scripts" / "check_pins.py")], check=False)
    print(p.stdout.strip(), flush=True)
    if p.returncode != 0:
        sys.exit("Pin check failed: a model changed since models.lock.json was written. Not running.")
    print("Stopping service, resetting database, restarting Ollama ...", flush=True)
    run(["docker", "compose", "stop", "triage"])
    for name in ("tickets.db", "tickets.db-wal", "tickets.db-shm"):
        (ROOT / "data" / name).unlink(missing_ok=True)
    run(["docker", "compose", "restart", "ollama"])
    wait_for(OLLAMA + "/api/tags", lambda b: "models" in b)
    env = dict(os.environ, TRIAGE_MODE=mode, CASCADE_SETTING=setting, OLLAMA_MODEL=model, RUN_ID=run_id)
    print(f"Starting service: TRIAGE_MODE={mode} CASCADE_SETTING={setting} OLLAMA_MODEL={model} RUN_ID={run_id}", flush=True)
    run(["docker", "compose", "up", "-d", "--force-recreate", "triage"], env=env)
    stats = wait_for(URL + "/stats", lambda b: "total" in b)
    if stats["total"] != 0:
        sys.exit(f"Database not empty after reset (total={stats['total']}).")


def post_ticket(narrative, request_id):
    req = urllib.request.Request(URL + "/tickets", json.dumps({"narrative": narrative}).encode("utf-8"),
                                 {"Content-Type": "application/json", "X-Request-ID": request_id})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
            status, body = r.status, json.load(r)
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body = json.load(e)
        except Exception:
            body = {}
    except Exception as e:
        status, body = 0, {"error": str(e)}
    return status, body, time.perf_counter() - t0


def warm_large_directly(narrative):
    """One direct call to the 7b (same prompt/options as the service, keep_alive -1) so it is resident."""
    prompt = (ROOT / "service" / "classification_prompt.txt").read_text(encoding="utf-8")
    body = json.dumps({"model": LARGE, "messages": [{"role": "system", "content": prompt},
                                                     {"role": "user", "content": narrative}],
                       "stream": False, "format": "json", "keep_alive": -1,
                       "options": {"temperature": 0, "num_gpu": 0}}).encode()
    urllib.request.urlopen(urllib.request.Request(OLLAMA + "/api/chat", body, {"Content-Type": "application/json"}),
                           timeout=REQUEST_TIMEOUT).read()


def log_records(run_id):
    recs = {}
    with open(ROOT / "logs" / "requests.jsonl", encoding="utf-8") as f:
        for line in f:
            if run_id not in line:
                continue
            r = json.loads(line)
            if r.get("run_id") == run_id and r.get("method") == "POST" and r.get("path") == "/tickets":
                recs[r["client_request_id"]] = r
    return recs


def frac(a, b):
    return f"{a}/{b} = {100 * a / b:.1f}%" if b else f"{a}/0"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True, choices=["cascade-strict", "cascade-relaxed"])
    ap.add_argument("--smoke", action="store_true", help="3 non-golden tickets; checks plumbing, no scoring")
    args = ap.parse_args()
    setting = args.config.split("-")[1]

    gold = {int(r["row"]): r["label"].strip() for r in read_csv(ROOT / "golden_set" / "golden_set.csv")}
    test_rows = sorted(int(r["row"]) for r in read_csv(ROOT / "golden_set" / "test.csv"))
    assert len(test_rows) == 75 and all(r % 2 == 0 for r in test_rows), "unexpected test set"
    text = {int(r["row"]): r["narrative"] for r in read_csv(ROOT / "team_rows_4000_4999.csv")}
    warmup = [t["row"] for t in json.loads((ROOT / "results/a2/workload_tickets.json").read_text())["warmup_tickets"]]
    lim = limits(test_rows, gold)
    a1 = {m: {int(r["row"]): (r["predicted"] or None) for r in read_csv(p)} for m, p in A1_PRED.items()}

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"{'smoke' if args.smoke else 'acc'}-a2-{args.config}-{stamp}"
    prepare("cascade", setting, LARGE, run_id)

    for row in warmup:
        status, body, secs = post_ticket(text[row], f"{run_id}-warmup-{row}")
        print(f"warm-up row {row}: HTTP {status}, {secs:.1f} s (excluded)", flush=True)
    warm_large_directly(text[warmup[0]])
    ps = run(["docker", "compose", "exec", "ollama", "ollama", "ps"]).stdout.rstrip()
    print(ps, flush=True)
    if SMALL not in ps or LARGE not in ps:
        sys.exit("Both models are not resident after warm-up. Not running.")

    rows = SMOKE_ROWS if args.smoke else test_rows
    started = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    sent = []
    for i, row in enumerate(rows, 1):
        rid = f"{run_id}-{row}"
        status, body, secs = post_ticket(text[row], rid)
        sent.append({"row": row, "rid": rid, "status": status, "category": body.get("category"),
                     "public_model": body.get("model"), "secs": secs, "error": body.get("error", "")})
        mark = "" if args.smoke else ("  OK" if body.get("category") == gold[row] else "  WRONG")
        print(f"{i}/{len(rows)} row {row}: HTTP {status}, {secs:.1f} s -> {body.get('category') or body.get('error')}{mark}",
              flush=True)
    finished = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    time.sleep(1)
    recs = log_records(run_id)

    results, problems = [], []
    for s in sent:
        r = recs.get(s["rid"])
        if r is None:
            problems.append(f"row {s['row']}: no service log entry")
            r = {}
        elif r.get("status") != s["status"] or (r.get("category") or None) != (s["category"] or None):
            problems.append(f"row {s['row']}: response and service log disagree")
        if s["status"] == 201 and s["public_model"] != f"cascade-{setting}":
            problems.append(f"row {s['row']}: response model field is {s['public_model']!r}")
        small_a1, large_a1 = a1[SMALL].get(s["row"]), a1[LARGE].get(s["row"])
        expected = small_a1 if small_a1 in ACCEPT[setting] else large_a1
        results.append({
            "row": s["row"], "golden": gold.get(s["row"], ""), "small_prediction": r.get("small_prediction") or "",
            "escalated": bool(r.get("escalated")), "escalation_reason": r.get("escalation_reason") or "",
            "final_model": r.get("final_model") or "",
            "predicted": s["category"] if s["status"] == 201 and s["category"] in CATEGORIES else "",
            "http_status": s["status"], "client_seconds": round(s["secs"], 3), "service_ms": r.get("duration_ms"),
            "request_id": s["rid"], "error": s["error"],
            "a1_small": small_a1 or "", "a1_large": large_a1 or "", "a1_expected": expected or "",
        })
    if args.smoke:
        for x in results:
            print(f"row {x['row']}: small {x['small_prediction'] or '-'} | escalated {x['escalated']} "
                  f"({x['escalation_reason'] or '-'}) | final {x['final_model']} -> {x['predicted']}")
        print("Log/response problems:", problems or "none")
        print(f"Smoke test finished; no scoring. Run id {run_id}")
        return

    # ---- scoring ----
    for x in results:
        x["correct"] = int(x["predicted"] == x["golden"])
    n = len(results)
    correct = sum(x["correct"] for x in results)
    per = {}
    for c in CATEGORIES:
        xs = [x for x in results if x["golden"] == c]
        k, m, need = sum(x["correct"] for x in xs), len(xs), lim["per_category"][c]["min_correct"]
        per[c] = {"n": m, "correct": k, "min_correct": need, "pass": k >= need,
                  "top_correct": lim["per_category"][c]["top_correct"], "margin": k - need}
    matrix = {g: {c: 0 for c in CATEGORIES + ["ERROR"]} for g in CATEGORIES}
    for x in results:
        matrix[x["golden"]][x["predicted"] or "ERROR"] += 1
    esc = [x for x in results if x["escalated"]]
    acc = [x for x in results if not x["escalated"] and x["final_model"] == SMALL]
    small_wrong_caught = sum(1 for x in esc if x["small_prediction"] != x["golden"])
    errors = sum(1 for x in results if not x["predicted"])
    overall_pass = correct >= lim["overall_min"]
    all_cats_pass = all(p["pass"] for p in per.values())
    vs_a1_small = sum(1 for x in results if x["small_prediction"] and x["small_prediction"] != x["a1_small"])
    vs_a1_final = [x["row"] for x in results if x["predicted"] != x["a1_expected"]]
    summary = {
        "config": args.config, "run_id": run_id, "started_at": started, "finished_at": finished,
        "accept_categories": sorted(ACCEPT[setting]), "n": n, "correct": correct, "errors": errors,
        "overall_min": lim["overall_min"], "top_model_correct": lim["top_correct"],
        "overall_pass": overall_pass, "all_categories_pass": all_cats_pass, "pass": overall_pass and all_cats_pass,
        "per_category": per, "confusion_matrix": matrix,
        "escalated": len(esc), "escalation_fraction": len(esc) / n,
        "escalation_reasons": {r: sum(1 for x in esc if x["escalation_reason"] == r) for r in
                               sorted({x["escalation_reason"] for x in esc})},
        "escalated_correct": sum(x["correct"] for x in esc), "not_escalated": len(acc),
        "not_escalated_correct": sum(x["correct"] for x in acc),
        "small_wrong_among_escalated": small_wrong_caught,
        "wrong_answers_accepted_from_small": sum(1 for x in acc if not x["correct"]),
        "reconciliation": {"requests_sent": n, "log_entries": len(recs) - len(warmup), "problems": problems},
        "consistency_with_a1": {"small_answer_differs_from_a1": vs_a1_small,
                                "final_answer_differs_from_a1_expected_rows": vs_a1_final},
    }

    out = ROOT / "results" / "a2" / "accuracy" / run_id
    out.mkdir(parents=True, exist_ok=True)
    cols = ["row", "golden", "small_prediction", "escalated", "escalation_reason", "final_model", "predicted", "correct",
            "http_status", "client_seconds", "service_ms", "request_id", "error", "a1_small", "a1_large", "a1_expected"]
    with open(out / "predictions.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(results)
    with open(out / "confusion_matrix.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["golden \\ predicted"] + CATEGORIES + ["ERROR"])
        for g in CATEGORIES:
            w.writerow([g] + [matrix[g][c] for c in CATEGORIES + ["ERROR"]])
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    small_cats = {"Credit card", "Bank account or service", "Consumer loan"}
    md = [f"# A2 accuracy: {args.config}", "",
          f"Run `{run_id}` · {started} → {finished} · test set (`golden_set/test.csv`, 75 even rows)", "",
          f"Rule: qwen2.5:1.5b first; accept its answer if it predicts {', '.join(sorted(ACCEPT[setting]))}; "
          f"otherwise escalate to qwen2.5:7b (`docs/a2/CASCADE_A2.md`).", "",
          f"- **Overall: {frac(correct, n)}**, limit {lim['overall_min']}/75 (70.0%) → **{'PASS' if overall_pass else 'FAIL'}**"
          f" (qwen2.5:7b alone: {frac(lim['top_correct'], n)})",
          f"- Per-category limit: **{'PASS' if all_cats_pass else 'FAIL'}**"
          + ("" if all_cats_pass else f" ({', '.join(c for c in CATEGORIES if not per[c]['pass'])})"),
          f"- **Configuration: {'PASSES' if summary['pass'] else 'FAILS'} both accuracy limits**",
          f"- Errors / invalid answers: {errors}", "",
          "## Per category", "",
          "| Category | Cascade | 7b alone | Min to pass | Result | Note |", "|---|---|---|---|---|---|"]
    for c in CATEGORIES:
        p = per[c]
        note = ""
        if c in small_cats:
            note = (f"small category ({p['n']} tickets): {p['margin'] + 1} more wrong would fail" if p["pass"]
                    else f"small category ({p['n']} tickets): needed {-p['margin']} more correct")
        md.append(f"| {c} | {frac(p['correct'], p['n'])} | {p['top_correct']}/{p['n']} | {p['min_correct']}/{p['n']} | "
                  f"{'PASS' if p['pass'] else 'FAIL'} | {note} |")
    md += ["", "## Escalation (from the service log)", "",
           f"- Escalated to qwen2.5:7b: **{frac(len(esc), n)}**  (reasons: "
           + ", ".join(f"{k} {v}" for k, v in summary["escalation_reasons"].items()) + ")",
           f"- Escalated tickets correct: {frac(summary['escalated_correct'], len(esc))}",
           f"- Not escalated (1.5b answer accepted) correct: {frac(summary['not_escalated_correct'], len(acc))}"
           f" → {summary['wrong_answers_accepted_from_small']} wrong answers slipped through",
           f"- Of the escalated tickets, the 1.5b's own answer was wrong on {small_wrong_caught}/{len(esc)}"
           " (the rule caught these)", "",
           "## Confusion matrix (rows: golden label; columns: cascade answer)", "",
           "| Golden \\ Predicted | " + " | ".join(CATEGORIES) + " | ERROR |", "|---" * (len(CATEGORIES) + 2) + "|"]
    for g in CATEGORIES:
        md.append(f"| {g} | " + " | ".join(str(matrix[g][c]) for c in CATEGORIES + ["ERROR"]) + " |")
    md += ["", "## Checks", "",
           f"- Service log reconciliation: {len(problems)} problems" + (": " + "; ".join(problems) if problems else ""),
           f"- 1.5b answers differing from its saved A1 answers: {vs_a1_small}",
           f"- Final answers differing from what the saved A1 answers predict for this rule: {len(vs_a1_final)}"
           + (f" (rows {', '.join(map(str, vs_a1_final))})" if vs_a1_final else ""), ""]
    (out / "summary.md").write_text("\n".join(md), encoding="utf-8")

    print(f"\n{args.config}: {frac(correct, n)} (limit {lim['overall_min']}) | categories "
          f"{'all pass' if all_cats_pass else 'FAIL: ' + ', '.join(c for c in CATEGORIES if not per[c]['pass'])} | "
          f"escalated {frac(len(esc), n)} | log problems {len(problems)} | differs from A1 estimate {len(vs_a1_final)}")
    print(f"Results in {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
