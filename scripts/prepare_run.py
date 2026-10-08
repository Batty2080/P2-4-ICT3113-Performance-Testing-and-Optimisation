"""
Prepare the system under test for ONE load-test run (run this on the laptop, Machine A, before starting JMeter).

  1. verifies the pinned model digests (stops if a model changed)
  2. stops the triage service, deletes its database, restarts it with the chosen model and run id
  3. sends one warm-up request (excluded from results) so the model is loaded

Usage (from the repo root):
    python scripts/prepare_run.py --model qwen2.5:7b --run-id load-mixed-qwen2.5-7b-r1

The run id is what ties the service log (logs/requests.jsonl, field run_id) to the JMeter results; pass the same
value to JMeter with -Jrun_id=... (the run script on the load generator does this).
"""
import argparse, csv, json, sys
from pathlib import Path

import accuracy_test as a  # same folder; reuses pin check, database reset, service restart and warm-up request

ROOT = a.ROOT


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="model tag from models.lock.json")
    ap.add_argument("--run-id", required=True, help="run id, e.g. load-mixed-qwen2.5-7b-r1")
    args = ap.parse_args()

    locked = [m["tag"] for m in json.loads((ROOT / "models.lock.json").read_text(encoding="utf-8"))["models"]]
    if args.model not in locked:
        sys.exit(f"{args.model} is not in models.lock.json ({', '.join(locked)})")

    narratives = a.load_narratives()
    a.check_pins()
    a.prepare_service(args.model, args.run_id)
    status, cat, secs, err = a.post_ticket(narratives[a.WARMUP_ROW], f"{args.run_id}-warmup")
    print(f"warm-up (excluded): HTTP {status}, {secs:.1f}s, {cat or err}")
    if status != 201:
        sys.exit("Warm-up request failed; do not start the test.")
    print(f"\nREADY: model {args.model}, run id {args.run_id}. Start JMeter on the load generator now.")


if __name__ == "__main__":
    main()
