<#  artifacts/ICP/make_icp_pack.ps1
    Builds icp5_pack.zip for the demo.

    Contents target:
      - demo_ui.html at ZIP ROOT
      - artifacts/ICP/*           (current UI & ICP files)
      - artifacts/audio/tts/*     (at least one WAV if available)
      - WAIVER_W001.md            (at root if found; else continue)

    Self-check:
      - prints UI present?, WAV count, waiver present?
      - prints "OK" if UI present AND (wavCount>=1 OR SUKOON_TTS_URDU=0), else "CHECK"
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

# Paths
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Stage    = Join-Path $PSScriptRoot 'icp5_stage'
$ZipOut   = Join-Path $PSScriptRoot 'icp5_pack.zip'

# Reset stage
if (Test-Path $Stage) { Remove-Item $Stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Stage | Out-Null

# 1) Copy UI at root of stage
Copy-Item -Path (Join-Path $PSScriptRoot 'demo_ui.html') -Destination (Join-Path $Stage 'demo_ui.html') -Force

# 2) Copy ICP folder (JSONs, runbooks, etc.)
Copy-Item -Recurse -Force -Path (Join-Path $PSScriptRoot '*') -Destination (Join-Path $Stage 'artifacts\ICP') -Exclude 'icp5_stage','icp5_pack.zip','icp5_stage.zip' | Out-Null

# 3) Copy latest audio (if any)
$AudioSrc = Join-Path $RepoRoot 'artifacts\audio\tts'
if (Test-Path $AudioSrc) {
  Copy-Item -Recurse -Force -Path $AudioSrc -Destination (Join-Path $Stage 'artifacts\audio\tts') -ErrorAction SilentlyContinue
}

# 4) Try to include a representative last_turn.json (if exists)
$LastTurn = Join-Path $RepoRoot 'artifacts\ICP\last_turn.json'
if (Test-Path $LastTurn) {
  Copy-Item -Force -Path $LastTurn -Destination (Join-Path $Stage 'artifacts\ICP\last_turn.json')
}

# 5) Optional waiver
$WaiverSrc1 = Join-Path $RepoRoot 'WAIVER_W001.md'
$WaiverSrc2 = Join-Path $RepoRoot 'artifacts\rap\stage1\dossier\WAIVER_W001.md'
if (Test-Path $WaiverSrc1) {
  Copy-Item -Force $WaiverSrc1 -Destination (Join-Path $Stage 'WAIVER_W001.md')
} elseif (Test-Path $WaiverSrc2) {
  Copy-Item -Force $WaiverSrc2 -Destination (Join-Path $Stage 'WAIVER_W001.md')
}

# 6) Zip it
if (Test-Path $ZipOut) { Remove-Item $ZipOut -Force }
Compress-Archive -Path (Join-Path $Stage '*') -DestinationPath $ZipOut -Force
Write-Host "Built: $ZipOut" -ForegroundColor Green

# 7) Self-check
$wavCount = (Get-ChildItem -Recurse $Stage -Filter *.wav -ErrorAction SilentlyContinue | Measure-Object).Count
$hasUI    = (Test-Path (Join-Path $Stage 'demo_ui.html')) -or (Test-Path (Join-Path $Stage 'artifacts\ICP\demo_ui.html'))
$hasWvr   = (Test-Path (Join-Path $Stage 'WAIVER_W001.md'))

"UI: $hasUI"
"WAV: $wavCount"
"Waiver: $hasWvr"

# If Urdu TTS is enabled, prefer to have at least one WAV
$wantWav = [bool]([int](($env:SUKOON_TTS_URDU+"") -eq "1"))
if ($hasUI -and (($wavCount -ge 1) -or (-not $wantWav))) {
  Write-Host "OK" -ForegroundColor Green
} else {
  Write-Host "CHECK (no WAV or UI missing)" -ForegroundColor Yellow
}
