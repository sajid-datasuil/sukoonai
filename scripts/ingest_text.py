#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, json, os, re, hashlib
from typing import List, Dict, Any
from datetime import datetime, timezone

def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150) -> List[str]:
    t = text.strip()
    if not t:
        return []
    if len(t) <= max_chars:
        return [t]
    chunks, start = [], 0
    while start < len(t):
        end = min(len(t), start + max_chars)
        cut = t.rfind(".", start, end)
        if cut == -1 or cut <= start + 200:
            cut = end
        chunks.append(t[start:cut].strip())
        if cut >= len(t):
            break
        start = max(cut - overlap, cut)
    return [c for c in chunks if c]

def sha256(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--txt", required=True)
    ap.add_argument("--doc-id-prefix", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--section-root", required=True)
    ap.add_argument("--source-key", required=True)
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--license", required=True)
    ap.add_argument("--distribution", required=True, choices=["public", "internal-only"])
    ap.add_argument("--topic", nargs="*", default=[])
    ap.add_argument("--doc-type", default="terminology")
    ap.add_argument("--language", default="en")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.txt, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    # Split by blank lines, then chunk
    paras = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
    rows = []
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    n = 0
    for para in paras:
        for ch in chunk_text(para):
            n += 1
            section_path = [args.section_root]
            chunk_id = f"{n:04d}"
            rid = f"{args.doc_id_prefix}:{chunk_id}"
            h = sha256("|".join([args.source_key, args.title, "/".join(section_path), ch]))
            rows.append({
                "id": rid,
                "doc_id": args.doc_id_prefix,
                "chunk_id": chunk_id,
                "title": args.title,
                "section_path": section_path,
                "text": ch,
                "language": args.language,
                "topics": args.topic,
                "license": args.license,
                "distribution": args.distribution,
                "source_url": args.source_url,
                "source_key": args.source_key,
                "doc_type": args.doc_type,
                "crisis_flag": False,
                "content_hash": h,
                "created_at": now,
            })

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} chunks → {args.out}")

if __name__ == "__main__":
    main()
