import hashlib
import json
import os
import re
from datetime import datetime
from typing import List, Tuple

ARABIC_RANGE = re.compile(r"[\u0600-\u06FF]")
ROMAN_UR_HINTS = re.compile(
    r"\b(aur|kia|kyun|kya|mein|tum|ap|apka|masla|bechaini|afsurdgi|dil|soch|ghabrahat|"
    r"tez dhadkan|neend|thaka|ukhra|fikr|dua|sukoon|zindagi)\b", re.IGNORECASE
)
CRISIS_HINTS = re.compile(
    r"\b(self[-\s]?harm|suicid(e|al)|kill myself|hurt myself|immediate danger|call 1122|"
    r"emergency|overdose|harm others)\b", re.IGNORECASE
)

def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def normalize_text(s: str) -> str:
    # Trim whitespace, collapse multiple spaces/newlines
    s = s.replace("\u00A0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def estimate_tokens(s: str) -> int:
    # Rough heuristic ~ 4 chars/token
    return max(1, len(s) // 4)

def detect_language(text: str) -> str:
    if not text:
        return "other"
    arabic_chars = len(ARABIC_RANGE.findall(text))
    ratio = arabic_chars / max(1, len(text))
    if ratio >= 0.2:
        return "ur"
    if ROMAN_UR_HINTS.search(text) and ratio < 0.05:
        return "roman-ur"
    # Mixed if there is some Arabic but not dominant
    if 0 < ratio < 0.2:
        return "mixed"
    return "en"

def crisis_flag(text: str) -> bool:
    return bool(CRISIS_HINTS.search(text))

def chunk_paragraphs(paragraphs: List[str], target_chars: int = 1200) -> List[str]:
    """
    Simple paragraph packer: combine paragraphs until near target size.
    """
    chunks, buf = [], []
    total = 0
    for p in paragraphs:
        p = normalize_text(p)
        if not p:
            continue
        if total + len(p) + 1 > target_chars and buf:
            chunks.append("\n\n".join(buf))
            buf, total = [p], len(p)
        else:
            buf.append(p)
            total += len(p) + 1
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks

def make_chunk_record(
    *,
    text: str,
    title: str,
    section_path: List[str],
    source_key: str,
    source_url: str,
    license_str: str,
    distribution: str,
    doc_type: str,
    doc_id: str,
    page_span: Tuple[int, int],
    topics: List[str],
    icd11_codes: List[str]
) -> dict:
    tnorm = normalize_text(text)
    content_hash = sha256_hex(tnorm)
    chunk_id = content_hash[:12]
    lang = detect_language(tnorm)
    record = {
        "id": f"{doc_id}:{chunk_id}",
        "doc_id": doc_id,
        "chunk_id": chunk_id,
        "title": title,
        "section_path": section_path,
        "headings": section_path[1:],  # drop root as a heuristic
        "text": tnorm,
        "tokens_est": estimate_tokens(tnorm),
        "content_hash": content_hash,
        "source_key": source_key,
        "source_url": source_url,
        "license": license_str,
        "distribution": distribution,
        "language": lang,
        "topics": topics,
        "icd11_codes": icd11_codes,
        "doc_type": doc_type,
        "page_span": list(page_span),
        "crisis_flag": crisis_flag(tnorm),
        "created_at": now_iso(),
        "metadata": {}
    }
    return record

def write_jsonl(path: str, records: List[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
