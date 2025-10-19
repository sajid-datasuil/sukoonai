# artifacts/ICP/demo_run.ps1
# Tiny demo runner for SukoonAI (Web path, Windows/SAPI) — PowerShell 5 compatible
$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:8002"

# --- helpers ---
function Call-Turn($text, $headers=@{}) {
  $body = @{ text = $text } | ConvertTo-Json -Compress
  Invoke-RestMethod -Method Post -Uri "$base/api/web/turn" -ContentType "application/json" -Headers $headers -Body $body
}

function Show-Item($p) {
  if (Test-Path $p) {
    Get-Item $p | Select-Object @{n='Path';e={$_.FullName}}, @{n='Bytes';e={$_.Length}}, LastWriteTime
  } else {
    $rp = Resolve-Path -LiteralPath $p -ErrorAction SilentlyContinue
    $pathOut = if ($rp) { $rp.Path } else { $p }
    [pscustomobject]@{ Path = $pathOut; Bytes = 0; LastWriteTime = $null }
  }
}

Write-Host "== SukoonAI tiny demo runner =="

# --- 1) Health checks ---
Write-Host "`n[1/3] Health checks..."
$apiStatus = Invoke-RestMethod -Method Get -Uri "$base/api/status"
$privacy   = Invoke-RestMethod -Method Get -Uri "$base/privacy"
$healthOK  = ($null -ne $apiStatus -and $null -ne $privacy)
Write-Host "  /api/status: OK"
Write-Host "  /privacy:    OK"

# --- 2) Happy-path web/turn (assist route expected) ---
Write-Host "`n[2/3] Happy-path /api/web/turn..."
$headers = @{ "X-User-Id"="demo"; "X-Plan"="Free" }
# Use ASCII hyphen to avoid encoding quirks in some consoles
$assist  = Call-Turn -text "Assalam o Alaikum - aik saathi se baat karni hai." -headers $headers
$assistOK = ($assist.route -eq "assist" -and $assist.abstain -eq $false)
Write-Host ("  route: {0}, abstain: {1}" -f $assist.route, $assist.abstain)

# --- 3) Artifact checklist ---
Write-Host "`n[3/3] Artifact checklist..."
$paths = @(
  "artifacts/ICP/icp1_demo_checks.json",
  "artifacts/ICP/icp3_check.json",
  "artifacts/ICP/icp4_safety.json",
  "artifacts/ICP/demo_script_ur_en.md",
  "artifacts/audio/tts/demo_dialog.wav",
  "artifacts/ICP/icp5_pack.zip",
  "artifacts/rap/stage1/SukoonAI_RAP_Stage1_dossier.zip",
  "artifacts/rap/stage1/dossier/WAIVER_W001.md"
)
$items = $paths | ForEach-Object { Show-Item $_ }

$allExist = ($items | Where-Object { $_.Bytes -gt 0 } | Measure-Object).Count
$passArtifacts = ($allExist -ge 6)  # allow a couple optional misses if not built yet

# --- Summary to console & file ---
$summary = [pscustomobject]@{
  health_ok    = $healthOK
  assist_ok    = $assistOK
  artifacts_ok = $passArtifacts
}
$summary | ConvertTo-Json -Depth 5 | Write-Host

New-Item -ItemType Directory -Force -Path "artifacts/ICP" | Out-Null
$summary | ConvertTo-Json -Depth 5 | Out-File -Encoding utf8 "artifacts/ICP/demo_run_summary.json"

# --- Plain-ASCII trailer (PS5-safe) ---
Write-Host ""
Write-Host "Details:"
$items | Format-Table -AutoSize
Write-Host ""
Write-Host "Done."
