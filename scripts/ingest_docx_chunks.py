#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, json, os, re, hashlib
from typing import List, Dict, Any
from datetime import datetime, timezone
from docx import Document

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

def crisis_flag(text: str) -> bool:
    return bool(re.search(r"\b(suicide|self[-\s]?harm|kill myself|hurt myself)\b", text, re.I))

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def write_jsonl(rows: List[Dict[str, Any]], out_path: str):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} chunks → {out_path}")

def parse_docx(docx_path: str) -> List[Dict[str, str]]:
    doc = Document(docx_path)
    items = []
    for p in doc.paragraphs:
        txt = norm_ws(p.text)
        if not txt:
            continue
        style = (p.style.name if p.style else "") or ""
        items.append({"text": txt, "style": style})
    return items

def build_chunks(doc_items: List[Dict[str, str]], section_root: str) -> List[Dict[str, Any]]:
    rows, path = [], [section_root]
    buf: List[str] = []

    def flush():
        nonlocal rows, buf, path
        if not buf:
            return
        block = "\n".join(buf).strip()
        for ch in chunk_text(block):
            rows.append({"section_path": list(path), "text": ch})
        buf = []

    for it in doc_items:
        style = it["style"]
        txt = it["text"]
        if style.startswith("Heading"):
            flush()
            m = re.search(r"(\d+)", style)
            level = int(m.group(1)) if m else 1
            # keep last 3 levels max
            if level <= 1:
                path = [section_root, txt]
            else:
                # extend/trim to level
                while len(path) > level:
                    path.pop()
                if len(path) == level:
                    path[-1] = txt
                else:
                    path.append(txt)
        else:
            buf.append(txt)
    flush()
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", required=True)
    ap.add_argument("--doc-id-prefix", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--section-root", required=True)
    ap.add_argument("--source-key", required=True)
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--license", required=True)
    ap.add_argument("--distribution", required=True, choices=["public", "internal-only"])
    ap.add_argument("--topic", nargs="*", default=[])
    ap.add_argument("--doc-type", default="instrument")
    ap.add_argument("--language", default="en")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    doc_items = parse_docx(args.docx)
    blocks = build_chunks(doc_items, args.section_root)

    rows = []
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for i, b in enumerate(blocks, 1):
        text = b["text"]
        section_path = b["section_path"]
        chunk_id = f"{i:04d}"
        rid = f"{args.doc_id_prefix}:{chunk_id}"
        h = sha256("|".join([args.source_key, args.title, "/".join(section_path), text]))
        rows.append({
            "id": rid,
            "doc_id": args.doc_id_prefix,
            "chunk_id": chunk_id,
            "title": args.title,
            "section_path": section_path,
            "text": text,
            "language": args.language,
            "topics": args.topic,
            "license": args.license,
            "distribution": args.distribution,
            "source_url": args.source_url,
            "source_key": args.source_key,
            "doc_type": args.doc_type,
            "crisis_flag": crisis_flag(text),
            "content_hash": h,
            "created_at": now,
        })
    write_jsonl(rows, args.out)

if __name__ == "__main__":
    main()
