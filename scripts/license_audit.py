import argparse, csv, json, os, sys, hashlib
from pathlib import Path
from collections import Counter
from typing import Dict, Any, List

def load_jsonl(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

def sidecar_meta(p: Path) -> Dict[str, Any]:
    m = p.with_suffix(p.suffix + ".meta.json")
    if m.exists():
        try:
            return json.loads(m.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def walk_corpus_jsonl(corpus_dir: str) -> List[Dict[str, Any]]:
    """Synthesize JSONL-like rows from a filesystem corpus."""
    rows: List[Dict[str, Any]] = []
    root = Path(corpus_dir)
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        meta = sidecar_meta(p)
        rows.append({
            "path": str(p.relative_to(root)),
            "license": (meta.get("license") or "").strip(),
            "distribution": (meta.get("distribution") or "").strip(),
            "source_key": (meta.get("source_key") or "").strip(),
        })
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="*", help="JSONL files (e.g., artifacts/open_evidence/*.jsonl)")
    ap.add_argument("--out", required=True, help="Output CSV path")
    ap.add_argument("--corpus", help="Folder of KB files to audit (reads optional *.meta.json sidecars)")
    args = ap.parse_args()

    rows: List[Dict[str, Any]] = []
    if args.corpus:
        rows = walk_corpus_jsonl(args.corpus)
    else:
        for p in args.inputs:
            if not os.path.exists(p):
                print(f"[warn] missing file: {p}", file=sys.stderr)
                continue
            rows.extend(load_jsonl(p))

    counts = Counter()
    missing = {"license": 0, "distribution": 0, "source_key": 0}
    totals = 0

    for rec in rows:
        lic = (rec.get("license") or "").strip()
        dist = (rec.get("distribution") or "").strip()
        src  = (rec.get("source_key") or "").strip()
        if not lic:  missing["license"] += 1
        if not dist: missing["distribution"] += 1
        if not src:  missing["source_key"] += 1
        counts[(lic or "MISSING"), (dist or "MISSING"), (src or "MISSING")] += 1
        totals += 1

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["license", "distribution", "source_key", "count"])
        for (lic, dist, src), c in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
            w.writerow([lic, dist, src, c])

    print(f"Wrote CSV → {args.out}")
    print(f"Total items: {totals}")
    if any(missing.values()):
        print(f"[WARN] Missing fields → {missing}")
    else:
        print("All items contained license, distribution, and source_key.")

if __name__ == "__main__":
    main()
