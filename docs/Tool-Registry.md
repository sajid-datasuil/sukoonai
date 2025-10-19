# Tool Registry (what/why/where/cost)
## faster-whisper (ASR)
- Why: local, Urdu/Roman-Urdu friendly; cost≈0
- Where: STT stage; outputs transcript JSON

## GPT-4o mini (LLM)
- Why: good-enough at low cost; token-capped
- Where: after retrieval + tools; outputs draft

## CKG-lite (SQLite + NetworkX)
- Why: explainability + safety + fewer tokens
- Where: app/kg/*; inputs entities → plan JSON

## SAPI (TTS)
- Why: stable on Win + Py3.12; cost≈0
- Where: final stage; outputs WAV 16k mono
