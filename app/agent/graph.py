# -*- coding: utf-8 -*-
"""
Week-2 planner graph (revised for Week-4 MS-1 safety gate).

Order: intent_gate -> planner (templates) -> safety gate -> speak
Emits strict Decision JSON. Uses mock evidence ids for Week-2/3 paths; safety gate
now loads bilingual refusals and deterministic crisis flow (WhatsApp default).
"""

from __future__ import annotations
import time
from typing import Dict, Any, List

from app.agent.intent import classify_topic
from app.agent.prompts import render_planner_prompt, speakable_citation

# --- ADD NEAR TOP (imports) ---
from app.policies import shim as safety_shim  # existing lightweight shim (kept for back-compat)

# --- Week-4 MS-1: Safety Node wiring (additions) ---
from pathlib import Path
import json, yaml
from pydantic import BaseModel

# ---------- NEW: load planner knobs ----------
def _load_yaml(path: str) -> dict:
    p = Path(path)
    if p.exists():
        try:
            return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}
    return {}

_PLANNER = _load_yaml("configs/planner.yaml")  # min_score/top_k/abstain/no_network

# ---------- NEW: tiny TTS cache matcher with safe defaults ----------
class _TTSCache:
    def __init__(self, path: str):
        self.cfg = _load_yaml(path)
        self.rules: List[tuple[str, List[str]]] = []

        # 1) Try to load from YAML
        yaml_rules = ((self.cfg.get("match") or {}).get("rules") or []) if isinstance(self.cfg, dict) else []
        for r in yaml_rules:
            if not isinstance(r, dict):
                continue
            key = (r.get("key") or "generic")
            toks = [str(s).lower() for s in (r.get("contains") or []) if s]
            if toks:
                self.rules.append((key, toks))

        # 2) If nothing loaded, fall back to sensible defaults
        if not self.rules:
            self.rules = [
                ("box_breathing", [
                    "breathe in 4", "hold 4", "box breathing",
                    "باکس", "سانس", "روکیں"
                ]),
                ("54321", [
                    "5-4-3-2-1", "54321", "grounding",
                    "گراؤنڈنگ", "پانچ چیزیں", "چار", "تین", "دو", "ایک"
                ]),
            ]

        # 3) Always add a tiny citation rule so evidence “Source:” lines cache
        self.rules.append(("citation", ["source: gad-7", "source: phq-9"]))

    def hits_for_actions(self, actions: list) -> int:
        hits = 0
        for a in actions or []:
            if not isinstance(a, dict) or a.get("type") != "say":
                continue
            txt = (a.get("text") or "").lower()
            if any(any(tok in txt for tok in toks) for _, toks in self.rules):
                hits += 1
        return hits

_TTS = _TTSCache("configs/tts_cache.yaml")
# ----------------------------------------------

class CrisisDecision(BaseModel):
    crisis: bool
    signals: dict
    actions: dict

