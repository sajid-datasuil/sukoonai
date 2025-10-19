# Changelog

All notable changes to **SukoonAI** will be documented here. Version tags follow the milestone notation **MS-x.y**.

## [MS-5.8] — 2025-10-18
- UI (A3) Turn Metadata & Resilience — adds status ribbon (server_time [+server_id]), audio onerror note + Retry (cache-buster), and error=… chips for /api/web/turn; preserves A1/A2 and adds CI smoke.

## [MS-5.7] — 2025-10-18
**UI (A1 + A2)**
- **A1: English Voice stability**
  - Enforce single audio bar invariant (no duplicate players per turn).
  - Autoplay enabled; minimum voice capture ≥ 1200 ms.
  - Prevent duplicate UI inserts and keep spinner/scroll behavior stable.
- **A2: Parity & Breadcrumb**
  - Use one canonical string for both on-screen assistant text and audio caption  
    (priority: `answer_tts` → `tts_text` → `answer` → `text` → `answer_for_tts`).
  - Add per-turn breadcrumb: `route • t=…s • cost=₨…` (fields omitted if missing).
- **Cache-busting** of static assets to avoid stale JS/CSS:
  - `/static/web/styles.css?v=20251018a`
  - `/static/web/app.js?v=20251018a`

**Files touched**
- `artifacts/ICP/web/app.js`
- `artifacts/ICP/web/index.html`
- `artifacts/ICP/web/styles.css`
- `.github/workflows/lint-and-test.yml` (CI self-skips when PR has no Python diffs)

**Verification**
- Voice → English → say “hello, how are you?” → Stop  
  Expect: single audio bar; **caption text == on-screen text**; breadcrumb shows route & timing (and cost if present).

**PR:** #5 • **Tag:** `MS-5.7`

---

## [MS-5.6] — earlier
Safety/Crisis eval, WER harness improvements, CI hygiene (see repo history).
