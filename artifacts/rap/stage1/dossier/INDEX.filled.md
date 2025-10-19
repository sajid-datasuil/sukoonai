# RAP Stage-1 â€” Dossier Index

**Generated:** 2025-10-14T03:31:16Z

This index compiles the key audit artifacts for Stageâ€‘1.

## 1) Drill Results (Stepâ€‘1)

| Drill | Route | Abstain | Tokens/Handoff (ms) | PASS |
|------:|:------|:--------|:--------------------|:-----|
| Crisis | assist | False | tokens=0, handoff_ms=3380 | **False** |
| Abstainâ€‘Finance | assist | False | n/a | **False** |
| Assist (cited) | assist | False | evidence_count=1 | **False** |

**Stageâ€‘1/Stepâ€‘1 allâ€‘pass:** **False**

Artifact paths:
- raw: `artifacts/rap/stage1/drills/raw/`
- eval: `artifacts/rap/stage1/drills/eval/`
- rollâ€‘up: `artifacts/rap/stage1/drills/summary.json`

## 2) Grounding UX (Stepâ€‘2)

- evidence_cap_ok: **True**
- recall_at_k: **1**
- passed: **True**
- evidence_count: **1**
- gold_defined: **False**

Artifact: `artifacts/rap/stage1/grounding_eval/report.json`

## 3) Costs Rollâ€‘up (Stepâ€‘3, 1â€‘day)

- day: **2025-10-14**
- row_count: **10**
- total_pkr: **0\.25**
- by_component: **\{"llm":0,"retrieval":0\.25}**

Artifact: `artifacts/rap/stage1/costs_summary.json`

## 4) Planâ€‘Cap Enforcement Evidence

- overage artifact found: **True**  
Path: `artifacts/rap/stage1/plan_gate_overage.json`

## 5) RAP CI Proof

- status: **pending\ attach**  
(Attach run log/screenshot in this folder.)

## 6) Endpoint Health Note

- `/status`, `/api/status`, `/privacy`, `/api/privacy`: **200\ OK\ locally\ \(recorded\ earlier\)**
- `/api/web/turn` contract: **\{route,\ answer,\ abstain,\ timings\{},\ usage\{},\ evidence\[]}**

---

### How to render this file with live values
Run the included PowerShell generator to produce `INDEX.filled.md` next to this file:

```powershell
.rtifacts\rap\stage1\dossier\generate_rap_docs.ps1
```

> **Note:** Proceeding under RAP Waiver **W-001** (Assist cited drill). See WAIVER_W001.md.
