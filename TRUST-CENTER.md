# TRUST CENTER — SukoonAI (Week-3)

## Scope & Use
- SukoonAI is a **voice-first, evidence-grounded assistant for anxiety & depression self-help**.
- **Not a diagnostic tool**; does not replace professional care.

## Data Handling
- **No PHI/PII stored** in evidence or indices. Evidence is curated from public sources (e.g., PHQ-9, GAD-7).
- **No raw audio stored** by default. Transient audio/text is processed in memory; logs are scrubbed and capped (<1 KB/turn).
- Offline-first design (`NO_NETWORK=1`) supported end-to-end.

## Evidence & Citations
- All chunks trace to curated sources with licensing notes and a **speakable citation** (`cited_as`).
- Index manifest (`data/index/manifest.json`) records backend, counts, timestamp.

## Safety & Crisis
- Agent will **ABSTAIN** on out-of-scope/low-confidence queries.
- For **self-harm or acute crisis** signals, the agent escalates to crisis guidance/hotlines.

## Licensing
- PHQ-9 / GAD-7: free/clinical use with attribution (check local policy).
- Additional sources (e.g., mhGAP) follow publisher terms.

_Last updated: Week-3 (v0.3.0-week3)._
