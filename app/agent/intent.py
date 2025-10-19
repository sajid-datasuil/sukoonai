"""
Cheap deterministic topic gate.

Maps user text -> {"topic": "anxiety"|"depression"|"other"} using keyword lists.
Safety note: Gate errs on 'other' when uncertain.
"""
from __future__ import annotations
import re
from typing import Literal, Dict

Topic = Literal["anxiety", "depression", "other"]

ANX_PATTERNS = [
    r"\banx(ious|iety)?\b", r"\bpani(c|ky)\b", r"\bworry(ing)?\b",
    r"\bstress(ed)?\b", r"\bfikar\b", r"\bdar\b"
]
DEP_PATTERNS = [
    r"\bdepress(ion|ed)?\b", r"\blow mood\b", r"\bhopeless\b",
    r"\bgham\b", r"\budaas(i)?\b"
]

def classify_topic(text: str) -> Dict[str, Topic]:
    t = text.lower()
    if any(re.search(p, t) for p in ANX_PATTERNS):
        return {"topic": "anxiety"}
    if any(re.search(p, t) for p in DEP_PATTERNS):
        return {"topic": "depression"}
    return {"topic": "other"}
