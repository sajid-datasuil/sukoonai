from typing import Dict, Any, List
import time
import re
import unicodedata  # normalize incoming user text
from pathlib import Path

# --- tiny retrieval fallback (≤3) if your main retriever isn't wired ---
def _mini_tokens(s: str) -> set:
    return set(re.findall(r"[\w\u0600-\u06FF]{2,}", (s or "").lower()))

_KB_FALLBACK = [
    {
        "id": "kb-breathe",
        "title": "گہری سانس (Box Breathing)",
        "excerpt": "ناک سے آہستہ سانس لیں، 4 تک روکیں، منہ سے آہستہ چھوڑیں—2–3 منٹ۔",
    },
    {
        "id": "kb-54321",
        "title": "گراؤنڈنگ 5-4-3-2-1",
        "excerpt": "5 دیکھیں، 4 چھوئیں، 3 سنیں، 2 سونگھیں، 1 چکھیں—توجہ حال میں۔",
    },
    {
        "id": "kb-sleep",
        "title": "نیند کی صفائی",
        "excerpt": "سونے سے 1 گھنٹہ پہلے اسکرین بند، روشنی مدھم، کمرہ ٹھنڈا۔",
    },
]

def _mini_retrieve(query: str, k: int = 3) -> List[Dict]:
    q = _mini_tokens(query)
    items = _KB_FALLBACK
    scored = []
    for it in items:
        score = len(q & (_mini_tokens(it["title"]) | _mini_tokens(it["excerpt"])))
        if score > 0:
            scored.append((score, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    k = max(1, min(k, 3))
    return [it for _, it in scored[:k]] or items[:1]

# --- safety/policy regexes (Urdu + Roman-Urdu + EN) ---
# Crisis: allow punctuation between words; add common Urdu phrasing "نقصان پہنچانا/پہنچانے"
CRISIS_RX = re.compile(
    r"("
    r"خودکشی|زندگی[\s\W]*ختم|جان[\s\W]*لے[\s\W]*ل(?:وں|و)"
    r"|خود[\s\W]*کو[\s\W]*نقصان(?:[\s\W]*پہنچا(?:نا|نے))?"
    r"|مر[\s\W]*نا|مر[\s\W]*جانا"
    r"|suicid(?:e|al)|kill[\s\W]*myself|take[\s\W]*my[\s\W]*life|self[-\s]?harm"
    r"|khud[\s\W]*kushi|khudkushi|apni[\s\W]*jaan|jan[\s\W]*le[\s\W]*loon|jan[\s\W]*le[\s\W]*lu|nuqsan[\s\W]*khud[\s\W]*ko"
    r")",
    re.I,
)
# Finance/speculation: include Urdu script words (کوائن/سٹاک/شیئر/منافع) + Roman-Urdu + EN
ABSTAIN_RX = re.compile(
    r"(کریپٹو|کرپٹو|crypto|bitcoin|btc|altcoin[s]?|"
    r"کوائن|سکہ|سٹاک|شیئر|share[s]?|stock[s]?|"
    r"coin[s]?|tip|signal[s]?|double|doubling|quick[\s\W]*profit|منافع)",
    re.I,
)

# Added: broader finance/out-of-scope pattern for deterministic ABSTAIN (kept from existing file)
FINANCE_PAT = re.compile(
    r"(کریپٹو|کرپٹو|crypto|bitcoin|btc|altcoins?|trading|trade|"
    r"forex|stocks?|signal[s]?|get\s*rich|doubl(e|ing)\s+money)",
    re.I,
)

from app.safety.router import SafetyRouter
from app.ops.cost_meter import CostMeter
from app.llm.openai_client import LLMClient
# SNIPPET APPLIED: route TTS through factory (engine decided by SUKOON_TTS_ENGINE)
from app.audio.tts import synth as tts_synth  # provides {"tts_path": "...", "duration_sec": ...}
from app.retrieval.mini import retrieve as kb_retrieve

safety = SafetyRouter()
meter = CostMeter(config_path="configs/costing.yaml")
llm = LLMClient()

SYSTEM_URDU = (
    "آپ سکوون اے آئی کے مددگار ہیں — اردو کو ترجیح دیں، سادہ، ہمدرد لہجہ۔ "
    "تشخیص یا ادویات پر رائے نہ دیں۔ "
    "خطرے کی صورت میں ہمیشہ محفوظ رہنمائی دیں۔ "
    "اگر سوال دائرہ کار سے باہر ہو تو 'ABSTAIN' کریں۔"
)

CRISIS_REPLY_URDU = (
    "مجھے افسوس ہے کہ آپ مشکل میں ہیں۔ ابھی فوراً اپنی حفاظت کو ترجیح دیں۔ "
    "اگر آپ کو خود کو یا کسی اور کو نقصان پہنچانے کا خیال آ رہا ہے تو "
    "براہِ کرم مقامی ہنگامی سروس یا قریبی معتمد شخص سے فوراً رابطہ کریں۔ "
    "پاکستان میں آپ 1122 یا قریبی ہسپتال سے رابطہ کریں۔"
)

def _extract_tts_path(tts_out: Any) -> str | None:
    """Accept either a plain path or a dict with {'tts_path': ...}."""
    if isinstance(tts_out, dict):
        return tts_out.get("tts_path")
    return tts_out

def _mk_timings_alias(metrics: Dict[str, Any]) -> Dict[str, int]:
    """
    Create Stage-1 'timings' alias expected by the drill script from our 'metrics'.
    We don't track plan/handoff separately here, so set them to 0.
    """
    return {
        "safety_ms": int(metrics.get("safety_ms", 0)),
        "plan_ms": 0,
        "tts_ms": int(metrics.get("tts_ms", 0)),
        "handoff_ms": 0,
        "total_ms": int(metrics.get("total_ms", 0)),
    }

def run_turn(user_text: str, lang_hint: str = "ur") -> Dict[str, Any]:
    # --- Normalize once to stabilize Urdu/Arabic forms (NFC) ---
    text_in = unicodedata.normalize("NFC", user_text or "")

    # 1) Pre-LLM safety
    t0 = time.perf_counter()
    s = safety.detect(text_in)
    safety_ms = int((time.perf_counter() - t0) * 1000)

    # === Stage-1: Crisis fast-path (no LLM) ===
    if s.get("crisis") or CRISIS_RX.search(text_in):
        meter.log_event(component="web", unit="per_message", units=1, metadata={"route": "crisis"})
        t_tts0 = time.perf_counter()
        tts_out = tts_synth(CRISIS_REPLY_URDU, lang_hint=lang_hint)
        tts_ms = int((time.perf_counter() - t_tts0) * 1000)
        tts_path = _extract_tts_path(tts_out)
        # Minimal evidence for UX grounding (≤3)
        evidence = [{"id": "kb-breathe", "title": "گہری سانس (Box Breathing)", "excerpt": "ناک سے 4… روکیں… چھوڑیں—2 منٹ۔"}]
        metrics = {
            "safety_ms": safety_ms,
            "retrieval_ms": 0,
            "llm_ms": 0,
            "tts_ms": tts_ms,
            "total_ms": int(safety_ms + tts_ms),
            "tts_rtf": 0.0,
        }
        resp = {
            "ok": True,
            "route": "crisis",
            "safety": {**s, "crisis": True},
            "answer": CRISIS_REPLY_URDU,
            "abstain": True,
            "usage": {},
            "tts_path": tts_path,
            "metrics": metrics,
            "evidence": evidence[:3],
        }
        # Stage-1 visibility aliases
        resp["latency_ms"] = metrics
        resp["timings"] = _mk_timings_alias(metrics)
        return resp

    # === Stage-1: ABSTAIN for speculative finance ===
    if ABSTAIN_RX.search(text_in) or FINANCE_PAT.search(text_in):
        safe_msg = "اس سوال پر میں رائے نہیں دے سکتا/سکتی۔ براہِ کرم مالی مشورے کے لیے مستند ماہر سے رجوع کریں۔"
        t_tts0 = time.perf_counter()
        tts_out = tts_synth(safe_msg, lang_hint=lang_hint)
        tts_ms = int((time.perf_counter() - t_tts0) * 1000)
        tts_path = _extract_tts_path(tts_out)
        meter.log_event(
            component="web",
            unit="per_message",
            units=1,
            metadata={"abstain": True, "reason": "finance"},
        )
        metrics = {
            "safety_ms": safety_ms,
            "retrieval_ms": 0,
            "llm_ms": 0,
            "tts_ms": tts_ms,
            "total_ms": int(safety_ms + tts_ms),
            "tts_rtf": 0.0,
        }
        resp = {
            "ok": True,
            "route": "abstain",
            "safety": s,
            "answer": safe_msg,
            "abstain": True,
            "usage": {},
            "tts_path": tts_path,
            "metrics": metrics,
            "evidence": [],
        }
        resp["latency_ms"] = metrics
        resp["timings"] = _mk_timings_alias(metrics)
        return resp

    # 2) Deterministic mini-retrieval (evidence-only)
    t1 = time.perf_counter()
    try:
        evidence = kb_retrieve(text_in, k=3)
    except Exception:
        evidence = []
    if not evidence:
        evidence = _mini_retrieve(text_in, k=3)
    retrieval_ms = int((time.perf_counter() - t1) * 1000)
    meter.log_event(
        component="retrieval",
        unit="per_query",
        units=1,
        metadata={"k": len(evidence), "hits": [e["id"] for e in evidence]},
    )

    # 3) LLM — Urdu-first; ABSTAIN instruction, evidence-conditioned
    ev_lines = "\n".join([f"- {e['title']}: {e['excerpt']}" for e in evidence])
    prompt = (
        "If user intent is out of scope or clinical judgement is needed, reply exactly with 'ABSTAIN'. "
        "Use ONLY the following evidence; do not add claims beyond it:\n" + ev_lines +
        "\nRespond concisely in Urdu first."
    )
    try:
        t2 = time.perf_counter()
        text, usage = llm.chat(
            system_prompt=SYSTEM_URDU + " " + prompt,
            user_text=text_in,
            lang_hint=lang_hint,
        )
        llm_ms = int((time.perf_counter() - t2) * 1000)
    except Exception as e:
        # Failure policy: never 500 — safe Urdu fallback; log error_reason
        safe_msg = "اس وقت میری سروس دستیاب نہیں۔ براہِ کرم کچھ دیر بعد دوبارہ کوشش کریں یا مستند ماہر سے رابطہ کریں۔"
        meter.log_event(
            component="llm",
            unit="per_error",
            units=1,
            metadata={"error_reason": type(e).__name__},
        )
        t_tts0 = time.perf_counter()
        tts_out = tts_synth(safe_msg, lang_hint=lang_hint)
        tts_ms = int((time.perf_counter() - t_tts0) * 1000)
        tts_path = _extract_tts_path(tts_out)
        metrics = {
            "safety_ms": safety_ms,
            "retrieval_ms": retrieval_ms,
            "llm_ms": 0,
            "tts_ms": tts_ms,
            "total_ms": int(safety_ms + retrieval_ms + tts_ms),
            "tts_rtf": 0.0,
        }
        resp = {
            "ok": False,
            "route": "assist",
            "safety": s,
            "retrieval": {"evidence": evidence},
            "answer": safe_msg,
            "abstain": False,
            "usage": {},
            "tts_path": tts_path,
            "metrics": metrics,
        }
        resp["evidence"] = evidence[:3]
        resp["latency_ms"] = metrics
        resp["timings"] = _mk_timings_alias(metrics)
        return resp

    # 4) ABSTAIN handling (model-driven)
    abstain = text.strip().upper().startswith("ABSTAIN")
    if abstain:
        safe_msg = "میں اس موضوع پر رائے دینے سے معذرت خواہ ہوں۔ براہِ کرم مستند ماہر سے رجوع کریں۔"
        t_tts0 = time.perf_counter()
        tts_out = tts_synth(safe_msg, lang_hint=lang_hint)
        tts_ms = int((time.perf_counter() - t_tts0) * 1000)
        tts_path = _extract_tts_path(tts_out)
        meter.log_event(component="web", unit="per_message", units=1, metadata={"abstain": True})
        metrics = {
            "safety_ms": safety_ms,
            "retrieval_ms": retrieval_ms,
            "llm_ms": llm_ms,
            "tts_ms": tts_ms,
            "total_ms": int(safety_ms + retrieval_ms + llm_ms + tts_ms),
            "tts_rtf": 0.0,
        }
        resp = {
            "ok": True,
            "route": "abstain",
            "safety": s,
            "answer": safe_msg,
            "abstain": True,
            "usage": {},
            "tts_path": tts_path,
            "metrics": metrics,
            "evidence": [],
        }
        resp["latency_ms"] = metrics
        resp["timings"] = _mk_timings_alias(metrics)
        return resp

    # 5) Meter tokens if available
    pt = usage.get("prompt_tokens") or 0
    ct = usage.get("completion_tokens") or 0
    if pt:
        meter.log_event(
            component="llm:gpt_4o_mini",
            unit="input_token",
            units=pt,
            metadata={"model": "gpt-4o-mini"},
        )
    if ct:
        meter.log_event(
            component="llm:gpt_4o_mini",
            unit="output_token",
            units=ct,
            metadata={"model": "gpt-4o-mini"},
        )

    # 6) TTS output + timings
    try:
        t3 = time.perf_counter()
        tts_out = tts_synth(text, lang_hint=lang_hint)
        tts_path = _extract_tts_path(tts_out)  # may be None if engine missing
        tts_status = "ok" if tts_path else "degraded:no_sapi"  # <-- status flag
        tts_ms = int((time.perf_counter() - t3) * 1000)
    except Exception as e:
        safe_msg = "آواز بنانے میں مسئلہ آیا؛ میں متن کے طور پر جواب دے رہا/رہی ہوں۔"
        meter.log_event(
            component="tts",
            unit="per_error",
            units=1,
            metadata={"error_reason": type(e).__name__},
        )
        tts_out = {}  # ensure downstream duration_sec logic is safe
        tts_path = None
        tts_status = "degraded:no_sapi"
        tts_ms = 0

    # --- precise totals + timings row (additive, no schema break) ---
    duration_sec = (tts_out or {}).get("duration_sec") if isinstance(tts_out, dict) else None
    llm_ms_val = int(locals().get("llm_ms") or 0)
    total_ms = int(safety_ms + retrieval_ms + llm_ms_val + tts_ms)
    tts_rtf = round((float(duration_sec or 0.0)) / max(0.001, tts_ms / 1000.0), 3)
    try:
        meter.log_timings(
            route="assist",
            timings={
                "safety_ms": safety_ms,
                "retrieval_ms": retrieval_ms,
                "llm_ms": llm_ms_val,
                "tts_ms": tts_ms,
                "total_ms": total_ms,
                "tts_rtf": tts_rtf,
            },
        )
    except Exception:
        pass

    resp = {
        "ok": True,
        "route": "assist",
        "safety": s,
        "retrieval": {"evidence": evidence},
        "answer": text,
        "abstain": False,
        "usage": usage,
        "tts_path": tts_path,
        "tts_status": tts_status,
        "metrics": {
            "safety_ms": safety_ms,
            "retrieval_ms": retrieval_ms,
            "llm_ms": llm_ms_val,
            "tts_ms": tts_ms,
            "total_ms": total_ms,
            "tts_rtf": tts_rtf,
        },
    }
    # Stage-1 visibility aliases for the drills/UX
    resp["evidence"] = (evidence or [])[:3]            # ≤3 items
    resp["latency_ms"] = resp["metrics"]               # legacy alias
    resp["timings"] = _mk_timings_alias(resp["metrics"])  # Stage-1 alias
    return resp

# ---- Stage-1 shim: keep legacy imports working ----
def turn_handler(*args, **kwargs):
    return run_turn(*args, **kwargs)
