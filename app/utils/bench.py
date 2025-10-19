"""
Latency micro-bench harness (offline mocks).

Runs N requests against /say and collects stage timers from Decision JSON.
Writes logs/bench-*.jsonl and prints P50/P95 and mean.
"""
from __future__ import annotations
import json, os, statistics, time, uuid, pathlib
import requests
from typing import Dict, List

API = os.environ.get("SAY_URL", "http://127.0.0.1:8000/say")
N = int(os.environ.get("BENCH_N", "40"))
TEXT = os.environ.get("BENCH_TEXT", "I feel anxious lately. What can I do?")

LOG_DIR = pathlib.Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
OUT = LOG_DIR / f"bench-{int(time.time())}.jsonl"

def p95(xs: List[float]) -> float:
    if not xs: return 0.0
    xs_sorted = sorted(xs)
    k = max(0, int(round(0.95 * (len(xs_sorted)-1))))
    return xs_sorted[k]

def main():
    lat_mouth, lat_plan, lat_tts = [], [], []
    sid = str(uuid.uuid4())
    for i in range(N):
        t0 = time.perf_counter()
        r = requests.post(API, json={"text": TEXT, "locale": "en", "session_id": sid}, timeout=5)
        r.raise_for_status()
        d: Dict = r.json()
        dt = d.get("latency_ms", {})
        lat_mouth.append(float(dt.get("mouth_to_ear", 0.0)))
        lat_plan.append(float(dt.get("plan", 0.0)))
        lat_tts.append(float(dt.get("tts", 0.0)))
        OUT.write_text(OUT.read_text() + json.dumps(d) + "\n" if OUT.exists() else json.dumps(d) + "\n", encoding="utf-8")

    def line(name: str, arr: List[float]) -> str:
        return f"{name}: mean={statistics.mean(arr):.1f} ms, p50={statistics.median(arr):.1f} ms, p95={p95(arr):.1f} ms"

    print(line("mouth_to_ear", lat_mouth))
    print(line("plan", lat_plan))
    print(line("tts", lat_tts))
    # Acceptance: mouth_to_ear p95 <= 1500 ms (mocks)
    assert p95(lat_mouth) <= 1500.0, "p95 mouth_to_ear exceeded 1.5s"

if __name__ == "__main__":
    main()