class SafetyNode:
    """
    Deterministic safety/guardrail gate:
      - Refusals (medical/diagnosis/medication/legal/out_of_scope) in Urdu/English
      - Crisis flow → fixed JSON + WhatsApp outreach + neutral speech line
    """
    def __init__(self, policy_map: str, refusal_yaml: str, crisis_flow: str):
        self.rules = yaml.safe_load(Path(policy_map).read_text(encoding="utf-8"))
        self.templates = yaml.safe_load(Path(refusal_yaml).read_text(encoding="utf-8"))["templates"]
        self.crisis_flow = json.loads(Path(crisis_flow).read_text(encoding="utf-8"))
        self.schema = self.crisis_flow["decision_schema"]

    def _render_refusal(self, template_key: str, lang: str = "en") -> str:
        """
        Robust renderer:
        - Accepts "section.key" or bare keys
        - Falls back to templates.generic.generic or .fallback if missing
        - Falls back to English if requested lang unavailable
        """
        # Parse "sect.key" or default to generic
        if "." in template_key:
            sect, key = template_key.split(".", 1)
        else:
            sect, key = "generic", "generic"

        T = self.templates

        # Section fallback
        if sect not in T:
            sect = "generic"
        sect_map = T.get(sect, {})

        # Key fallback preference: generic → fallback → first available
        if key not in sect_map:
            if "generic" in sect_map:
                key = "generic"
            elif "fallback" in sect_map:
                key = "fallback"
            else:
                key = next(iter(sect_map.keys()), "generic")

        lang_map = sect_map.get(key, {})
        # Language fallback: requested → en → any available
        tpl = (
            lang_map.get(lang)
            or lang_map.get("en")
            or (next(iter(lang_map.values())) if isinstance(lang_map, dict) and lang_map else "")
        )

        # Optional WA follow-up line (per-lang, fallback to en)
        follow = (
            sect_map.get(key, {}).get(f"whatsapp_followup_{lang}")
            or sect_map.get(key, {}).get("whatsapp_followup_en")
        )
        return f"{tpl} " + (follow or "")

    def _build_crisis_decision(self, signals: dict) -> dict:
        decision = {
            "crisis": True,
            "signals": {
                "intent": signals.get("intent", ""),
                "plan": signals.get("plan", ""),
                "means": signals.get("means", ""),
                "timeframe": signals.get("timeframe", ""),
                "location": signals.get("location", "")
            },
            "actions": {
                "connect_human": True,
                "send_whatsapp": True,
                "resources": ["national_hotline", "nearest_hospital"]
            }
        }
        # Validate structure (pydantic)
        CrisisDecision.model_validate(decision)
        return decision

    def __call__(self, state: dict) -> dict:
        """
        State must carry: `policy_tags` (list[str]), `lang` ('en'|'ur'),
        optional `crisis_signals`.
        """
        tags = set(state.get("policy_tags", []))
        lang = state.get("lang", "en")
        for rule in self.rules["rules"]:
            if rule["tag"] in tags:
                if rule["action"] == "refuse":
                    text = self._render_refusal(rule["template"], lang)
                    state.update({"final_text": text, "actions": {"whatsapp": True}, "halt": True})
                    return state
                if rule["action"] == "crisis_flow":
                    decision = self._build_crisis_decision(state.get("crisis_signals", {}))
                    # Minimal, neutral verbal line; do not repeat harmful details.
                    voice_line = "I’m here with you. I will connect you to a trained helper now and send support options to your WhatsApp."
                    if lang == "ur":
                        voice_line = "میں آپ کے ساتھ ہوں۔ میں ابھی آپ کو تربیت یافتہ مدد سے ملا رہا/رہی ہوں اور واٹس ایپ پر مدد کے آپشنز بھیج رہا/رہی ہوں۔"
                    state.update({
                        "final_text": voice_line,
                        "decision_json": decision,
                        "actions": {"connect_human": True, "whatsapp": True},
                        "halt": True
                    })
                    return state
        return state  # no safety action → pass through

# Instantiate safety gate (files created in MS-1)
SAFETY = SafetyNode(
    policy_map="app/policies/policy_map.yaml",
    refusal_yaml="app/policies/refusals_ur_en.yaml",
    crisis_flow="app/policies/crisis_flow.json"
)

# --- IN YOUR PIPELINE AFTER planner/intent STEP, BEFORE "speak" ---
def _infer_policy_tags(user_text: str, topic: str) -> List[str]:
    """
    Offline, deterministic tagger used only to drive the SafetyNode.
    Adds Urdu + English heuristics aligned with the eval classifier.
    """
    t = (user_text or "").lower()
    tags: List[str] = []

    # Crisis (Urdu + English; handle verb morphology)
    ur_crisis_self = ["خودکشی", "خود کشی", "اپنے آپ کو نقصان", "خود کو نقصان", "خود کو مار", "جان لینا"]
    ur_crisis_other = ["کسی کو نقصان", "جان سے مار", "قتل", "تشدد کرنا"]
    if any(k in t for k in ["hurt myself", "hurting myself", "kill myself", "suicide", "self-harm"]) or any(k in t for k in ur_crisis_self):
        tags.append("crisis.self_harm")
    if any(k in t for k in ["harm someone", "harming someone"]) or any(k in t for k in ur_crisis_other):
        tags.append("crisis.harm_to_others")

    # Clinical / medication / legal (Urdu + English)
    ur_diag = ["تشخیص", "علامات کی بنیاد پر تشخیص", "تشخیص کریں"]
    ur_med  = ["دوائی", "دوائ", "ادویات", "دوا", "خوراک"]
    ur_legal = ["قانونی"]

    en_diag_q = [
        "do i have depression", "do i have anxiety",
        "am i depressed", "am i anxious",
        "tell me if i have depression", "tell me if i have anxiety"
    ]
    ur_diag_q_hit = ("کیا" in t) and (("افسردگی" in t) or ("اضطراب" in t))

    if ("diagnos" in t or "diagnose" in t or any(k in t for k in ur_diag)
        or any(k in t for k in en_diag_q) or ur_diag_q_hit):
        tags.append("clinical.ask_diagnosis")
    if any(k in t for k in ["medicine", "medication", "dose", "dosing"]) or any(k in t for k in ur_med):
        tags.append("clinical.ask_medication")
    if "legal" in t or any(k in t for k in ur_legal):
        tags.append("legal.request")

    # Out of scope
    if topic == "other" or "outside" in t or "دائرہ کار" in t:
        tags.append("scope.out_of_scope")

    return list(dict.fromkeys(tags))

