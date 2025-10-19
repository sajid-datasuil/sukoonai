# B3: CKG-lite adapter + synonyms (Agentic/RAG, Phase-B)

**Owner:** Release-Captain + Solutions-Architect  
**Goal (one sentence):** Add a CKG-lite synonym/alias adapter that boosts BM25 hits via concept expansion (English + a few Urdu/Roman-Urdu pairs), re-ranks results, and logs light metrics—without increasing surface area to the UI.

## Non-negotiables
- Endpoint remains `POST /api/web/turn`
- Do **not** touch `app/policies/term_gates.py`
- **No UI changes**
- Follow micro-step guardrails from the playbook

## Scope (≤3 files changed)
- `app/ckg/ckg_adapter.py` — new adapter  
  - `expand(query) -> {syn_terms:[(term,weight),...], lang:'en'|'ur'|'roman'}`
  - `score(hit, syn_terms) -> float` (normalized overlap / weighted boosts)
- `configs/ckg.yaml` — new config (blend weight, synonym sets)
- `app/graph/langgraph_pipeline.py` — blend & re-rank  
  - After BM25: call `ckg.expand()` + `ckg.score()`  
  - Compute `final_score = bm25 + lambda * ckg`  
  - Re-rank; add `metrics.ckg` to Decision-JSON

## How it works
1. **Expansion:** Adapter normalizes query (e.g., `phq-9`, `PHQ 9`, `phq9`) and expands to synonyms/aliases, incl. Urdu/Roman-Urdu pairs via `lang_aliases`.
2. **Per-hit scoring:** For each BM25 hit, `ckg.score()` tokenizes `(title + snippet)` and computes a normalized weighted overlap with synonyms.
3. **Blending + re-rank:** `score := bm25 + λ · ckg` (λ from `configs/ckg.yaml`, default `0.25`), then sort desc.
4. **Metrics:** Pipeline emits:
   ```json
   "metrics": {
     "retrieval": {"k":3, "min_score":..., "unique_sources":...},
     "ckg": {"used": true, "lambda": 0.25, "syn_terms": 12, "min_score_used": 0.0753}
   }
