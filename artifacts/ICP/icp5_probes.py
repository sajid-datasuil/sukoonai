# artifacts/ICP/icp5_probes.py
import json, urllib.request, urllib.error, os, pathlib

BASE = "http://127.0.0.1:8002"
OUT_DIR = pathlib.Path("artifacts/ICP"); OUT_DIR.mkdir(parents=True, exist_ok=True)
probes = [
    {"label":"healthz", "method":"GET", "url": f"{BASE}/healthz", "body": None},
    {"label":"ui_static", "method":"GET", "url": f"{BASE}/static/demo_ui.html", "body": None},
    {"label":"turn_neutral", "method":"POST", "url": f"{BASE}/api/web/turn", "body": {"text":"What is SukoonAI?"}},
]
out = {}
for p in probes:
    req = urllib.request.Request(p["url"], method=p["method"])
    if p["body"] is not None:
        data = json.dumps(p["body"]).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    else:
        data = None
    try:
        with urllib.request.urlopen(req, data, timeout=5) as r:
            content = r.read()
            try:
                parsed = json.loads(content.decode("utf-8", "ignore"))
            except Exception:
                parsed = content.decode("utf-8", "ignore")[:400]
            out[p["label"]] = {"status": r.status, "ok": True, "content": parsed}
    except urllib.error.HTTPError as e:
        out[p["label"]] = {"status": e.code, "ok": False, "error": str(e)}
    except Exception as e:
        out[p["label"]] = {"status": 0, "ok": False, "error": str(e)}

with open(OUT_DIR / "icp5_probes.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("Wrote", OUT_DIR / "icp5_probes.json")
