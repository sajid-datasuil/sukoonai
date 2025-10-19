# app/safety/router.py
import re
from typing import Dict, List, Optional

# Additional high-signal Urdu-script crisis phrases (self-harm)
# (Broadened for Stage-1 drill reliability)
URDU_CRISIS_PATTERNS: List[str] = [
    r"خود\s*ک[وْ]\s*نقصان",         # "خود کو نقصان"
    r"خود\s*کو\s*تکلیف",            # "خود کو تکلیف"
    r"اپنی\s*زندگی\s*ختم",          # "اپنی زندگی ختم" / end my life (Urdu)
    r"اپنی\s*جان\s*لین(ا|ے)",       # "اپنی جان لینے"
    r"جان\s*لے\s*(لوں|لینا)",       # "جان لے لوں/لینا"
    r"خودکشی",                       # suicide (Urdu)
    # English / mixed-script fallbacks
    r"suicide",
    r"self[- ]?harm",
    r"kill\s*myself",
    r"end\s*my\s*life",
]

class SafetyRouter:
    """
    Lightweight regex-based crisis detector (pre-LLM).
    Urdu-first: includes Roman Urdu variants for self-harm, violence, and abuse.
    Also augmented with Urdu script phrases for self-harm.
    """

    def __init__(self) -> None:
        # Categories -> keyword lists (extend as needed)
        self._patterns: Dict[str, List[str]] = {
            "self-harm": [
                # English / Roman Urdu base set
                r"suicide", r"self[\s-]?harm", r"end my life", r"kill myself",
                r"take my own life", r"hurt myself",
                r"khud\s?kushi", r"khudkushi", r"apni\s+jaan\s+le(na)?",
                r"apne\s+aap\s+ko\s+maar(na)?", r"apne\s+aap\s+ko\s+nuksan"
            ],
            "harm-others": [
                r"kill (him|her|them|someone)", r"murder", r"shoot", r"stab", r"bomb",
                r"harm others", r"attack",
                r"qatal", r"maar\s+d(o|u)nga", r"hamla"
            ],
            "abuse/assault": [
                r"rape", r"sexual assault", r"molest", r"abuse", r"harass(ment)?",
                r"z(i|e)ad(a|aa)ti", r"jinsi\s+tashaddud", r"tashaddud"
            ],
            "medical-emergency": [
                r"overdose", r"poison", r"bleeding", r"emergency",
                r"panic attack", r"heart attack", r"choking", r"stroke", r"zehar"
            ],
        }

        # >>> Patch: augment self-harm with broader Urdu/EN patterns <<<
        self._patterns["self-harm"].extend(URDU_CRISIS_PATTERNS)

        # Compile one regex per category
        self._compiled: Dict[str, re.Pattern] = {
            cat: re.compile(r"(" + r"|".join(pats) + r")", flags=re.IGNORECASE)
            for cat, pats in self._patterns.items()
        }

    def detect(self, text: str) -> Dict[str, Optional[object]]:
        text = text or ""
        matches: List[str] = []
        hit_category: Optional[str] = None

        for cat, rx in self._compiled.items():
            m = rx.search(text)
            if m:
                hit_category = cat
                matches.append(m.group(0))
                break  # first-hit wins

        crisis = hit_category is not None
        confidence = 0.80 if crisis else 0.0

        return {
            "crisis": crisis,
            "category": hit_category,
            "matched_terms": matches,
            "confidence": confidence
        }
