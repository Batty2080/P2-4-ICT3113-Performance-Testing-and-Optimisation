"""
Step 4 - pin candidate models.
Run ONCE after `ollama pull`-ing your candidates.
Reads the exact digest of each model from Ollama and writes models.lock.json.
"""
import json, sys, urllib.request, datetime

OLLAMA = "http://localhost:11434"

# >>> EDIT THIS LIST to your 3-5 candidate models (exact tags) <<<
CANDIDATES = [
    ("qwen2.5:1.5b", "tiny"),
    ("llama3.2:3b",  "small"),
    ("qwen2.5:7b",   "medium"),
]

def get(path):
    try:
        with urllib.request.urlopen(OLLAMA + path, timeout=10) as r:
            return json.load(r)
    except Exception as e:
        sys.exit(f"Cannot reach Ollama at {OLLAMA} ({e}). Is Ollama running?")

version = get("/api/version").get("version", "unknown")
live = {m["name"]: m for m in get("/api/tags")["models"]}

models, missing = [], []
for tag, size_class in CANDIDATES:
    m = live.get(tag)
    if not m:
        missing.append(tag); continue
    d = m.get("details", {})
    models.append({
        "tag": tag,
        "digest": "sha256:" + m["digest"].replace("sha256:", ""),
        "params": d.get("parameter_size"),
        "quant": d.get("quantization_level"),
        "family": d.get("family"),
        "size_bytes": m.get("size"),
        "size_class": size_class,
    })

if missing:
    sys.exit("Not pulled yet: " + ", ".join(missing) +
             "\nRun:  " + "  ".join(f"ollama pull {t};" for t in missing))

lock = {"recorded_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "ollama_version": version, "models": models}
json.dump(lock, open("models.lock.json", "w"), indent=2)

print(f"Ollama {version}\n")
print(f"{'tag':16}{'params':>8}  {'quant':8}  digest")
for m in models:
    print(f"{m['tag']:16}{m['params'] or '':>8}  {m['quant'] or '':8}  {m['digest']}")
print("\nSaved models.lock.json  -> commit it to Git before any benchmark run.")
