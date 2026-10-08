"""
Accuracy test (requirement R4).

For each candidate model: restart the triage service with that model, reset the database, verify the pinned
model digests, send one warm-up request (excluded), then send every golden-set ticket once through
POST /tickets, score the answers against golden_set/golden_set.csv, and cross-check against logs/requests.jsonl.

Usage (run from the repo root, on the machine that runs Docker):
    python scripts/accuracy_test.py                  # all models in models.lock.json
    python scripts/accuracy_test.py --models qwen2.5:7b      # one model (comma-separate for several)
    python scripts/accuracy_test.py --models qwen2.5:1.5b --smoke   # plumbing check: 3 non-golden tickets, no scoring

Needs: Docker running, models pulled (see scripts/pin_models.py / models.lock.json), team_rows_4000_4999.csv
(create with scripts/make_team_rows.py). Standard library only.
Output: results/accuracy/<run_id>/{predictions.csv, confusion_matrix.csv, summary.json, summary.md}
"""
import argparse, csv, datetime, json, subprocess, sys, time, urllib.error, urllib.request
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # repo root (this file lives in scripts/)
URL = "http://localhost:8000"
REQUEST_TIMEOUT = 400  # service model timeout is 300 s, gunicorn 360 s

CATEGORIES = [
    "Credit reporting", "Debt collection", "Mortgage", "Credit card",
    "Bank account or service", "Consumer loan", "Money transfer or service",
]
# Expected real-world share per category (REQUIREMENTS.md, R4; CFPB Bank of America 2024)
WEIGHTS = {
    "Bank account or service": 0.384, "Credit card": 0.236, "Credit reporting": 0.223,
    "Money transfer or service": 0.065, "Debt collection": 0.040, "Mortgage": 0.035, "Consumer loan": 0.017,
}
OVERALL_MIN = 0.85   # R4: weighted accuracy
RECALL_MIN = 0.70    # R4: every category
WARMUP_ROW = 4999    # outside the golden set (rows 4000-4149)
SMOKE_ROWS = [4500, 4501, 4502]


def load_golden():
    with open(ROOT / "golden_set" / "golden_set.csv", encoding="utf-8", newline="") as f:
        gold = {int(r["row"]): r["label"].strip() for r in csv.DictReader(f)}
    bad = {l for l in gold.values() if l not in CATEGORIES}
    if bad:
        sys.exit(f"Golden set has labels that are not one of the 7 categories: {bad}")
    return gold


def load_narratives():
    path = ROOT / "team_rows_4000_4999.csv"
    if not path.exists():
        sys.exit("team_rows_4000_4999.csv not found. Create it with:  python scripts/make_team_rows.py path/to/ict3113_tickets.csv")
    csv.field_size_limit(10**9)
    with open(path, encoding="utf-8", newline="") as f:
        return {int(r["row"]): r["narrative"] for r in csv.DictReader(f)}


def run(cmd, env=None, check=True):
    p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    if check and p.returncode != 0:
        sys.exit(f"Command failed: {' '.join(cmd)}\n{p.stdout}\n{p.stderr}")
    return p


def prepare_service(model, run_id):
    """Restart the triage service on a fresh database with this model and run id."""
    print(f"[{model}] stopping service and resetting database ...", flush=True)
    run(["docker", "compose", "stop", "triage"])
    for name in ("tickets.db", "tickets.db-wal", "tickets.db-shm"):
        (ROOT / "data" / name).unlink(missing_ok=True)
    env = dict(os.environ, OLLAMA_MODEL=model, RUN_ID=run_id)
    print(f"[{model}] starting service (RUN_ID={run_id}) ...", flush=True)
    run(["docker", "compose", "up", "-d", "--force-recreate", "triage"], env=env)
    deadline = time.time() + 90
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(URL + "/stats", timeout=5) as r:
                stats = json.load(r)
            if stats.get("total") == 0:
                return
            sys.exit(f"Database not empty after reset (total={stats.get('total')}). Aborting.")
        except Exception:
            time.sleep(2)
    sys.exit("Service did not become ready within 90 s.")


