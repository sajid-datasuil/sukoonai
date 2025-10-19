# RAP Close‑Out — Stage‑1 → ICP Handoff

**Generated:** {{TS_UTC}}

## Executive Summary
All Stage‑1 checks are compiled and verified below. Decision: **{{GO_NO_GO}}**

## PASS Table
| Check | PASS | Notes |
|------:|:----:|:------|
| Crisis drill | {{CRISIS_PASS}} | route={{CRISIS_ROUTE}}, tokens={{CRISIS_TOKENS}}, handoff_ms={{CRISIS_HANDOFF}} |
| Abstain‑Finance drill | {{ABSTAIN_PASS}} | route={{ABSTAIN_ROUTE}}, evidence=0 expected |
| Assist (cited) drill | {{ASSIST_PASS}} | route={{ASSIST_ROUTE}}, evidence_count={{ASSIST_EVIDENCE_COUNT}} |
| Grounding UX | {{GROUNDING_PASSED}} | cap={{EVIDENCE_CAP_OK}}, recall_at_k={{RECALL_AT_K}} |
| Costs roll‑up | {{COSTS_PRESENT}} | day={{COST_DAY}}, total_pkr={{COST_TOTAL_PKR}} |
| Plan‑cap evidence | {{PLAN_CAP_PRESENT}} | plan_gate_overage.json present |

## Known Limits / Notes
- LLM outbound auth: {{LLM_AUTH_NOTE}}
- Evidence shaping cap (≤3): {{EVIDENCE_CAP_NOTE}}
- Corpus manifest status: {{GOLD_DEFINED}}

## Attachments (this folder)
- `INDEX.filled.md`, `RAP_closeout.filled.md`
- `../drills/raw/*`, `../drills/eval/*`, `../drills/summary.json`
- `../grounding_eval/report.json`
- `../costs_summary.json`
- `../plan_gate_overage.json`
- `CI_proof/*` (add your screenshot/log)

---

### How to render this file with live values
Run the generator to produce `RAP_closeout.filled.md`:

```powershell
.rtifacts\rap\stage1\dossier\generate_rap_docs.ps1
```