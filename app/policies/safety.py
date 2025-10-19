# UTF-8 LF
from typing import Dict, List

CRISIS_KEYWORDS: List[str] = [
    "suicide",
    "kill myself",
    "hurt myself",
    "end my life",
    "self harm",
]


def detect_risk(text: str) -> Dict:
    """
    Deterministic keyword risk detector (Week-1).
    - 'suicide'-class words -> level 'med' (or 'high' if multiple)
    - otherwise 'none'
    """
    t = (text or "").lower()
    triggers = [kw for kw in CRISIS_KEYWORDS if kw in t]
    if not triggers:
        return {"level": "none", "triggers": []}
    level = "high" if len(triggers) >= 2 else "med"
    return {"level": level, "triggers": triggers}
