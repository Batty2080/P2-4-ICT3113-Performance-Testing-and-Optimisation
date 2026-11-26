"""
Assignment 2: measure S, the top model's typical time for one ticket, and derive the speed-test settings.

Procedure (A2 brief, Step 4 Set-up): restart Ollama and warm up; then send three different typical-length tickets to
the top model (qwen2.5:7b), one at a time, and take the middle time. That middle time is S, in seconds.

Before running this script (from the repo root, on the service machine):
    OLLAMA_MODEL=qwen2.5:7b TRIAGE_MODE=single RUN_ID=a2-s-measurement docker compose up -d triage
    docker compose restart ollama          # clears Ollama's memory and prompt cache; no model loaded

Then:  python scripts/measure_s.py
It sends the 3 warm-up tickets (timings discarded), then the 3 S tickets, through POST /tickets one at a time,
times each from the client side, looks up the service's own timing in logs/requests.jsonl by request ID, and writes
results/a2/s_measurement.txt. Ticket rows come from results/a2/workload_tickets.json (scripts/pick_a2_tickets.py).
Standard library only.
"""
import csv, datetime, json, math, statistics, subprocess, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = "http://localhost:8000"
TOP_MODEL = "qwen2.5:7b"
RUN_ID = "a2-s-measurement"


def post(narrative):
    req = urllib.request.Request(URL + "/tickets", json.dumps({"narrative": narrative}).encode(),
                                 {"Content-Type": "application/json"})
    t = time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as r:
        body = json.load(r)
        status = r.status
    return time.perf_counter() - t, status, body


def log_entry(request_id):
    for _ in range(20):
        with open(ROOT / "logs" / "requests.jsonl", encoding="utf-8") as f:
            for line in f:
                if request_id in line:
                    rec = json.loads(line)
                    if rec.get("request_id") == request_id:
                        return rec
        time.sleep(0.25)
    return None


def sh(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout + p.stderr).rstrip()


def main():
    csv.field_size_limit(10**8)
    with open(ROOT / "team_rows_4000_4999.csv", encoding="utf-8", newline="") as f:
        text = {int(r["row"]): r["narrative"] for r in csv.DictReader(f)}
    picks = json.loads((ROOT / "results" / "a2" / "workload_tickets.json").read_text(encoding="utf-8"))
    warmup = [t["row"] for t in picks["warmup_tickets"]]
    s_rows = [t["row"] for t in picks["s_tickets"]]

    out = []
    def log(s=""):
        print(s, flush=True); out.append(s)

    log(f"Assignment 2 – measurement of S · {datetime.datetime.now().isoformat(timespec='seconds')}")
    log("Machine A (Lenovo 83DF, i9-14900HX), compose.yaml unchanged (Ollama 0.40.0, 6 CPUs, OLLAMA_NUM_PARALLEL=1).")
    log(f"Service: single mode, {TOP_MODEL}, run_id {RUN_ID}. Requests sent to POST /tickets on the service machine,")
    log("one at a time; client time measured around each HTTP request. Ollama restarted just before this script.")
    log()
    log("$ docker compose exec ollama ollama ps   (before warm-up; expect empty)")
    log(sh(["docker", "compose", "exec", "ollama", "ollama", "ps"]))
    log()

    def send(kind, row):
        secs, status, body = post(text[row])
        rec = log_entry(body.get("request_id", "")) or {}
        calls = rec.get("model_calls") or [{}]
        ok = status == 201 and rec.get("run_id") == RUN_ID and rec.get("final_model") == TOP_MODEL
        log(f"{kind:8} row {row} ({len(text[row])} chars): client {secs:6.2f} s | service {rec.get('duration_ms', 0)/1000:6.2f} s"
            f" | model {rec.get('model_ms', 0)/1000:6.2f} s | load {(calls[0].get('load_duration_ms') or 0)/1000:5.2f} s"
            f" | HTTP {status} -> {body.get('category')} | final_model {rec.get('final_model')}{'' if ok else '  <-- CHECK'}")
        return secs, ok

    log("Warm-up (timings discarded):")
    for r in warmup:
        send("warm-up", r)
    log()
    log("$ docker compose exec ollama ollama ps   (after warm-up)")
    log(sh(["docker", "compose", "exec", "ollama", "ollama", "ps"]))
    log()
    log("S tickets:")
    results = [send("S", r) for r in s_rows]
    times = [t for t, _ in results]
    all_ok = all(ok for _, ok in results)

    S = statistics.median(times)
    gap = 2 * S
    run_s = round(max(S, 5) * 60)               # S minutes (exact, in whole seconds), minimum 5 minutes
    timeout_s = max(10 * S, 300)                # 10 x S seconds, at least 5 minutes
    timeout_min = math.ceil(timeout_s / 60)
    pause_min = timeout_min + 1                 # longer than the timeout by at least one minute
    log()
    log(f"Three S timings (client): {', '.join(f'{t:.2f}' for t in times)} s for rows {s_rows}")
    log(f"S = middle value = {S:.2f} s")
    log()
    log("Derived speed-test settings (same for every configuration):")
    log(f"  Arrival rate : one ticket every 2 x S = {gap:.2f} s on average = {60/gap:.2f} per minute = {3600/gap:.1f} per hour")
    log(f"  Run length   : S minutes, minimum 5 -> {run_s} s = {run_s/60:.2f} min (about {run_s/gap:.0f} tickets per run)")
    log(f"  HTTP timeout : max(10 x S, 300 s) = {timeout_s:.0f} s -> {timeout_min} min")
    log(f"  End pause    : timeout + 1 min -> {pause_min} min")
    log(f"  A1 design peak: 72 tickets/hour -> test rate is {'ABOVE' if 3600/gap > 72 else 'BELOW'} the client's peak")
    log()
    log(f"RESULT: {'OK – all requests answered by ' + TOP_MODEL + ' under run_id ' + RUN_ID if all_ok else 'CHECK – see marked lines'}")

    dest = ROOT / "results" / "a2" / "s_measurement.txt"
    dest.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"\nSaved {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
