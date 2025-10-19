# app/redaction.py  (extend with a chat-safe sanitizer)
# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from pathlib import Path
from typing import List, Dict, Any

# Symbolic placeholders we use in-chat
PLACEHOLDERS = ("⟪intent⟫", "⟪means⟫", "⟪time⟫")

def _load_blocklist_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

def redact_text(s: str) -> str:
    # existing redaction (emails/phones/etc.) may already be here in your file
    s = re.sub(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', '[REDACTED_EMAIL]', s)
    s = re.sub(r'\b(?:\+?\d[\d\s\-]{8,})\b', '[REDACTED_PHONE]', s)
    return s

def sanitize_for_chat(text: str, blocklist_path: str = "configs/blocklist_chat.yaml") -> str:
    """
    Replace any sensitive real tokens with symbolic placeholders
    so content is safe to paste into ChatGPT. Deterministic and local.
    """
    cfg = _load_blocklist_yaml(Path(blocklist_path))
    # lists of real tokens to mask; DO NOT paste real tokens into chat
    intents: List[str] = cfg.get("intent", [])
    means:   List[str] = cfg.get("means", [])
    times:   List[str] = cfg.get("time", [])

    def _multi_replace(s: str, terms: List[str], placeholder: str) -> str:
        if not terms: return s
        # word-boundary-ish, case-insensitive; Urdu terms can be plain substring
        pat = re.compile("|".join(re.escape(t) for t in terms if t), flags=re.I)
        return pat.sub(placeholder, s)

    out = text
    out = _multi_replace(out, intents, "⟪intent⟫")
    out = _multi_replace(out, means,   "⟪means⟫")
    out = _multi_replace(out, times,   "⟪time⟫")
    return redact_text(out)
