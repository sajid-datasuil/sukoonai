from __future__ import annotations
import json, argparse
from typing import List, Dict
from app.retrieval.search import search

def recall_at_k(q: str, gold_doc_ids: List[str], k: int = 5) -> float:
    results = search(q, k=k) or []
    # pass if any returned doc_id is in the gold set
    return 1.0 if any((r or {}).get("doc_id") in gold_doc_ids for r in results) else 0.0

def run(gold_path: str, k: int, min_recall: float) -> Dict:
    # Read gold file with BOM-tolerant encoding
    with open(gold_path, "r", encoding="utf-8-sig") as f:
        items = json.load(f)

    scores = [recall_at_k(it["q"], it["gold_doc_ids"], k=k) for it in items]
    recall = sum(scores) / max(1, len(scores))
    out = {
        "k": k,
        "min_recall": min_recall,
        "recall": recall,
        "passed": recall >= min_recall,
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    if not out["passed"]:
        raise SystemExit(1)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default="data/golden/anxiety_depression.json")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--min_recall", type=float, default=0.90)
    args = ap.parse_args()
    return run(args.gold, args.k, args.min_recall)

if __name__ == "__main__":
    main()
