from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any
import re, yaml
from app.retrieval.indexer import search as _idx_search

def _load_cfg() -> dict:
    cfg = {}
    for p in ("configs/retrieval.yaml", "configs/planner.yaml"):
        path = Path(p)
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                cfg.update(yaml.safe_load(f) or {})
    return cfg

def _boost(results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    ql = query.lower()
    q_tokens = set(re.findall(r"[a-z]+", ql))
    boosted = []
    for r in results:
        sim = float(r.get("similarity", 0.0))
        bonus = 0.0
        # Domain nudges (offline heuristic)
        if "anxiety" in ql and (r.get("topic") == "anxiety" or r.get("doc_id") == "gad7"):
            bonus += 0.6
        if "depression" in ql and (r.get("topic") == "depression" or r.get("doc_id") == "phq9"):
            bonus += 0.6
        # Token-overlap nudge
        text_tokens = set(re.findall(r"[a-z]+", r.get("text", "").lower()))
        if q_tokens:
            overlap = len(q_tokens & text_tokens) / max(1, len(q_tokens))
            bonus += 0.3 * overlap
        r["similarity"] = sim + bonus
        boosted.append(r)
    boosted.sort(key=lambda x: x["similarity"], reverse=True)
    return boosted

def search(query: str, k: int | None = None) -> List[Dict[str, Any]]:
    cfg = _load_cfg()
    top_k = int(k or cfg.get("top_k", 5))
    index_dir = cfg.get("index_dir", "data/index")
    base = _idx_search(query, k=top_k, index_dir=index_dir)
    return _boost(base, query)
