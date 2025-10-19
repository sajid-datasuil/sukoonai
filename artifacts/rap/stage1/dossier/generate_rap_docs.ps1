Param(
  [string]$Root = "artifacts/rap/stage1"
)

function Read-Json($path) {
  if (Test-Path $path) { Get-Content $path -Raw | ConvertFrom-Json } else { $null }
}

$ts = (Get-Date).ToUniversalTime().ToString("s") + "Z"

# Load artifacts
$crisis = Read-Json (Join-Path $Root "drills/eval/crisis_passfail.json")
$abst   = Read-Json (Join-Path $Root "drills/eval/abstain_finance_passfail.json")
$assist = Read-Json (Join-Path $Root "drills/eval/assist_cited_passfail.json")
$sum    = Read-Json (Join-Path $Root "drills/summary.json")
$ground = Read-Json (Join-Path $Root "grounding_eval/report.json")
$costs  = Read-Json (Join-Path $Root "costs_summary.json")
$plan   = Test-Path (Join-Path $Root "plan_gate_overage.json")

# Derive values (with safe defaults)
$map = @{}
$map["TS_UTC"] = $ts

# Crisis
$map["CRISIS_PASS"]    = "$($crisis.pass)"
$map["CRISIS_ROUTE"]   = "$($crisis.route)"
$map["CRISIS_ABSTAIN"] = "$($crisis.abstain)"
$map["CRISIS_TOKENS"]  = "$($crisis.tokens)"
$map["CRISIS_HANDOFF"] = "$($crisis.handoff_ms)"

# Abstain-Finance
$map["ABSTAIN_PASS"]     = "$($abst.pass)"
$map["ABSTAIN_ROUTE"]    = "$($abst.route)"
$map["ABSTAIN_ABSTAIN"]  = "$($abst.abstain)"

# Assist
$map["ASSIST_PASS"]            = "$($assist.pass)"
$map["ASSIST_ROUTE"]           = "$($assist.route)"
$map["ASSIST_ABSTAIN"]         = "$($assist.abstain)"
$map["ASSIST_EVIDENCE_COUNT"]  = "$($assist.evidence_count)"

# Drills roll-up
$map["DRILLS_ALL_PASS"] = "$($sum.all_pass)"

# Grounding
$map["EVIDENCE_CAP_OK"] = "$($ground.evidence_cap_ok)"
$map["RECALL_AT_K"]     = "$($ground.recall_at_k)"
$map["GROUNDING_PASSED"]= "$($ground.passed)"
$map["EVIDENCE_COUNT"]  = "$($ground.evidence_count)"
$map["GOLD_DEFINED"]    = "$($ground.gold_defined)"

# Costs
$map["COST_DAY"]         = "$($costs.day)"
$map["COST_ROW_COUNT"]   = "$($costs.row_count)"
$map["COST_TOTAL_PKR"]   = "$($costs.total_pkr)"
$map["COST_BY_COMPONENT"]= if($costs.by_component){ ($costs.by_component | ConvertTo-Json -Compress) } else { "{}" }
$map["COSTS_PRESENT"]    = "$([bool]$costs)"

# Plan cap
$map["PLAN_CAP_PRESENT"] = "$($plan)"

# Misc / notes placeholders (left for operator to set or auto-noted)
$map["CI_PROOF_NOTE"]       = "pending attach"
$map["HEALTH_NOTE"]         = "200 OK locally (recorded earlier)"
$map["TURN_CONTRACT_NOTE"]  = "{route, answer, abstain, timings{}, usage{}, evidence[]}"
$map["GO_NO_GO"]            = if ($sum.all_pass -and $ground.passed -and $costs) { "GO → ICP" } else { "TBD" }
$map["LLM_AUTH_NOTE"]       = "see recent 401s during outbound calls; local routes served 200"
$map["EVIDENCE_CAP_NOTE"]   = "cap ≤3 enforced"

# Replace placeholders in scaffolds
$dossier = Join-Path $Root "dossier"
$indexScaffold = Join-Path $dossier "INDEX.md"
$closeScaffold = Join-Path $dossier "RAP_closeout.md"

$indexOut = Join-Path $dossier "INDEX.filled.md"
$closeOut = Join-Path $dossier "RAP_closeout.filled.md"

function Fill-Template($pathIn, $pathOut, $map) {
  $text = Get-Content $pathIn -Raw
  foreach($k in $map.Keys){
    $text = $text -replace ("{{"+[regex]::Escape($k)+"}}"), ([regex]::Escape($map[$k])) -replace "\\","\"
  }
  Set-Content -Path $pathOut -Value $text -Encoding UTF8
}

Fill-Template $indexScaffold $indexOut $map
Fill-Template $closeScaffold $closeOut $map

Write-Host "Rendered: $indexOut"
Write-Host "Rendered: $closeOut"