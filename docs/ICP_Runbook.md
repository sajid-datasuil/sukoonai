# SukoonAI — ICP Runbook (Windows-first, Web Demo)

**Scope:** Integration & Closure Phase (ICP) run instructions, safety probes, packaging, and troubleshooting for the **local Windows** demo build.  
**Audience:** Operator/demo runner. Assumes a working Python venv, FastAPI/Uvicorn server, and minimal logging posture.

---

## 0) Quick Facts

- **Green paths (must not regress):**
  - **Text→Text:** English, Urdu (script), Roman-Urdu
  - **Text→Voice (typed→audio):** English (stable)
- **New (this ICP):**
  - **Urdu Text→Voice** via Windows SAPI (opt-in)
  - **Voice→Voice** tab (browser STT → server → TTS, English first)
  - **Mic device picker + input level meter**
  - **UTF-8 safety probes** CLI (crisis/finance/wellness; EN/Urdu/Roman-Urdu)
  - **Packaging self-check** for `icp5_pack.zip`
- **Minimal logging:** No transcripts stored; aggregate counters only.
- **Fast-gates:** Crisis/finance zero-token gates remain ON.

---

## 1) Prerequisites

- **OS:** Windows 10/11  
- **Python:** 3.12 in a virtual environment  
- **Web Server:** FastAPI/Uvicorn  
- **Browser:** Chrome desktop recommended (for `webkitSpeechRecognition` STT)

**Optional (Urdu TTS):**
- Install an **Urdu** voice in Windows:  
  Settings → Time & Language → **Language & Region** → **Add a language** → Urdu → (let it download speech components) → **Restart PowerShell**.

---

## 2) Environment Variables (feature flags)

Set these in **PowerShell** before launching:

```powershell
$env:PYTHONPATH = (Resolve-Path .).Path
$env:SUKOON_DET = "1"               # deterministic prompts (stable demo runs)
$env:SUKOON_TTS_FALLBACK = "1"      # enable Windows SAPI fallback TTS (English + Urdu)
$env:SUKOON_TTS_URDU = "1"          # allow Urdu synthesis (script & mapped Roman-Urdu). Set "0" to disable.
# Optional debug endpoint (gates introspection):
# $env:SUKOON_DEBUG = "1"
