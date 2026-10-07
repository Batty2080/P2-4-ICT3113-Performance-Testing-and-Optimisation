"""
Run at the START of every test run.
Verifies the models in Ollama still match models.lock.json and saves the result to logs/.
Exit code 1 = a model changed -> do not run the benchmark.
"""
import json, sys, os, urllib.request, datetime

OLLAMA = "http://localhost:11434"
lock = json.load(open("models.lock.json"))
try:
    tags = json.load(urllib.request.urlopen(OLLAMA + "/api/tags", timeout=10))["models"]
except Exception as e:
    sys.exit(f"Cannot reach Ollama at {OLLAMA} ({e}). Is Ollama running?")
live = {m["name"]: m["digest"].replace("sha256:", "") for m in tags}

lines, ok = [], True
for m in lock["models"]:
    want = m["digest"].replace("sha256:", "")
    got = live.get(m["tag"], "MISSING")
    status = "OK" if got == want else "MISMATCH"
    ok &= status == "OK"
    lines.append(f"{m['tag']:16} locked {want[:12]}  live {got[:12]}  {status}")

stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
report = f"Pin check {stamp}\n" + "\n".join(lines) + f"\nRESULT: {'PASS' if ok else 'FAIL'}\n"
print(report)
os.makedirs("logs", exist_ok=True)
open(f"logs/pin_check_{stamp}.txt", "w").write(report)
sys.exit(0 if ok else 1)
