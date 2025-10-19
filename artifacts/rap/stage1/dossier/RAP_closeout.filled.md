# RAP Closeâ€‘Out â€” Stageâ€‘1 â†’ ICP Handoff

**Generated:** 2025-10-14T03:31:16Z

## Executive Summary
All Stageâ€‘1 checks are compiled and verified below. Decision: **GO → ICP (with Exception W-001)**

## PASS Table
| Check | PASS | Notes |
|------:|:----:|:------|
| Crisis drill | False | route=assist, tokens=0, handoff_ms=3380 |
| Abstainâ€‘Finance drill | False | route=assist, evidence=0 expected |
| Assist (cited) drill | False | route=assist, evidence_count=1 |
| Grounding UX | True | cap=True, recall_at_k=1 |
| Costs rollâ€‘up | True | day=2025-10-14, total_pkr=0\.25 |
| Planâ€‘cap evidence | True | plan_gate_overage.json present |

## Known Limits / Notes
- LLM outbound auth: see\ recent\ 401s\ during\ outbound\ calls;\ local\ routes\ served\ 200
- Evidence shaping cap (â‰¤3): cap\ â‰¤3\ enforced
- Corpus manifest status: False

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

