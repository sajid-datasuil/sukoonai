# app/ckg/ckg_adapter.py
from __future__ import annotations
import re, yaml
from typing import Dict, List, Tuple

# Tokenizer: ASCII letters/digits + Arabic block (Urdu)
_TOKEN_RE = re.compile(r"[A-Za-z0-9\u0600-\u06FF]+")

def _tok(s: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(s or "")]

def _has_arabic(s: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", s or ""))

def _norm(s: str) -> str:
    """
    Normalizes by:
      - lowercasing
      - removing spaces, hyphens, and punctuation (keeps ascii/arabic letters+digits)
    Example: 'PHQ-9' -> 'phq9', 'Patient Health Questionnaire' -> 'patienthealthquestionnaire'
    """
    if not s:
        return ""
    return "".join(_TOKEN_RE.findall(s.lower()))

# ---- Load config (with safe defaults) ----
try:
    with open("configs/ckg.yaml", "r", encoding="utf-8") as f:
        _CFG = yaml.safe_load(f) or {}
except Exception:
    _CFG = {}

_LAMBDA = float(_CFG.get("lambda", 0.25))
_MAX_SYN = int(_CFG.get("max_syn_per_term", 5))
_SYNS: Dict[str, List[str]] = dict(_CFG.get("synonyms", {}) or {})
_LANG_ALIASES: Dict[str, Dict[str, List[str]]] = dict(_CFG.get("lang_aliases", {}) or {})

# Build reverse lookup once: alias/variant -> (canon, weight)
# Simple weight scheme:
#  - exact canonical term: 1.0
#  - listed alias (same language): 0.9
#  - cross-language alias (ur/roman): 0.8
_ALIAS2W: Dict[str, Tuple[str, float]] = {}
_NORM2CANON: Dict[str, str] = {}
for canon, arr in _SYNS.items():
    c = canon.lower().strip()
    if c:
        _ALIAS2W[c] = (c, 1.0)
        _NORM2CANON[_norm(c)] = c
    for a in arr or []:
        a = (a or "").lower().strip()
        if a:
            _ALIAS2W[a] = (c, 0.9)
            _NORM2CANON[_norm(a)] = c

for lang, mapping in _LANG_ALIASES.items():
    for base, arr in (mapping or {}).items():
        b = (base or "").lower().strip()
        if b and b not in _ALIAS2W:
            _ALIAS2W[b] = (b, 0.9)  # base appears as alias too
        _NORM2CANON[_norm(b)] = b
        for a in arr or []:
            a = (a or "").lower().strip()
            if a and a not in _ALIAS2W:
                _ALIAS2W[a] = (b, 0.8)
            _NORM2CANON[_norm(a)] = b

def expand(query: str) -> Dict[str, object]:
    """
    Expand a query into synonym/alias terms.
    Returns: { 'syn_terms': [(term, weight), ...], 'lang': 'en'|'ur'|'roman' }
    """
    q = query or ""
    lang = "ur" if _has_arabic(q) else "en"
    terms = _tok(q)
    qn = _norm(q)
    out: List[Tuple[str, float]] = []
    seen = set()

    # --- Phrase-level detection: if normalized canon appears in normalized query,
    # inject canon + its aliases even if tokens don't match exactly (phq-9 vs phq9).
    for canon, syns in (_SYNS or {}).items():
        c = canon.lower().strip()
        if not c:
            continue
        if _norm(c) and _norm(c) in qn:
            # canon itself
            if c not in seen:
                out.append((c, 1.0)); seen.add(c)
            # its synonyms
            for a in (syns or [])[:_MAX_SYN]:
                a = (a or "").lower().strip()
                if a and a not in seen:
                    out.append((a, 0.9)); seen.add(a)
            # language aliases if any
            for lang_key in ("ur", "roman"):
                la = _LANG_ALIASES.get(lang_key, {})
                if c in la:
                    for a in la[c][: _MAX_SYN]:
                        a = (a or "").lower().strip()
                        if a and a not in seen:
                            out.append((a, 0.8)); seen.add(a)

    for t in terms:
        # map token via normalized alias map too (so 'phq'+'9' can still resolve if configured)
        tn = _norm(t)
        canon = _ALIAS2W.get(t, (None, None))[0] or _NORM2CANON.get(tn) or t
        # include the token (or resolved canon) itself
        if canon not in seen:
            w = _ALIAS2W.get(t, (canon, 0.7))[1] if canon == t else 1.0
            out.append((canon, float(w))); seen.add(canon)

        # collect synonyms for this (possibly resolved) canon
        # 1) direct synonyms block
        if canon in _SYNS:
            for a in _SYNS.get(canon, [])[:_MAX_SYN]:
                a = a.lower().strip()
                if a and a not in seen:
                    out.append((a, 0.9)); seen.add(a)
        # 2) language aliases for cross-language coverage
        for lang_key in ("ur", "roman"):
            la = _LANG_ALIASES.get(lang_key, {})
            if canon in la:
                for a in la[canon][: _MAX_SYN]:
                    a = a.lower().strip()
                    if a and a not in seen:
                        out.append((a, 0.8)); seen.add(a)

    return {"syn_terms": out, "lang": lang}

def score(hit: Dict[str, str], syn_terms: List[Tuple[str, float]]) -> float:
    """
    Lightweight concept score: normalized weighted overlap of (title+snippet) with syn_terms.
    """
    hay = _tok((hit.get("title") or "") + " " + (hit.get("snippet") or ""))
    if not hay or not syn_terms:
        return 0.0
    hayset = set(hay)
    # sum weights for present terms, normalized by total potential weight
    total_w = sum(w for _, w in syn_terms) or 1.0
    got_w = 0.0
    for term, w in syn_terms:
        if term in hayset:
            got_w += w
    # tiny heuristic bump if the source likely matches a concept (e.g., phq for PHQ-9 queries)
    bump = 0.1 if (("phq" in (hit.get("source") or "").lower()) and any("phq" in t for t, _ in syn_terms)) else 0.0
    return max(0.0, min(1.0, (got_w / total_w) + bump))

def get_lambda() -> float:
    return _LAMBDA
