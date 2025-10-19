# app/policies/term_gates.py
from __future__ import annotations
from pathlib import Path
import re, yaml
from typing import Dict, List

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
_POLICY_DIRS = [HERE, REPO / "configs" / "policies", Path("app/policies"), Path("configs/policies")]

def _load_list(name: str) -> List[str]:
    for d in _POLICY_DIRS:
        p = d / name
        try:
            if p.exists():
                data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                terms = data.get("terms") or []
                return sorted({t.strip().lower() for t in terms if isinstance(t, str) and t.strip()})
        except Exception:
            pass
    return []

# Loaded from policy files (kept from original)
_CRISIS = _load_list("crisis_terms.yaml")
_FIN    = _load_list("abstain_finance_terms.yaml")

# NOTE: Python 're' has no \p{…}; explicitly keep Urdu/Arabic range U+0600–U+06FF and Latin \w.
_SPLIT_RE = re.compile(r"[^\w\u0600-\u06FF]+")

def _tokenize(s: str) -> List[str]:
    return [tok for tok in _SPLIT_RE.split(s) if tok]

def _term_hits(text_low: str, terms: List[str]) -> List[str]:
    toks = _tokenize(text_low)
    hits = []
    for term in terms:
        words = _tokenize(term)
        if not words:
            continue
        # in-order (not necessarily adjacent)
        i = 0
        ok = True
        for w in words:
            try:
                j = toks.index(w, i)
                i = j + 1
            except ValueError:
                ok = False
                break
        if ok:
            hits.append(term)
    return hits

def detect_route(text: str) -> Dict[str, object]:
    """
    Route detector with:
      - broadened crisis triggers (Urdu/English, early return)
      - neutral/brand allowlist (early assist)
      - wellness allowlist (prevents finance false positives)
      - finance abstain requires BOTH finance context AND tip-like intent
      - default: assist
    """
    t = (text or "")
    low = t.lower().strip()
    if not low:
        return {"route": "assist", "matched_terms": []}

    # ---- Crisis: broaden Urdu/English triggers (early return) ----
    # Combine file-based crisis terms with inline crisis keywords
    crisis_inline = (
        # Urdu
        "مجھے فوری مدد", "مجھے فوری مدد کی ضرورت", "خودکشی", "جان لینے", "مرنا چاہتا", "نقصان پہنچانا",
        # English
        "suicide", "kill myself", "end my life", "self harm", "hurt myself",
        "emergency help", "need urgent help"
    )
    crisis_hits_file   = _term_hits(low, _CRISIS)
    crisis_hits_inline = [kw for kw in crisis_inline if kw in low]
    if crisis_hits_file or crisis_hits_inline:
        hits = (crisis_hits_file + crisis_hits_inline)[:5]
        return {"route": "crisis", "matched_terms": hits}

    # ---- Safe brand/neutral allowlist (early return to assist) ----
    safe_phrases = (
        "what is sukoonai", "sukoonai", "who are you", "about you",
        "about sukoonai", "privacy", "status"
    )
    if any(p in low for p in safe_phrases):
        return {"route": "assist", "reason": "neutral-allowlist", "matched_terms": []}

    # ---- Wellness allowlist to avoid finance false positives ----
    wellness_inline = (
        "grounding exercise", "breathing exercise",
        "box breathing", "mindfulness exercise", "relaxation exercise",
        "progressive muscle relaxation", "pmr"
    )
    if any(w in low for w in wellness_inline):
        return {"route": "assist", "reason": "wellness-allowlist", "matched_terms": []}

    # ---- Wellness allowlist (kept from original, prevents finance false-positives) ----
    wellness = (
        "grounding", "grounding exercise", "breathing", "box breathing", "mindfulness",
        "meditation", "anxiety", "panic", "relax",
        "سانس", "گراؤنڈنگ", "مدیتیشن", "پرسکون", "ریلیکس"
    )
    if any(w in low for w in wellness):
        return {"route": "assist", "reason": "wellness-allowlist", "matched_terms": []}

    # ---- Roman-Urdu wellness allowlist (narrow, reversible) ----
    # Only Roman-Urdu tokens here (no plain English words). Also ensure we are NOT in Urdu script.
    roman_wellness_inline = (
        "saans", "gehri saans", "saans ki", "mashq",
        "ghabrahat", "bechaini", "sakoon", "sukoon",
        "tawajjo", "tawajjoh", "tawajju",
        "5-4-3-2-1", "54321"
    )
    if any(w in low for w in roman_wellness_inline) and not any("\u0600" <= ch <= "\u06FF" for ch in t):
        return {"route": "assist", "reason": "wellness-allowlist-roman", "matched_terms": []}

    # ---- Finance abstain requires BOTH finance-context AND tip-like intent ----
    # Consider both file-based finance terms and inline finance vocabulary
    finance_terms_inline = (
        "stock", "stocks", "price target", "buy", "sell", "crypto", "ticker",
        "return", "yield", "forex", "investment", "trading", "day trade",
        "bitcoin", "eth", "bond", "mutual fund", "portfolio", "roi", "dividend",
        "nifty", "s&p", "nasdaq", "kse", "psx", "option", "futures"
    )
    tip_like = ("which", "should i", "recommend", "prediction", "target", "price", "buy now", "sell now")

    finance_hits_file = _term_hits(low, _FIN)
    finance_trigger = bool(finance_hits_file) or any(ft in low for ft in finance_terms_inline)
    tip_trigger = any(tp in low for tp in tip_like)

    if finance_trigger and tip_trigger:
        return {
            "route": "abstain",
            "reason": "finance-tip",
            "matched_terms": finance_hits_file[:5] if finance_hits_file else []
        }

    # Default
    return {"route": "assist", "matched_terms": []}
