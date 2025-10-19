<# 
.SYNOPSIS
  Bootstrap Phase-B B1 docs, env flag, and changelog (idempotent).
  Safe to re-run. Optionally commits and tags.

.EXAMPLE
  pwsh -File scripts/bootstrap_b_phase_docs.ps1 -Commit -Tag 'ms-6.0-b1'
#>

[CmdletBinding()]
param(
  [switch]$Commit,
  [string]$Tag = '',
  [string]$MilestoneTitle = 'MS-6.0 — Phase-B B1: LangGraph skeleton + Decision JSON'
)

$ErrorActionPreference = 'Stop'
function Write-Note($msg){ Write-Host "» $msg" -ForegroundColor Cyan }

# --- 0) Ensure we're at repo root
if (-not (Test-Path .git)) { throw "Run this from the repository root." }

# --- 1) UTF-8 console (avoid mojibake)
try {
  chcp 65001 > $null 2>$null
  $OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
} catch {}

# --- 2) Create docs/
New-Item -ItemType Directory -Force -Path docs | Out-Null

# --- 3) Write docs/README-PhaseB.md
$readme = @'
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
'@
$readme | Out-File -Encoding utf8 -FilePath docs/README-PhaseB.md -Force

# --- 4) Write docs/DECISION_JSON.md
$decision = @'
# Decision JSON (Phase-B Surface)

**Minimal example**
```json
{
  "route": "assist",
  "answer": "Here to help. Let's slow your breathing together…",
  "graph": {
    "trace": [
      {"node":"input","ms":5},
      {"node":"policy_gate","ms":2,"out":"assist"},
      {"node":"retrieve","ms":7,"k":3,"hits":[{"title":"PHQ-9 Official","score":0.71}]},
      {"node":"respond","ms":11}
    ]
  },
  "metrics": { "total_ms": 34, "node_ms": {"input":5,"policy_gate":2,"retrieve":7,"respond":11} }
}
