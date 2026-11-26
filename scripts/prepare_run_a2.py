"""
Assignment 2: prepare the laptop (Machine A) for ONE speed-test run, then start JMeter on the load generator.

Before the run (A2 brief, Step 4 "Each run"):
  1. verify the pinned model digests (stops if a model changed)
  2. stop the service, delete its database, restart Ollama (clears its memory and prompt cache)
  3. start the service in the chosen configuration with this run id
  4. send the 3 fixed warm-up tickets (results/a2/workload_tickets.json) through POST /tickets; timings discarded.
     For a cascade, also one direct call to qwen2.5:7b so the large model is loaded too
  5. check `ollama ps` lists the model(s) the configuration needs, and record GET /stats (expect 3: the warm-ups)
  Evidence is written to results/a2/load_prep/<run id>.txt.

After the run (optional but recommended), with --after: records `ollama ps` and GET /stats again, to show the
model(s) stayed loaded for the whole run. Written to results/a2/load_prep/<run id>-after.txt.

Usage (from the repo root, on the laptop):
    python scripts/prepare_run_a2.py --config cascade-strict --run-id a2-cascade-strict-r1
    ...start JMeter on the PC:  .\\jmeter\\run_load_test.ps1 -Test a2 -Config cascade-strict -Run 1
    python scripts/prepare_run_a2.py --config cascade-strict --run-id a2-cascade-strict-r1 --after
Configurations: single-7b, cascade-strict, cascade-relaxed. Models stay loaded (keep_alive -1, service/app.py),
so there is no 5-minute deadline for starting JMeter, but start it promptly.
"""
import argparse, datetime, json, sys, urllib.request

import accuracy_test_a2 as a  # same folder: pin check, reset, Ollama restart, service start, warm-up helpers

CONFIGS = {  # config -> (TRIAGE_MODE, CASCADE_SETTING, OLLAMA_MODEL, models that must be resident)
    "single-7b": ("single", "strict", a.LARGE, [a.LARGE]),
    "cascade-strict": ("cascade", "strict", a.LARGE, [a.SMALL, a.LARGE]),
    "cascade-relaxed": ("cascade", "relaxed", a.LARGE, [a.SMALL, a.LARGE]),
}


def stats_total():
    with urllib.request.urlopen(a.URL + "/stats", timeout=10) as r:
        return json.load(r)["total"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True, choices=list(CONFIGS))
    ap.add_argument("--run-id", required=True, help="must match the JMeter run id, e.g. a2-cascade-strict-r1")
    ap.add_argument("--after", action="store_true", help="record ollama ps and /stats after the run")
    args = ap.parse_args()
    expected = f"a2-{args.config}-r"
    if not (args.run_id.startswith(expected) or args.run_id.startswith("dry-" + expected)):
        sys.exit(f"Run id {args.run_id!r} does not match the config (expected {expected}<n> or dry-{expected}<n>).")
    mode, setting, model, needed = CONFIGS[args.config]
    dest = a.ROOT / "results" / "a2" / "load_prep"
    dest.mkdir(parents=True, exist_ok=True)
    out = []

    def log(s=""):
        print(s, flush=True); out.append(s)

    now = datetime.datetime.now().isoformat(timespec="seconds")
    if args.after:
        log(f"After run {args.run_id} ({args.config}) · {now}")
        ps = a.run(["docker", "compose", "exec", "ollama", "ollama", "ps"]).stdout.rstrip()
        log("$ docker compose exec ollama ollama ps"); log(ps)
        log(f"GET /stats total: {stats_total()}")
        missing = [m for m in needed if m not in ps]
        log("RESULT: " + ("required model(s) still loaded" if not missing else f"NOT LOADED: {missing}"))
        (dest / f"{args.run_id}-after.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
        return

    text = {int(r["row"]): r["narrative"] for r in a.read_csv(a.ROOT / "team_rows_4000_4999.csv")}
    warmup = [t["row"] for t in json.loads((a.ROOT / "results/a2/workload_tickets.json").read_text())["warmup_tickets"]]

    log(f"Prepare run {args.run_id} ({args.config}) · {now}")
    a.prepare(mode, setting, model, args.run_id)
    for row in warmup:
        status, body, secs = a.post_ticket(text[row], f"{args.run_id}-warmup-{row}")
        log(f"warm-up row {row}: HTTP {status}, {secs:.1f} s -> {body.get('category') or body.get('error')} (excluded)")
        if status != 201:
            sys.exit("Warm-up request failed; do not start the test.")
    if mode == "cascade":
        a.warm_large_directly(text[warmup[0]])
        log(f"direct warm-up call to {a.LARGE}: done")
    ps = a.run(["docker", "compose", "exec", "ollama", "ollama", "ps"]).stdout.rstrip()
    log("$ docker compose exec ollama ollama ps"); log(ps)
    total = stats_total()
    log(f"GET /stats total before the run: {total} (expected 3: the warm-up tickets)")
    missing = [m for m in needed if m not in ps]
    ok = not missing and total == 3
    log("RESULT: " + ("READY" if ok else f"NOT READY (missing models: {missing}, stats total {total})"))
    (dest / f"{args.run_id}.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
    if not ok:
        sys.exit(1)
    run_n = args.run_id.rsplit("-r", 1)[1]
    dry = " -Dry" if args.run_id.startswith("dry-") else ""
    print(f"\nREADY. Now on the PC:  .\\jmeter\\run_load_test.ps1 -Test a2 -Config {args.config} -Run {run_n}{dry}")
    print(f"After JMeter says Done, on the laptop:  python scripts/prepare_run_a2.py --config {args.config} "
          f"--run-id {args.run_id} --after")


if __name__ == "__main__":
    main()
