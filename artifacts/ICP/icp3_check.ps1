$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path "artifacts/ICP" | Out-Null

$sumPath = "artifacts/rap/stage1/costs_summary.json"
$srcCsv  = "artifacts/ops/costs_daily.csv"
$today   = (Get-Date).ToString("yyyy-MM-dd")

if (-not (Test-Path $sumPath)) { throw "Missing $sumPath" }
$sum = Get-Content $sumPath -Raw | ConvertFrom-Json

$hasToday   = ($sum.day -eq $today)
$totOK      = ([double]$sum.total_pkr -gt 0)
$byCompOK   = ($sum.by_component -ne $null -and $sum.by_component.PSObject.Properties.Name.Count -gt 0)
$srcExists  = Test-Path $srcCsv

$out = [ordered]@{
  ok = ($hasToday -and $totOK -and $byCompOK -and $srcExists)
  day_is_today        = $hasToday
  total_gt_zero       = $totOK
  by_component_present= $byCompOK
  source_csv_exists   = $srcExists
  summary_file        = $sum
}

$out | ConvertTo-Json -Depth 10 | Out-File -Encoding utf8 "artifacts/ICP/icp3_check.json"
Write-Host "Wrote artifacts/ICP/icp3_check.json"