def safety_node(state: dict) -> dict:
    """
    Safety/guardrail node: enforces refusal/crisis policies BEFORE speak/TTS.
    Expects 'state' to contain {'user_text', 'topic', 'decision'} and returns updated state.
    """
    user_text = state.get("user_text", "")
    topic = state.get("topic")
    decision = state.get(
        "decision",
        {"actions": [], "risk": {"level": "none", "triggers": []}, "meta": {}}
    )

    # Keep legacy shim behavior (no-op if shim decides nothing)
    decision = safety_shim.apply_policies(decision, user_text=user_text, topic=topic)

    # Week-4 SafetyNode (deterministic)
    policy_tags = _infer_policy_tags(user_text, topic)
    lang = decision.get("lang", "en")
    s = {"policy_tags": policy_tags, "lang": lang, "crisis_signals": {"intent": "unsure"}}
    out = SAFETY(s)

    if out.get("halt"):
        # Merge halt into decision structure the rest of the graph expects
        decision["actions"] = [{"type": "say", "text": out["final_text"]}]
        decision.setdefault("meta", {})["safety_halt"] = True
        if "decision_json" in out:
            # Attach crisis decision JSON for logging/handoff
            decision["meta"]["crisis_decision"] = out["decision_json"]
        return {"user_text": user_text, "topic": topic, "decision": decision}

    # No safety intervention
    return {"user_text": user_text, "topic": topic, "decision": decision}
# --- End MS-1 additions ---

# Mock planner for Week-2 (no network). Replace with adapter in Week-3/4.
def _mock_planner(user_text: str, topic: str) -> Dict[str, Any]:
    # Minimal deterministic plan with a single evidence id + speakable source line + extra cacheable line.
    if topic == "anxiety":
        evidence_ids = ["gad7"]
        speakable = speakable_citation("gad7") or "Source: GAD-7"
        actions = [
            {"type": "say", "text": "Let’s try a quick grounding. 1) Breathe in 4. 2) Hold 4. 3) Out 4. 4) Hold 4."},
            {"type": "say", "text": "Let's do 5-4-3-2-1 grounding."},
            {"type": "say", "text": speakable},
        ]
    elif topic == "depression":
        evidence_ids = ["phq9"]
        speakable = speakable_citation("phq9") or "Source: PHQ-9"
        actions = [
            {"type": "say", "text": "Low mood can be hard. Try this. 1) Name one good thing today. 2) Take three slow breaths."},
            {"type": "say", "text": "Let's do 5-4-3-2-1 grounding."},
            {"type": "say", "text": speakable},
        ]
    else:
        evidence_ids = []
        actions = []

    return {"actions": actions, "evidence_ids": evidence_ids}

