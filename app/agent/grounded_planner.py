from __future__ import annotations
import json, time, argparse
from pathlib import Path
from typing import Any, Dict, List
import yaml
from app.retrieval.search import search as retrieve

def _load_min_score(default: float = 0.40) -> float:
    min_score = default
    for p in ("configs/retrieval.yaml", "configs/planner.yaml"):
        path = Path(p)
        if path.exists():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if "min_score" in data:
                min_score = float(data["min_score"])
    return min_score

def plan(query: str) -> Dict[str, Any]:
    results = retrieve(query)
    min_score = _load_min_score()
    top_score = float(results[0]["similarity"]) if results else 0.0

    decision: Dict[str, Any] = {
        "query": query,
        "timestamp": int(time.time()),
        "abstain": False,
        "reason": "",
        "evidence": [],         # metadata for citations
        "evidence_texts": [],   # short snippets to condition prompts/voice
        "meta": {"top_score": top_score, "min_score": min_score, "k": len(results)},
    }

    if not results or top_score < min_score:
        decision["abstain"] = True
        decision["reason"] = "low_confidence_or_out_of_scope"
        return decision

    for r in results:
        decision["evidence"].append({
            "evidence_id": r["evidence_id"],
            "doc_id": r["doc_id"],
            "topic": r["topic"],
            "ctype": r["ctype"],
            "license": r["license"],
            "source_path": r["source_path"],
            "cited_as": r["cited_as"],
            "similarity": float(r["similarity"]),
        })
        decision["evidence_texts"].append(r["text"])

    return decision

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ask", required=True)
    args = ap.parse_args()
    print(json.dumps(plan(args.ask), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
