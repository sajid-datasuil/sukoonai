
---

# Micro-step 2 — Add “Setup file” build (one-click EXE for Windows)

1) **Create** a PyInstaller spec and build script.

### `scripts/build_exe.ps1`
```powershell
# Build a single-file Windows executable
$ErrorActionPreference = "Stop"
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# Ensure output dirs exist
New-Item -ItemType Directory -Force dist | Out-Null
New-Item -ItemType Directory -Force build | Out-Null

# Bundle configs and fixtures; exclude tests
pyinstaller `
  --name "SukoonAI-Agent" `
  --onefile `
  --clean `
  --add-data "configs;configs" `
  --add-data "data/wer_fixtures;data/wer_fixtures" `
  --add-data "app/policies;app/policies" `
  --hidden-import "app" `
  --exclude-module "tests" `
  app\cli.py

Write-Host "EXE at: dist\SukoonAI-Agent.exe"
