#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, json, os, re, hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any
from pypdf import PdfReader

def norm_ws(s: str) -> str:
    """Normalize whitespace to single spaces and trim."""
    return re.sub(r"\s+", " ", (s or "").strip())

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150) -> List[str]:
    """
    Simple, punctuation-aware chunking with overlap to help retrieval.
    Splits near sentence boundaries where possible.
    """
    t = (text or "").strip()
    if not t:
        return []
    if len(t) <= max_chars:
        return [t]
    out, start = [], 0
    while start < len(t):
        end = min(len(t), start + max_chars)
        # try to cut at a sentence boundary
        cut = t.rfind(".", start, end)
        if cut == -1 or cut <= start + 200:
            cut = end
        out.append(t[start:cut].strip())
        if cut >= len(t):
            break
        start = max(cut - overlap, cut)
    return [c for c in out if c]

def extract_pdf_text(path: str) -> List[Dict[str, Any]]:
    """Extract normalized text per page from a PDF."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"[ingest_pdf] Input PDF not found: {path}")
    reader = PdfReader(path)
    pages = []
    for i, p in enumerate(reader.pages, 1):
        txt = norm_ws(p.extract_text() or "")
        pages.append({"page": i, "text": txt})
    return pages

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--doc-id-prefix", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--section-root", required=True)
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--license", required=True)
    ap.add_argument("--distribution", required=True, choices=["public", "internal-only"])
    ap.add_argument("--topic", nargs="*", default=[])
    ap.add_argument("--icd11", nargs="*", default=[])
    ap.add_argument("--doc-type", default="taxonomy")
    ap.add_argument("--language", default="en")
    ap.add_argument("--source-key", help="Override source key; defaults to doc-id-prefix")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    pages = extract_pdf_text(args.pdf)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    source_key = (args.source_key or args.doc_id_prefix).strip()

    rows: List[Dict[str, Any]] = []
    n = 0
    for pg in pages:
        # Page-aware chunking
        for ch in chunk_text(pg["text"]):
            n += 1
            chunk_id = f"{n:04d}"
            section_path = [args.section_root, f"p.{pg['page']}"]
            rid = f"{args.doc_id_prefix}:{chunk_id}"
            h = sha256("|".join([source_key, args.title, "/".join(section_path), ch]))
            rows.append({
                "id": rid,
                "doc_id": args.doc_id_prefix,
                "chunk_id": chunk_id,                     # string (zero-padded)
                "title": args.title,
                "section_path": section_path,
                "text": ch,
                "language": args.language,
                "topics": args.topic,
                "license": args.license,
                "distribution": args.distribution,
                "source_url": args.source_url,
                "source_key": source_key,                 # no longer hardcoded
                "doc_type": args.doc_type,
                "icd11_codes": args.icd11,
                "crisis_flag": bool(re.search(r"\b(suicide|self[-\s]?harm|kill myself|hurt myself)\b", ch, re.I)),
                "content_hash": h,
                "created_at": now,                        # ISO-8601 UTC
            })

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} chunks → {args.out}")

if __name__ == "__main__":
    main()
