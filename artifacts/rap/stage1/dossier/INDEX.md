# RAP Stage-1 — Dossier Index

**Generated:** {{TS_UTC}}

This index compiles the key audit artifacts for Stage‑1.

## 1) Drill Results (Step‑1)

| Drill | Route | Abstain | Tokens/Handoff (ms) | PASS |
|------:|:------|:--------|:--------------------|:-----|
| Crisis | {{CRISIS_ROUTE}} | {{CRISIS_ABSTAIN}} | tokens={{CRISIS_TOKENS}}, handoff_ms={{CRISIS_HANDOFF}} | **{{CRISIS_PASS}}** |
| Abstain‑Finance | {{ABSTAIN_ROUTE}} | {{ABSTAIN_ABSTAIN}} | n/a | **{{ABSTAIN_PASS}}** |
| Assist (cited) | {{ASSIST_ROUTE}} | {{ASSIST_ABSTAIN}} | evidence_count={{ASSIST_EVIDENCE_COUNT}} | **{{ASSIST_PASS}}** |

**Stage‑1/Step‑1 all‑pass:** **{{DRILLS_ALL_PASS}}**

Artifact paths:
- raw: `artifacts/rap/stage1/drills/raw/`
- eval: `artifacts/rap/stage1/drills/eval/`
- roll‑up: `artifacts/rap/stage1/drills/summary.json`

## 2) Grounding UX (Step‑2)

- evidence_cap_ok: **{{EVIDENCE_CAP_OK}}**
- recall_at_k: **{{RECALL_AT_K}}**
- passed: **{{GROUNDING_PASSED}}**
- evidence_count: **{{EVIDENCE_COUNT}}**
- gold_defined: **{{GOLD_DEFINED}}**

Artifact: `artifacts/rap/stage1/grounding_eval/report.json`

## 3) Costs Roll‑up (Step‑3, 1‑day)

- day: **{{COST_DAY}}**
- row_count: **{{COST_ROW_COUNT}}**
- total_pkr: **{{COST_TOTAL_PKR}}**
- by_component: **{{COST_BY_COMPONENT}}**

Artifact: `artifacts/rap/stage1/costs_summary.json`

## 4) Plan‑Cap Enforcement Evidence

- overage artifact found: **{{PLAN_CAP_PRESENT}}**  
Path: `artifacts/rap/stage1/plan_gate_overage.json`

## 5) RAP CI Proof

- status: **{{CI_PROOF_NOTE}}**  
(Attach run log/screenshot in this folder.)

## 6) Endpoint Health Note

- `/status`, `/api/status`, `/privacy`, `/api/privacy`: **{{HEALTH_NOTE}}**
- `/api/web/turn` contract: **{{TURN_CONTRACT_NOTE}}**

---

### How to render this file with live values
Run the included PowerShell generator to produce `INDEX.filled.md` next to this file:

```powershell
.rtifacts\rap\stage1\dossier\generate_rap_docs.ps1
```