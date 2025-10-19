
### `docs/INSTALL.md`
```md
# Install & Setup

## Option A — One-click EXE (Windows)
1. Run `SukoonAI-Agent-Setup.exe`.
2. Launch **SukoonAI Agent** from Start Menu.
3. (Optional) Place `configs/*.yaml` next to the EXE to override defaults.

## Option B — From source (Windows)
```powershell
python -m venv .venv; .\.venv\Scripts\activate
pip install -r requirements.txt
python -m app.api.server
