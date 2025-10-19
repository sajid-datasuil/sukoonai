# Purpose: CLI entrypoint to run dataset loaders, write JSONL, and build index.
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import List
from app.ingest.loaders.phq9 import PHQ9Loader
from app.ingest.loaders.gad7 import GAD7Loader
from app.retrieval.indexer import build_index
from app.retrieval.schema import EvidenceRecord

def write_jsonl(records: List[EvidenceRecord], path: str) -> int:
    Path(Path(path).parent).mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in records:
             f.write(r.model_dump_json() + "\n")
    return len(records)

def run_ingest() -> int:
    loaders = [PHQ9Loader(), GAD7Loader()]
    all_records: List[EvidenceRecord] = []
    counts = {}
    for L in loaders:
        recs = list(L.iter_records())
        out = f"data/curated/{L.doc_id}.jsonl"
        counts[L.doc_id] = write_jsonl(recs, out)
        all_records.extend(recs)

    idx_meta = build_index(all_records, out_dir="data/index")
    print(json.dumps({
        "docs": counts,
        "total_chunks": sum(counts.values()),
        "index": idx_meta
    }, indent=2))
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["datasets"], help="datasets → run curated loaders")
    args = ap.parse_args()
    if args.command == "datasets":
        raise SystemExit(run_ingest())

if __name__ == "__main__":
    main()
