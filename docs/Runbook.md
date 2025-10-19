# Runbook (local demo)

1) Activate venv and run:
   - PowerShell:
     $env:PYTHONPATH="."
     $env:SUKOON_TTS_ENGINE="sapi"
     uvicorn app.runtime.main:app --host 127.0.0.1 --port 8000

2) Smoke test:
   - GET /healthz → {status:"ok", engine:"sapi"}
   - POST /assist → returns output.text + audio_url + evidence (≤3) + cost fields

3) Artifacts:
   - WAV: artifacts/audio/tts
   - Costs: artifacts/ops/costs_daily.csv

**Port Policy:** The default development port for SukoonAI is **8000**.  
If 8000 is already in use, use **8001** temporarily, but do not hardcode it in scripts.  
All RAP tests and CI workflows assume port 8000 as the default.
