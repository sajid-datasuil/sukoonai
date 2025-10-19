# -*- coding: utf-8 -*-
"""
Legacy safety shim kept for back-compat with Week-2/3 tests.
Week-4 introduced a nested refusal YAML (refusals_ur_en.yaml). This shim now:
- Loads the new YAML if available, fallback to old name.
- Flattens nested sections so legacy tags like 'out_of_scope' resolve.
- Never raises KeyError for missing templates; uses a safe default instead.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
import yaml

# ---------- load & normalize templates ----------
def _load_templates() -> Dict[str, Dict[str, str]]:
    candidates = [
        Path("app/policies/refusals_ur_en.yaml"),
        Path("app/policies/refusals.yaml"),  # legacy filename
    ]
    data = {}
    for p in candidates:
        if p.exists():
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            break
    templates = data.get("templates", {}) or {}

    flat: Dict[str, Dict[str, str]] = {}
    for key, val in templates.items():
        # Case 1: already flat (has 'en'/'ur' fields)
        if isinstance(val, dict) and ("en" in val or "ur" in val):
            flat[key] = val
            continue
        # Case 2: nested sections (e.g., 'scope': {'out_of_scope': {...}})
        if isinstance(val, dict):
            for subk, subv in val.items():
                # fully qualified name (e.g., 'scope.out_of_scope')
                flat[f"{key}.{subk}"] = subv
                # legacy aliases for common tags
                if subk in ("out_of_scope", "diagnosis", "medication", "generic"):
                    flat[subk] = subv
                # medical.* convenience
                if key == "medical" and subk in ("diagnosis", "medication"):
                    flat[subk] = subv
    return flat

_TEMPLATES = _load_templates()

_DEFAULT_REFUSAL = {
    "en": "I can’t answer that safely. I focus on anxiety and depression self-help and referrals.",
    "ur": "میں اس کا محفوظ جواب نہیں دے سکتا/سکتی۔ میرا دائرہ کار اضطراب اور افسردگی کی خود مدد اور ریفرلز تک محدود ہے۔",
}

def _template_for(tag: str) -> Dict[str, str]:
    """
    Resolve a template by tag. Supports:
      - 'out_of_scope' (legacy flat)
      - 'scope.out_of_scope' (nested)
      - falls back to default refusal if not found
    """
    if tag in _TEMPLATES:
        return _TEMPLATES[tag]
    # try common expansions
    if f"scope.{tag}" in _TEMPLATES:
        return _TEMPLATES[f"scope.{tag}"]
    if "scope.out_of_scope" in _TEMPLATES:
        return _TEMPLATES["scope.out_of_scope"]
    return _DEFAULT_REFUSAL

def _render_refusal(policy_tag: str, lang: str = "en") -> Dict[str, Any]:
    tpl = _template_for(policy_tag)
    text = tpl.get(lang) or tpl.get("en") or _DEFAULT_REFUSAL["en"]
    return {"type": "say", "text": text}

# ---------- public API (used by graph/tests) ----------
def apply_policies(decision: Dict[str, Any], *, user_text: str = "", topic: str = "") -> Dict[str, Any]:
    """
    Minimal, deterministic guardrail used by Week-2/3 tests. Non-LM, offline.
    - Out-of-scope → refusal line
    - Medication/Dose → refusal line
    - Diagnosis → refusal line
    - Legal → refusal line
    """
    lang = decision.get("lang", "en")
    t = (user_text or "").lower()

    # Out-of-scope by topic
    if topic == "other":
        decision.setdefault("risk", {}).setdefault("triggers", []).append("scope.out_of_scope")
        decision.setdefault("actions", []).append(_render_refusal("out_of_scope", lang))
        return decision

    # Medication
    if any(k in t for k in ("medicine", "medication", "dose", "dosing")):
        decision.setdefault("risk", {}).setdefault("triggers", []).append("clinical.ask_medication")
        decision.setdefault("actions", []).append(_render_refusal("medical.medication", lang))

    # Diagnosis
    if "diagnos" in t:
        decision.setdefault("risk", {}).setdefault("triggers", []).append("clinical.ask_diagnosis")
        decision.setdefault("actions", []).append(_render_refusal("medical.diagnosis", lang))

    # Legal
    if "legal" in t:
        decision.setdefault("risk", {}).setdefault("triggers", []).append("legal.request")
        decision.setdefault("actions", []).append(_render_refusal("legal.generic", lang))

    return decision
