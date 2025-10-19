# Purpose: Deterministic chunking (≈300–500 chars) optimized for voice readability.
from __future__ import annotations
import re
from typing import List

def normalize_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s

def split_into_chunks(s: str, min_c=300, max_c=500) -> List[str]:
    s = normalize_text(s)
    # Prefer sentence-ish splits; then pack to 300–500 chars.
    sentences = re.split(r"(?<=[\.!\?])\s+", s)
    chunks, buf = [], ""
    for sent in sentences:
        if not sent:
            continue
        if len(buf) + 1 + len(sent) <= max_c:
            buf = (buf + " " + sent).strip()
        else:
            if len(buf) >= min_c:
                chunks.append(buf)
                buf = sent
            else:
                # If too small, force append
                buf = (buf + " " + sent).strip()
                chunks.append(buf)
                buf = ""
    if buf:
        chunks.append(buf)
    return [c for c in chunks if c]
