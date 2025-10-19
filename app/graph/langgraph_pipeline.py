# app/graph/langgraph_pipeline.py
from __future__ import annotations
import time, math
import hashlib
from typing import Any, Dict, List, Optional
# --- B2 additions (imports) ---
import yaml
from time import perf_counter
from app.rag.retriever import retriever as bm25

from app.graph.types import DecisionJSON, GraphObj, TraceItem, Metrics
from app.policies.term_gates import detect_route

# --- B3: CKG-lite adapter (new) ---
try:
    from app.ckg import ckg_adapter as ckg
except Exception:  # allow pipeline to run even if adapter/config not present yet
    ckg = None  # type: ignore

# --- B2: load retrieval config ---
try:
    with open("configs/retrieval.yaml", "r", encoding="utf-8") as _f:
        _RET_CFG = yaml.safe_load(_f) or {}
except Exception:
    _RET_CFG = {"top_k": 3, "per_source_cap": 1, "min_chars": 220, "min_score": 0.0, "k1": 1.5, "b": 0.75}

# --- B3: read CKG lambda from adapter/config with safe default ---
_CKG_LAMBDA = 0.25
try:
    if ckg and hasattr(ckg, "get_lambda"):
        _CKG_LAMBDA = float(ckg.get_lambda())
except Exception:
    pass

# Tiny timing helper
class _Timer:
    def __enter__(self):
        # Use ns precision to avoid 0ms for very fast nodes
        self.t0 = time.perf_counter_ns()
        return self
    def __exit__(self, *exc):
        dt_ns = time.perf_counter_ns() - self.t0
        # ceil to next ms and enforce a 1ms floor for visibility
        self.ms = max(1, int(math.ceil(dt_ns / 1_000_000)))

def _node_input(ctx: Dict[str, Any]) -> Dict[str, Any]:
    # Here we could normalize text, scripts, etc. (B9 later)
    return ctx

def _node_policy_gate(ctx: Dict[str, Any]) -> Dict[str, Any]:
    # Keep the *same* term gates (non-negotiable). We only *observe* here.
    text = ctx.get("text", "")
    gate = detect_route(text)
    ctx["route"] = gate.get("route", "assist")
    ctx["gate_detail"] = {"route": ctx["route"], "reason": gate.get("reason")}
    return ctx

# --- B2: real retriever node (replaces placeholder) ---
def _node_retrieve(ctx: Dict[str, Any]) -> Dict[str, Any]:
    q = ctx.get("text", "") or ""
    # Timed block aligned with acceptance (recorded as 'retrieve' node ms)
    t0 = perf_counter()
    hits = []
    try:
        hits = bm25(q, _RET_CFG)  # returns [{id, source, title, score, snippet}]
    finally:
        t_ms = int(round((perf_counter() - t0) * 1000))

    # metrics for retrieval
    unique_sources = len({h.get("source") for h in hits}) if hits else 0
    min_score = (min(h.get("score", 0.0) for h in hits) if hits else 0.0)

    ctx["retrieval"] = {
        "k": int(_RET_CFG.get("top_k", 3)),
        "hits": hits,  # keep full hits (includes snippet)
        "min_score": float(min_score),
        "unique_sources": int(unique_sources),
        "ms": t_ms,
    }
    return ctx

def _node_respond(ctx: Dict[str, Any]) -> Dict[str, Any]:
    # B1 keeps generation out of scope; supply a calm, short answer.
    route = ctx.get("route", "assist")
    if route == "crisis":
        ctx["answer"] = ""  # server still short-circuits crisis; we don't override
    elif route == "abstain":
        ctx["answer"] = "I can’t assist with that topic. Let’s focus on your wellbeing."
    else:
        ctx["answer"] = "Here to help. Let’s slow your breathing together—inhale 4, exhale 6, three times."
    return ctx