def check_pins():
    p = run([sys.executable, str(ROOT / "scripts" / "check_pins.py")], check=False)
    print(p.stdout.strip())
    if p.returncode != 0:
        sys.exit("Pin check failed: a model changed since models.lock.json was written. Not running.")


def post_ticket(narrative, request_id):
    req = urllib.request.Request(
        URL + "/tickets",
        data=json.dumps({"narrative": narrative}).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Request-ID": request_id},
    )
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
    except Exception as e:  # connection error / timeout
        status, body = 0, {"error": str(e)}
    return status, body.get("category"), time.perf_counter() - t0, body.get("error", "")


def score(pairs):
    """pairs: list of (golden_label, predicted_or_None). Errors / invalid answers count as wrong."""
    n = len(pairs)
    correct = sum(1 for g, p in pairs if p == g)
    per = {}
    for c in CATEGORIES:
        support = sum(1 for g, _ in pairs if g == c)
        hit = sum(1 for g, p in pairs if g == c and p == c)
        predicted = sum(1 for _, p in pairs if p == c)
        per[c] = {
            "support": support, "correct": hit, "predicted": predicted,
            "recall": hit / support if support else None,
            "precision": hit / predicted if predicted else None,
        }
    weighted = sum(WEIGHTS[c] * per[c]["recall"] for c in CATEGORIES if per[c]["recall"] is not None)
    matrix = {g: {c: 0 for c in CATEGORIES + ["ERROR"]} for g in CATEGORIES}
    for g, p in pairs:
        matrix[g][p if p in CATEGORIES else "ERROR"] += 1
    weak = [c for c in CATEGORIES if per[c]["recall"] is not None and per[c]["recall"] < RECALL_MIN]
    return {
        "n": n, "correct": correct, "errors": sum(1 for _, p in pairs if p not in CATEGORIES),
        "accuracy_unweighted": correct / n, "accuracy_weighted": weighted,
        "per_category": per, "confusion_matrix": matrix,
        "r4_overall_pass": weighted >= OVERALL_MIN, "r4_categories_below_70": weak,
        "r4_pass": weighted >= OVERALL_MIN and not weak,
    }


