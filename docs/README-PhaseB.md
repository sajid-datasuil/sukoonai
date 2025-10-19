New-Item -ItemType Directory -Force docs | Out-Null
@'
# Phase-B: Agentic / RAG Backbone — B1 Skeleton

**Objective:** Wrap the existing A-phase turn engine with a tiny LangGraph-style pipeline and add an *additive* Decision-JSON surface.
- Nodes: `input → policy_gate → retrieve → respond`
- Each node records elapsed ms (visible in `graph.trace[]` and `metrics.node_ms`)
- **No behavior change** to term gates or A-phase UI

**Feature Flag**
- `SUKOON_GRAPH=on|off` (default **on**). When on, the server merges `graph` + `metrics.node_ms` after `run_turn(...)`.

**Files (added)**
- `app/graph/types.py` — `DecisionJSON`, `TraceItem`, `Metrics`
- `app/graph/langgraph_pipeline.py` — 4-node pipeline with ns-precision timer (≥1 ms floor)

**Acceptance (B1)**
- `POST /api/web/turn` contains `graph.trace` (len ≥ 2) and `metrics.node_ms` with keys: `input, policy_gate, retrieve, respond` (ints > 0).
- A1/A2/A3 UI remains unchanged (breadcrumb, answer, TTS parity).

**Next (B2–B6)**
- B2: plug minimal retriever (replace placeholder hits, per-source diversity).
- B3: CKG-lite / alias boosts (Urdu & Roman-Urdu).
- B4: LLM adapter + token/cost accounting (feeds PKR meter).
- B5: graph hardening (timeouts, retry-once).
- B6: recall@5 harness on curated golds.
'@ | Out-File -Encoding utf8 docs/README-PhaseB.md -Force