def run(text: str, mode: Optional[str] = "text",
        ui_lang: Optional[str] = None, ui_script: Optional[str] = None,
        predecided_route: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a tiny 4-node pipeline: input → policy_gate → retrieve → respond.
    Returns a dict conforming to DecisionJSON (route/answer/graph/metrics).
    """
    trace: List[TraceItem] = []
    node_ms: Dict[str, int] = {}
    ctx: Dict[str, Any] = {"text": text, "mode": mode, "ui_lang": ui_lang, "ui_script": ui_script}

    with _Timer() as t:
        ctx = _node_input(ctx)
    trace.append(TraceItem(node="input", ms=t.ms))
    node_ms["input"] = t.ms

    with _Timer() as t:
        if predecided_route:
            ctx["route"] = predecided_route
            ctx["gate_detail"] = {"route": predecided_route, "reason": "predecided"}
        else:
            ctx = _node_policy_gate(ctx)
    tr = TraceItem(node="policy_gate", ms=t.ms, out=ctx.get("route"))
    trace.append(tr); node_ms["policy_gate"] = t.ms

    # --- B2: retrieve ---
    with _Timer() as t:
        ctx = _node_retrieve(ctx)

    # --- B3: CKG-lite blend & re-rank (no new trace node, to avoid regressions) ---
    rhits = ctx.get("retrieval", {}).get("hits", []) or []
    syn_terms = []
    if ckg and hasattr(ckg, "expand") and hasattr(ckg, "score"):
        try:
            syn = ckg.expand(ctx.get("text", "") or "")
            syn_terms = syn.get("syn_terms", []) or []
        except Exception:
            syn_terms = []

    if rhits and syn_terms and _CKG_LAMBDA > 0.0 and ckg:
        ckg_scores: List[float] = []
        for h in rhits:
            try:
                c = float(ckg.score(h, syn_terms))
            except Exception:
                c = 0.0
            h["_ckg"] = round(c, 4)
            # blend: bm25 + lambda * ckg
            h["score"] = round(float(h.get("score", 0.0)) + (_CKG_LAMBDA * c), 4)
            ckg_scores.append(c)
        # rerank in-place
        rhits.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        ctx["retrieval"]["hits"] = rhits
        # lightweight metrics (top-k actually used)
        used = rhits[: int(_RET_CFG.get("top_k", 3))]
        min_used = min((u.get("_ckg", 0.0) for u in used), default=0.0)
        ctx["ckg_metrics"] = {
            "used": True,
            "lambda": float(_CKG_LAMBDA),
            "syn_terms": int(len(syn_terms)),
            "min_score_used": round(float(min_used), 4),
        }
    else:
        ctx["ckg_metrics"] = {
            "used": False,
            "lambda": float(_CKG_LAMBDA),
            "syn_terms": int(len(syn_terms)),
            "min_score_used": 0.0,
        }

    # push trace (unchanged shape)
    rhits = ctx.get("retrieval", {}).get("hits", [])
    trace.append(TraceItem(
        node="retrieve",
        ms=t.ms,
        k=int(_RET_CFG.get("top_k", 3)),
        hits=([{"id": h.get("id"), "title": h.get("title"), "score": h.get("score"), "source": h.get("source")} for h in rhits] or None)
    ))
    node_ms["retrieve"] = t.ms

    with _Timer() as t:
        ctx = _node_respond(ctx)
    trace.append(TraceItem(node="respond", ms=t.ms))
    node_ms["respond"] = t.ms

    total_ms = sum(node_ms.values())
    dj = DecisionJSON(
        route=ctx.get("route", "assist"),
        answer=ctx.get("answer", ""),
        graph=GraphObj(trace=trace),
        metrics=Metrics(total_ms=total_ms, node_ms=node_ms),
    )
    # Return a plain dict (easier to merge into existing server payload)
    try:
        out = dj.model_dump()  # Pydantic v2
    except AttributeError:
        out = dj.dict()        # Pydantic v1

    # --- B2: augment payload with retrieval metrics + evidence (non-breaking) ---
    # node ms already placed; now add retrieval sub-metrics
    hits_full = rhits
    if hits_full:
        out.setdefault("metrics", {}).setdefault("retrieval", {})
        out["metrics"]["retrieval"]["k"] = len(hits_full)
        out["metrics"]["retrieval"]["min_score"] = min(h.get("score", 0.0) for h in hits_full)
        out["metrics"]["retrieval"]["unique_sources"] = len({h.get("source") for h in hits_full})
        # expose compact evidence list to server / UI layer
        out.setdefault("evidence", hits_full)

    # --- B3: surface CKG metrics (Decision-JSON delta) ---
    out.setdefault("metrics", {})["ckg"] = ctx.get("ckg_metrics", {
        "used": False, "lambda": float(_CKG_LAMBDA), "syn_terms": 0, "min_score_used": 0.0
    })

    return out
