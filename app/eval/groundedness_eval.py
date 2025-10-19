# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List
import statistics, yaml, json

from app.agent.graph import plan_say

def _actions_text(decision: Dict[str, Any]) -> List[str]:
    out = []
    for a in decision.get("actions", []):
        if isinstance(a, dict) and a.get("type") == "say":
            t = (a.get("text") or "").strip()
            if t:
                out.append(t.lower())
    return out

def _is_grounded(decision: Dict[str, Any]) -> bool:
    """
    Response-level groundedness (lightweight):
    - There must be at least one evidence_id
    - And at least one speakable/source line appears in actions (heuristic check)
    """
    eids = [e.lower() for e in decision.get("evidence_ids", [])]
    if not eids:
        return False
    texts = " ".join(_actions_text(decision))
    # Heuristic: mention of known IDs or "source"
    if any(eid in texts for eid in eids):
        return True
    if "source" in texts or "according to" in texts:
        return True
    return False

def main(cfg_path: str = "configs/eval_quality.yaml") -> int:
    cfg = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    prompts = cfg["inputs"]["prompts"]
    repeats = int(cfg.get("execution", {}).get("repeats", 1))
    grounded: List[int] = []

    for p in prompts:
        for _ in range(repeats):
            d = plan_say(p["text"], p.get("lang", "en"))
            grounded.append(1 if _is_grounded(d) else 0)

    rate = sum(grounded) / max(1, len(grounded))
    print(f"GROUNDED: {sum(grounded)}/{len(grounded)} = {rate:.3f}")
    ok = rate >= float(cfg["targets"]["grounded_min"])
    print(f"VERDICT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
