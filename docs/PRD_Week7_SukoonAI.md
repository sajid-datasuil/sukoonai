# PRD — SukoonAI Week-7: MVP Final & Release (Individuals MVP)

## Problem & Opportunity
Millions in Pakistan face anxiety/depression with low access to care and stigma around seeking help. Western products price in USD and seldom support Urdu voice well. SukoonAI provides **Urdu-first, voice-first** self-help with grounded psychoeducation, micro-exercises, brief check-ins, and an always-on crisis route.

## Reference Model (internal note)
We take **Stella by United We Care** as a reference for business model and plan structuring (free vs paid tiers, clear gating by modality and minutes). **Key differences for SukoonAI**:
- **Urdu-first, voice-first** from the Free plan (we include voice in Free; we are not offering video).
- **PKR pricing** suited to local purchasing power.
- **Local constraints**: low-bandwidth, low-data mode; on-device/region-friendly speech stack (faster-whisper + Coqui-TTS).
- **Scope**: Individuals only for MVP (no clinician features in Week-7).

## Goals (MVP, Week-7)
- **Talk + chat**: mic/voice-note → STT (local) → Retrieval → GPT-4o mini → Guardrails → TTS (local).
- **Channels**: Web chat (launch), WhatsApp Cloud API (text + voice notes).
- **Safety**: Crisis fast-route **<5s**; strict **ABSTAIN** for diagnosis/meds/legal.
- **Quality**: **Recall@5 ≥ 90%** using production defaults (psychoeducation+instrument favored; source caps).
- **Finance**: Live token/message/session counters; daily/monthly **PKR** projection within ±10% of plan.
- **Docs & Ops**: README/Runbooks; tag `week7-mvp-ready`.

## Non-Goals (for MVP)
- No PSTN phone calling; no medication advice; **no video**; **no clinician services** (deferred).

## Users & JTBD (Individuals only)
- **Individuals (Urdu first)**: “Help me understand what I’m feeling and what I can do right now—in my language and without judgment.”

## Experience (happy path)
1) User taps mic or uploads a voice note → **faster-whisper** transcribes (Urdu/EN).  
2) Query expansion (EN/Urdu/Roman-Urdu) → retrieval (per-source cap; doc-type boost).  
3) **GPT-4o mini** synthesizes a short, cited reply; ABSTAIN if unsafe/out of scope.  
4) **Coqui-TTS** returns Urdu audio reply; display citations `[1][2]`.  
5) If crisis cues are detected at any point → **fast-route** to crisis flow (**<5s**).

## Safety & Compliance
- Crisis routing **<5s**; local helpline handoff copy + numbers.  
- No diagnosis/medication/legal guidance; **ABSTAIN + referral** copy.  
- Minimal PII; consent on first run; logs token/message counts (no transcripts by default in MVP).  
- Content sources are license-tagged; `distribution: internal-only` where needed.

## Functional Requirements
- **RAG**: `allow_doc_types=psychoeducation,instrument`, `per_source_cap=1..2`; Urdu query bonus.  
- **Channels**: Web chat UI; WhatsApp webhooks (text + voice note).  
- **Voice**: STT (faster-whisper small/medium); TTS (Coqui) with Urdu preset.  
- **Finance**: `/configs/costing.yaml` (PKR); `cost_meter.py` writes `artifacts/ops/costs_daily.csv`.  
- **Plans** (PKR): Free/Plus/Family gating by **voice minutes** + access.

## Non-Functional
- Latency: text turn < 1.5s median; voice reply round-trip < 2.5s for short messages.  
- Availability: single VPS (starter); graceful degradation to text.  
- Determinism: ingestion/chunking yields stable `content_hash`.

## Pricing (PKR) — MVP
- **Free**: PKR **0** — Unlimited text, **2 min/day voice**, assessments, basic programs.  
- **Plus**: PKR **799/mo** — **60 min/month voice**, all programs, priority.  
- **Family**: PKR **1,499/mo** — **180 min/month shared**, 2 listener credits.

## Success Metrics
- Quality: Recall@5 ≥ 90%; ≥70% sessions end with a concrete next step.  
- Safety: 100% crisis probes route < 5s.  
- Cost: projected LLM+transport within ±10% of PKR plan.  
- Adoption: ≥100 pilot users; ≥30% next-day return among Free.

## Risks & Mitigations
- **WhatsApp costs**: keep web chat default; rate-limit free voice minutes.  
- **STT accuracy (Urdu accents)**: allow Roman-Urdu text; short turns; fallback to text.  
- **Safety drift**: unit tests for crisis terms; ABSTAIN templates; human review mode.

## Deliverables (Week-7)
- Runtime code (`app/runtime/*`), web chat, WhatsApp webhook, safety router, cost meter.  
- Configs: costing, pricing; ops docs; release checklist; tag created.
