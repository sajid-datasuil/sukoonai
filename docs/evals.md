# Week-4 Evals (Offline Pack)

## How to run (local)
```powershell
$env:PYTHONPATH = (Get-Location).Path
pytest -q tests/policies
python -m app.eval.crisis_eval
python -m app.eval.groundedness_eval
python -m app.eval.cost_latency_eval
python -m app.eval.tts_cache_eval
