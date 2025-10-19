"""
Planner prompt utilities.

Loads config from YAML and renders a compact, speakable planner prompt.
This module does not perform any network calls.

Safety note: Do not add any medical advice templates here. Stick to evidence-only prompts.
"""
from __future__ import annotations

import pathlib
import yaml
from typing import Dict, Any

_CONFIG_PATH = pathlib.Path("configs/planner.yaml")

class PlannerConfig:
    def __init__(self, raw: Dict[str, Any]) -> None:
        self.raw = raw
        self.rules = tuple(raw.get("style", {}).get("rules", []))
        self.refusals = raw.get("refusal_templates", {})
        self.allow = set(raw.get("topic_allowlist", []))
        self.citation_fmt = raw.get("speakable_citation_format", "Source: {source}, {year}")
        self.registry = raw.get("evidence_registry", {})

def load_config() -> PlannerConfig:
    data = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8"))
    return PlannerConfig(data)

def render_planner_prompt(user_text: str, locale: str, topic: str) -> str:
    """
    Render a compact planner prompt string with embedded style rules.
    The planner (LLM or mock) should output strict Decision JSON.
    """
    cfg = load_config()
    rules = "\n".join(f"- {r}" for r in cfg.rules)
    lang_hint = "Urdu+English code-switch allowed." if locale.lower() in ("ur", "roman-ur", "ur/en") else "English."
    return (
        "ROLE: Mental-wellness voice planner for Anxiety & Depression only.\n"
        f"TOPIC: {topic}\n"
        f"LOCALE: {locale} ({lang_hint})\n"
        "STYLE RULES:\n"
        f"{rules}\n"
        "OUTPUT: Strict Decision JSON with fields: actions[], evidence_ids[], latency_ms{}, meta{}.\n"
        "CONSTRAINTS: No diagnosis. No medication advice. ABSTAIN if out-of-scope or weak evidence.\n"
        f"USER: {user_text}\n"
    )

def speakable_citation(evidence_id: str) -> str:
    """Return a speakable citation line for a known evidence id (Week-2 registry only)."""
    cfg = load_config()
    meta = cfg.registry.get(evidence_id, {})
    if not meta:
        return ""
    return cfg.citation_fmt.format(source=meta.get("source", "Evidence"), year=meta.get("year", ""))
