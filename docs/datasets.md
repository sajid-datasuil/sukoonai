# SukoonAI — Curation List (Evidence-Only)

> Governance note: Week-2 is **links/paths + licenses only** (no ingestion yet).  
> Columns: title | URL/path | license | topic(anxiety|depression) | type(exercise|psychoeducation|hotline|faq) | locale(ur|en|roman-ur) | voice_ready(true/false) | notes

| title                                               | URL/path                                                                 | license                                   | topic       | type            | locale   | voice_ready | notes |
|-----------------------------------------------------|--------------------------------------------------------------------------|-------------------------------------------|------------|-----------------|----------|-------------|-------|
| WHO mhGAP Intervention Guide (mental health)        | https://www.who.int/publications-detail-redirect/9789241549790          | WHO terms (non-commercial; attribution)   | anxiety     | psychoeducation | en       | false       | Use short bullets; map callouts to "Source: WHO mhGAP, 2023". |
| PHQ-9 (Patient Health Questionnaire-9)              | https://www.phqscreeners.com/select-screener                             | Free to use with attribution               | depression  | faq             | en       | true        | Speakable summary only; no diagnosis. |
| PHQ-2 (ultra-brief)                                 | https://www.phqscreeners.com/select-screener                             | Free to use with attribution               | depression  | faq             | en       | true        | Gate to ABSTAIN for clinical advice. |
| GAD-7 (Generalized Anxiety Disorder-7)              | https://www.phqscreeners.com/select-screener                             | Free to use with attribution               | anxiety     | faq             | en       | true        | Speakable steps + “talk to a professional” referral. |
| C-SSRS (Columbia Suicide Severity Rating Scale)     | https://cssrs.columbia.edu/                                              | Free for many uses (see site)              | anxiety     | hotline         | en       | false       | **Do not** administer; use for referral logic only. |
| “5-4-3-2-1” Grounding Exercise                      | docs/exercises/54321.md                                                  | Internal curation (derived from CBT norms) | anxiety     | exercise        | en/ur    | true        | Short numbered steps; pre-render TTS Week-3. |
| Box Breathing (4-4-4-4)                             | docs/exercises/box-breathing.md                                          | Internal curation                          | anxiety     | exercise        | en/ur    | true        | Safe micro-exercise; no contraindication claims. |
| National crisis/hotline directory (Pakistan, stub)  | configs/hotlines/pk.csv                                                  | Internal curation                          | both        | hotline         | ur/en    | n/a         | Placeholder file; to be validated with partner in Week-5. |

> CI Gate (Week-2): If PR touches `app/retrieval/*` or `configs/planner.yaml`, this file **must** be modified in the same PR (see scripts/check_datasets_guard.py).

## Ingestion Status (Week-3 seed)
| doc_id | title | topic | type | locale | license | voice_ready | ingested | chunks | last_update | speakable citation |
|---|---|---|---|---|---|---|---:|---:|---|---|
| phq9 | Patient Health Questionnaire (PHQ-9) | depression | psychoeducation | en | public/clinical use (check policy) | yes | ✅ | 1 | 2025-10-05T12:53:32Z | PHQ-9 (Kroenke et al., 2001) |
| gad7 | Generalized Anxiety Disorder (GAD-7) | anxiety | psychoeducation | en | public/clinical use (check policy) | yes | ✅ | 1 | 2025-10-05T12:53:32Z | GAD-7 (Spitzer et al., 2006) |
