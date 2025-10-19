# Ingestion Pipeline — Week-3 (Final)

**Outputs**
- `data/curated/*.jsonl` — one JSONL per source (PHQ-9, GAD-7, …)
- `data/index/` — `meta.pkl` + `vectors.pkl` (or `faiss.index`) + `manifest.json` (backend, counts, timestamp)

**Chunking**
- 300–500 chars, sentence-aware, voice-readable.
- `EvidenceRecord` schema tracks: `doc_id`, `evidence_id`, `topic`, `ctype`, `locale`, `license`, `source_path`, `cited_as`, `hash`, `tokens_estimate`.

**Rebuild (offline)**
```bash
python -m app.cli.ingest_cli datasets

**Governance**
- Only curated, non-PII, public sources are ingested.
- Offline embeddings; **no network** required for ingestion or retrieval.
- Speakable citations (`cited_as`) included for each chunk.
- See the repository **[TRUST CENTER](../TRUST-CENTER.md)** for scope, safety, and licensing.

