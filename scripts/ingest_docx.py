import argparse
import json
import os
import re
from docx import Document

URL_RE = re.compile(r"(https?://\S+)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    # Preflight checks (from snippet): ensure input exists and output dir is ready
    if not os.path.exists(args.docx):
        raise SystemExit(f"[ingest_docx] Input DOCX not found: {args.docx}")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    doc = Document(args.docx)
    items = []
    for p in doc.paragraphs:
        text = (p.text or "").strip()
        if not text:
            continue
        urls = URL_RE.findall(text)
        if urls:
            items.append({
                "title": text[:120],
                "url": urls[0],
                "notes": text
            })
        else:
            # Treat non-URL lines as notes/headers
            items.append({
                "title": text[:120],
                "url": None,
                "notes": text
            })

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(items)} catalog entries → {args.out}")

if __name__ == "__main__":
    main()
