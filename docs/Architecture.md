
---

## 2) `docs/Architecture.md` (no functional changes; kept your correct Port Policy)
```markdown
# SukoonAI Architecture (RAP)

**Flow:** Mic → faster-whisper (STT) → Entity Linking (EL) → Graph-filtered RAG → GPT-4o mini → Safety/Contra checks → SAPI TTS → WAV + Cost log

**Core components**
- Runtime: FastAPI + Uvicorn (Python 3.12)  
- STT: faster-whisper (local)  
- Reasoner: Agentic RAG + tools (`ground_text`, `get_pathway`, `check_contraindications`)  
- CKG-lite: SQLite + NetworkX (nodes: Condition, Symptom, Intervention, Tool, CrisisSignal)  
- TTS: Windows SAPI  
- Storage: `artifacts/` outputs; `data/kg/*.csv` seeds  
- Costs: `artifacts/ops/costs_daily.csv` (PKR)

**Port Policy:** The default development port for SukoonAI is **8000**.  
If 8000 is already in use, use **8001** temporarily, but do not hardcode it in scripts.  
All RAP tests and CI workflows assume port 8000 as the default.

Mic  
 └─► faster-whisper (STT)  
   └─► EL (/kg/ground) ─► CKG-lite (SQLite + NetworkX)  
     └─► Graph-filtered RAG (subset → FAISS)  
       └─► GPT-4o mini (tools: get_pathway, check_contra)  
         └─► Safety veto (crisis/contra) ─► ABSTAIN/ESCALATE  
           └─► SAPI TTS ─► WAV ─► Playback + Cost log
