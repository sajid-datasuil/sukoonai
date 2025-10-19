$ErrorActionPreference = "Stop"
$scriptPath = "artifacts/ICP/demo_script_ur_en.md"
$outWav     = "artifacts/audio/tts/demo_dialog.wav"

if (-not (Test-Path $scriptPath)) { throw "Missing $scriptPath" }

# Pull only SukoonAI lines (**SukoonAI:** ...)
$lines = Get-Content $scriptPath -Raw -Encoding UTF8 -ErrorAction Stop -Force 
$agentLines = ($lines -split "`r?`n") | Where-Object { $_ -match '^\*\*SukoonAI:\*\*\s*(.+)$' } |
  ForEach-Object { ($_ -replace '^\*\*SukoonAI:\*\*\s*','').Trim() }

if (-not $agentLines -or $agentLines.Count -eq 0) {
  # Fallback: use whole script, stripped of markdown
  $agentLines = @($lines -replace '\*\*.*?\*\*','' -replace '#.*','' -replace '\s+',' ')
}

# --- SAPI synth to 16kHz 16-bit mono WAV ---
$voice = New-Object -ComObject SAPI.SpVoice
$fs    = New-Object -ComObject SAPI.SpFileStream
$fmt   = New-Object -ComObject SAPI.SpAudioFormat
# SAFT16kHz16BitMono = 39
$fmt.Type = 39
$fs.Format = $fmt
$fs.Open($outWav, 3, $false)  # SSFMCreateForWrite=3
$voice.AudioOutputStream = $fs
$voice.Speak(($agentLines -join ' '), 0) | Out-Null
$fs.Close()

Write-Host "Wrote $outWav"

