# Voice UI — Quick Start & Test

This guide covers running the web demo, testing English Voice, and the acceptance checks introduced in **A1** and **A2**.

---

## 1) Prerequisites

- Windows 10/11
- Python 3.12 (venv recommended)
- FastAPI / Uvicorn installed via requirements
- Microphone permission in the browser (Chrome recommended)

**Optional (improves TTS/STT):**
- ElevenLabs API key (primary TTS)
- Windows SAPI-5 available (fallback TTS)
- Local faster-whisper configured if using offline STT

---

## 2) Environment (examples)

```powershell
# in PowerShell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -r requirements.txt

# Optional env toggles you use in development
# $env:SUKOON_TTS="elevenlabs"   # or "sapi"
# $env:SUKOON_STT="whisper"      # offline STT
# $env:SUKOON_STT_MODEL="base"   # e.g., tiny/base/small
