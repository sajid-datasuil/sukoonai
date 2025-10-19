from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json
import re

CURATED_DIR = Path("data/curated")
DOCS_FILE = Path("docs/datasets.md")

# Static metadata (extend as you add new loaders)
META = {
    "phq9": {
        "title": "Patient Health Questionnaire (PHQ-9)",
        "topic": "depression",
        "type": "psychoeducation",
        "locale": "en",
        "license": "public/clinical use (check policy)",
        "voice_ready": "yes",
        "speakable": "PHQ-9 (Kroenke et al., 2001)",
    },
    "gad7": {
        "title": "Generalized Anxiety Disorder (GAD-7)",
        "topic": "anxiety",
        "type": "psychoeducation",
        "locale": "en",
        "license": "public/clinical use (check policy)",
        "voice_ready": "yes",
        "speakable": "GAD-7 (Spitzer et al., 2006)",
    },
    # "mhgap": {...},  # add when ingested
}

TABLE_HEADER = """## Ingestion Status (Week-3 seed)
| doc_id | title | topic | type | locale | license | voice_ready | ingested | chunks | last_update | speakable citation |
|---|---|---|---|---|---|---|---:|---:|---|---|
"""

def count_chunks(doc_id: str) -> int:
    f = CURATED_DIR / f"{doc_id}.jsonl"
    if not f.exists():
        return 0
    n = 0
    with f.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                n += 1
    return n

def build_table() -> str:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    rows = []
    for doc_id, m in META.items():
        chunks = count_chunks(doc_id)
        ingested = "✅" if chunks > 0 else "—"
        rows.append(
            f"| {doc_id} | {m['title']} | {m['topic']} | {m['type']} | {m['locale']} | {m['license']} | {m['voice_ready']} | {ingested} | {chunks} | {ts} | {m['speakable']} |"
        )
    return TABLE_HEADER + "\n".join(rows) + "\n"

def replace_block(md: str) -> str:
    start_pat = r"(?ms)^## Ingestion Status.*?(?:\n\|---.*\|\n)"  # header + separator row
    # Find where the table starts; then replace the whole table block until next blank line or EOF
    start_match = re.search(start_pat, md)
    if not start_match:
        # append at end
        return md.rstrip() + "\n\n" + build_table()
    start_idx = start_match.start()
    # Find next header (## ) or EOF
    next_header = re.search(r"(?m)^\#\#\s", md[start_idx+1:])
    end_idx = len(md)
    if next_header:
        end_idx = start_idx + 1 + next_header.start()
    return md[:start_idx] + build_table() + md[end_idx:]

def main():
    DOCS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if DOCS_FILE.exists():
        md = DOCS_FILE.read_text(encoding="utf-8")
    else:
        md = "# Datasets\n\n"
    updated = replace_block(md)
    DOCS_FILE.write_text(updated, encoding="utf-8")
    print("Updated docs/datasets.md")

if __name__ == "__main__":
    main()
