# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import statistics, yaml, time

from app.agent.graph import plan_say

def _percentile(vals: List[float], pct: float) -> float:
    if not vals:
        return 0.0
    vs = sorted(vals)
    k = (len(vs) - 1) * pct
    f = int(k)
    c = min(f + 1, len(vs) - 1)
    if f == c:
        return vs[f]
    return vs[f] + (vs[c] - vs[f]) * (k - f)

def main(cfg_path: str = "configs/budget.yaml") -> int:
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    thr = cfg["thresholds"]
    utts = cfg["execution"]["utterances"]
    turns = int(cfg["execution"].get("turns_per_utterance", 10))

    latencies: List[float] = []
    tokens_in: List[int] = []
    tokens_out: List[int] = []
    cogs: List[float] = []

    for u in utts:
        for _ in range(turns):
            d = plan_say(u["text"], u.get("lang", "en"))
            l = float(d.get("latency_ms", {}).get("mouth_to_ear", 0.0))
            latencies.append(l)
            cost = d.get("cost", {})
            tokens_in.append(int(cost.get("tokens_in", 0)))
            tokens_out.append(int(cost.get("tokens_out", 0)))
            cogs.append(float(cost.get("est_cogs_per_min", 0.0)))

    p50 = _percentile(latencies, 0.50)
    p95 = _percentile(latencies, 0.95)
    max_in = max(tokens_in) if tokens_in else 0
    max_out = max(tokens_out) if tokens_out else 0
    max_cogs = max(cogs) if cogs else 0.0

    print(f"LAT: P50={p50:.1f}ms P95={p95:.1f}ms")
    print(f"TOKENS: in<= {max_in} out<= {max_out}")
    print(f"COGS/min max= ${max_cogs:.4f}")

    ok = (
        p50 <= float(thr["p50_ms_max"]) and
        p95 <= float(thr["p95_ms_max"]) and
        max_in <= int(thr["tokens_in_max"]) and
        max_out <= int(thr["tokens_out_max"]) and
        max_cogs <= float(thr["cogs_per_min_max"])
    )
    print(f"VERDICT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
