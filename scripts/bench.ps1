# Windows-first micro-bench runner
param(
  [int]$N = 40,
  [string]$Text = "I feel anxious lately. What can I do?"
)

$env:BENCH_N = "$N"
$env:BENCH_TEXT = $Text

Write-Host "Running micro-bench: $N requests to /say"
python -m app.utils.bench