def reconcile(run_id, results):
    """Cross-check what this script saw against the service's own log (logs/requests.jsonl)."""
    log = ROOT / "logs" / "requests.jsonl"
    recs = {}
    if log.exists():
        with open(log, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if r.get("run_id") == run_id and r.get("method") == "POST" and r.get("path") == "/tickets":
                    recs[r["client_request_id"]] = r
    missing = mismatched = 0
    for x in results:
        r = recs.get(x["request_id"])
        if r is None:
            missing += 1
        elif r["status"] != x["http_status"] or (r["category"] or None) != (x["predicted"] or None):
            mismatched += 1
    return {"requests_sent": len(results), "log_entries_found": sum(1 for k in recs if not k.endswith("-warmup")),
            "missing_in_log": missing, "mismatched_with_log": mismatched}


def pct(x):
    return "n/a" if x is None else f"{100 * x:.1f}%"


def write_outputs(out_dir, model, run_id, results, summary, recon, started, finished):
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "predictions.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["row", "golden", "predicted", "correct", "http_status", "client_seconds", "request_id", "error"])
        for x in results:
            w.writerow([x["row"], x["golden"], x["predicted"] or "", int(x["predicted"] == x["golden"]),
                        x["http_status"], f"{x['seconds']:.3f}", x["request_id"], x["error"]])
    with open(out_dir / "confusion_matrix.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["golden \\ predicted"] + CATEGORIES + ["ERROR"])
        for g in CATEGORIES:
            w.writerow([g] + [summary["confusion_matrix"][g][c] for c in CATEGORIES + ["ERROR"]])
    meta = {"model": model, "run_id": run_id, "started_at": started, "finished_at": finished,
            "reconciliation": recon, **summary}
    (out_dir / "summary.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    lines = [f"# Accuracy: {model}", "", f"Run `{run_id}` · {started} → {finished}", "",
             f"- Tickets: {summary['n']} · correct: {summary['correct']} · errors/invalid: {summary['errors']}",
             f"- **Weighted accuracy (R4): {pct(summary['accuracy_weighted'])}** (need ≥ {OVERALL_MIN:.0%})",
             f"- Unweighted accuracy: {pct(summary['accuracy_unweighted'])}",
             f"- Categories below {RECALL_MIN:.0%} recall: {', '.join(summary['r4_categories_below_70']) or 'none'}",
             f"- **R4: {'PASS' if summary['r4_pass'] else 'FAIL'}**",
             f"- Reconciliation with service log: {recon['mismatched_with_log']} mismatched, {recon['missing_in_log']} missing "
             f"of {recon['requests_sent']} requests", "",
             "| Category | Support | Recall | Precision |", "|---|---|---|---|"]
    for c in CATEGORIES:
        p = summary["per_category"][c]
        lines.append(f"| {c} | {p['support']} | {pct(p['recall'])} | {pct(p['precision'])} |")
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_model(model, gold, narratives, smoke):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = model.replace(":", "-")
    run_id = f"{'smoke' if smoke else 'acc'}-{slug}-{stamp}"
    check_pins()
    prepare_service(model, run_id)

    status, cat, secs, err = post_ticket(narratives[WARMUP_ROW], f"{run_id}-warmup")
    print(f"[{model}] warm-up (excluded): HTTP {status}, {secs:.1f}s, {cat or err}", flush=True)

    rows = SMOKE_ROWS if smoke else sorted(gold)
    started = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    results = []
    for i, row in enumerate(rows, 1):
        rid = f"{run_id}-{row}"
        status, cat, secs, err = post_ticket(narratives[row], rid)
        ok = status == 201 and cat in CATEGORIES
        results.append({"row": row, "golden": gold.get(row, ""), "predicted": cat if ok else None,
                        "http_status": status, "seconds": secs, "request_id": rid, "error": err})
        mark = "" if smoke else ("  OK" if cat == gold[row] else "  WRONG")
        print(f"[{model}] {i}/{len(rows)} row {row}: HTTP {status}, {secs:.1f}s -> {cat or err}{mark}", flush=True)
    finished = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    if smoke:
        print(f"[{model}] smoke test finished; no scoring. Run id {run_id}")
        return None
    summary = score([(x["golden"], x["predicted"]) for x in results])
    recon = reconcile(run_id, results)
    out_dir = ROOT / "results" / "accuracy" / run_id
    write_outputs(out_dir, model, run_id, results, summary, recon, started, finished)
    print(f"\n[{model}] weighted {pct(summary['accuracy_weighted'])}, unweighted {pct(summary['accuracy_unweighted'])}, "
          f"errors {summary['errors']}, R4 {'PASS' if summary['r4_pass'] else 'FAIL'}; "
          f"log mismatches {recon['mismatched_with_log']}, missing {recon['missing_in_log']}")
    print(f"[{model}] results in {out_dir}\n")
    return model, summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", default="all", help="'all' (from models.lock.json) or comma-separated tags")
    ap.add_argument("--smoke", action="store_true", help="plumbing check on 3 non-golden tickets; no scoring")
    args = ap.parse_args()

    lock = json.loads((ROOT / "models.lock.json").read_text(encoding="utf-8"))
    locked = [m["tag"] for m in lock["models"]]
    models = locked if args.models == "all" else [m.strip() for m in args.models.split(",")]
    for m in models:
        if m not in locked:
            sys.exit(f"{m} is not in models.lock.json ({', '.join(locked)})")

    gold, narratives = load_golden(), load_narratives()
    for row in list(gold) + [WARMUP_ROW] + SMOKE_ROWS:
        if row not in narratives:
            sys.exit(f"Row {row} missing from team_rows_4000_4999.csv")
    if not args.smoke and len(gold) < 150:
        sys.exit(f"Golden set has only {len(gold)} tickets; expected 150.")

    done = [r for r in (test_model(m, gold, narratives, args.smoke) for m in models) if r]
    if len(done) > 1:
        print("Model              Weighted  Unweighted  Errors  R4")
        for m, s in done:
            print(f"{m:<18} {pct(s['accuracy_weighted']):>8}  {pct(s['accuracy_unweighted']):>10}  {s['errors']:>6}  "
                  f"{'PASS' if s['r4_pass'] else 'FAIL'}")


if __name__ == "__main__":
    main()