def plan_say(user_text: str, locale: str = "en") -> Dict[str, Any]:
    t0 = time.perf_counter()
    # vad/asr are mocked by the /say endpoint in Week-2; timers remain present for benching.
    t_vad = 5.0
    t_asr = 5.0

    gate = classify_topic(user_text)
    topic = gate["topic"]

    # --- Heuristic fallback when intent classifier returns "other" ---
    if topic == "other":
        u = (user_text or "").lower()

        # Depression cues (English + Urdu) — check these FIRST
        dep_en = ["depress", "sad", "low mood", "hopeless", "unmotivated", "anhedonia"]
        dep_ur = ["افسردگی", "مایوسی", "دل اداس", "حوصلہ نہیں"]
        if any(w in u for w in dep_en) or any(w in u for w in dep_ur):
            topic = "depression"
        else:
            # Anxiety cues (English + Urdu, incl. grounding/breathing/5-4-3-2-1)
            anx_en = ["anxiety", "worry", "worried", "restless", "panic",
                      "grounding", "5-4-3-2-1", "54321", "breath", "breathe", "breathing"]
            anx_ur = ["سانس", "گراؤنڈ", "گراؤنڈنگ", "پریشانی", "گھبراہٹ"]
            if any(w in u for w in anx_en) or any(w in u for w in anx_ur):
                topic = "anxiety"

    if topic == "other":
        decision = {
            "session_id": "local",
            "turn_id": "1",
            "timestamp_ms": int(time.time() * 1000),
            "lang": locale,
            "intent": "out_of_scope",
            "risk": {"level": "low", "triggers": []},
            "actions": [
                {"type": "say", "text": "I’m trained for anxiety and depression topics. I can’t answer that safely. Would you like a short grounding exercise?"},
                # WhatsApp outreach by default; policy gate handles consent defaults.
                {"type": "whatsapp", "template": "hotline_pk", "params": {"number": "+92xxxxxxxx", "hours": "24/7", "send": True}}
            ],
            "evidence_ids": [],
            "latency_ms": {"vad": t_vad, "asr": t_asr, "plan": 2.0, "tts": 20.0, "mouth_to_ear": 60.0},
            "cost": {"tokens_in": 0, "tokens_out": 0, "est_cogs_per_min": 0.0},
            "meta": {"model_planner": "mock", "asr_backend": "mock", "tts_backend": "mock", "consent": None},
        }

        # ---- cache metrics & planner knobs after actions are set ----
        total_say = sum(1 for a in decision.get("actions", []) if isinstance(a, dict) and a.get("type") == "say")
        hits = _TTS.hits_for_actions(decision.get("actions"))
        cache_hit = hits > 0
        decision["cost"].update({
            "tts_cache_hit": cache_hit,
            "tts_cache_hits": hits,
            "tts_total_say": total_say,
            "planner_min_score": float(_PLANNER.get("min_score", 0.45)),
            "planner_top_k": int(_PLANNER.get("top_k", 3)),
            "planner_no_network": bool(_PLANNER.get("no_network", True)),
        })

        # --- Safety node hook (after intent/planner, before speak/output) ---
        state = {"user_text": user_text, "topic": "other", "decision": decision}
        state = safety_node(state)
        return state["decision"]

    # Allowed topic -> render template prompt (for traceability) then mock plan
    _ = render_planner_prompt(user_text, locale, topic)  # recorded in logs for transparency if needed
    plan = _mock_planner(user_text, topic)

    t_plan = 10.0
    t_tts = 20.0
    mouth = 100.0
    decision = {
        "session_id": "local",
        "turn_id": "1",
        "timestamp_ms": int(time.time() * 1000),
        "lang": locale,
        "intent": topic,
        "risk": {"level": "low", "triggers": []},
        "actions": plan["actions"],
        "evidence_ids": plan["evidence_ids"],
        "latency_ms": {"vad": t_vad, "asr": t_asr, "plan": t_plan, "tts": t_tts, "mouth_to_ear": mouth},
        "cost": {"tokens_in": 0, "tokens_out": 0, "est_cogs_per_min": 0.0},
        "meta": {"model_planner": "mock", "asr_backend": "mock", "tts_backend": "mock", "consent": None},
    }

    # ---- cache metrics & planner knobs after actions are set ----
    total_say = sum(1 for a in decision.get("actions", []) if isinstance(a, dict) and a.get("type") == "say")
    hits = _TTS.hits_for_actions(decision.get("actions"))
    cache_hit = hits > 0
    decision["cost"].update({
        "tts_cache_hit": cache_hit,
        "tts_cache_hits": hits,
        "tts_total_say": total_say,
        "planner_min_score": float(_PLANNER.get("min_score", 0.45)),
        "planner_top_k": int(_PLANNER.get("top_k", 3)),
        "planner_no_network": bool(_PLANNER.get("no_network", True)),
    })

    # --- Safety node hook (after intent/planner, before speak/output) ---
    state = {"user_text": user_text, "topic": topic, "decision": decision}
    state = safety_node(state)
    return state["decision"]
