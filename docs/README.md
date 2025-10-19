# SukoonAI — Voice AI Agent (Anxiety & Depression)

**What it is**: A voice-first + text agent focused on anxiety & depression.  
**Languages**: Urdu, English, Roman-Urdu.  
**Channels**: Web (first), WhatsApp policy-compliant.  
**Out of scope**: Diagnosis, medications, legal advice — the agent **abstains** and provides referrals.

## Key capabilities
- Agentic RAG for psychoeducation  
- Micro-exercises & brief check-ins  
- Safety triage & crisis escalation (< 5 s)  
- WhatsApp compliance (24-hour window, opt-in/templates)

## Quick start (developer)

```powershell
# 1) Setup
$env:PYTHONPATH="."
$env:NO_NETWORK="1"
python -m venv .venv; .\.venv\Scripts\activate
pip install -r requirements.txt

# 2) Run API locally
uvicorn app.runtime.main:app --host 127.0.0.1 --port 8000

# 3) In a new terminal: health check (expect {"status":"ok", "engine":"..."})
curl http://127.0.0.1:8000/healthz

# 4) (Optional) Full test/eval
pytest -q                # all tests
python app/eval/wer_eval.py configs/wer.yaml  # expect avg_wer ≤ 0.15
