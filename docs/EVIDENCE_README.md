# Open Evidence — SukoonAI (Week-6)

This pilot builds a local, license-aware evidence corpus for anxiety/depression **Agentic RAG** (Urdu-first; EN/Roman-Urdu supported). We keep **full text locally** for retrieval quality and tag each chunk with `license` and `distribution` (e.g., `internal-only`).

---

## Quickstart

```powershell
# Minimal deps (PDF/DOCX/Schema)
pip install pypdf python-docx jsonschema

# Ingest ICD-11 CH-06 (extracts) → JSONL
python scripts/ingest_pdf.py `
  --pdf "data/raw/icd11/Classification of Mental & Behavioral Disorders.pdf" `
  --doc-id-prefix "icd11-ch06" `
  --title "ICD-11 Chapter 06 (Extracts)" `
  --section-root "ICD-11 CH06" `
  --source-url "https://icd.who.int/" `
  --license "WHO terms - cite/link" `
  --distribution internal-only `
  --topic anxiety depression `
  --icd11 6A `
  --doc-type taxonomy `
  --out artifacts/open_evidence/icd11_ch06.jsonl

# Convert dataset list DOCX → simple catalog JSON
python scripts/ingest_docx.py `
  --docx "data/raw/lists/List - Free Datasets - SukoonAI.docx" `
  --out artifacts/open_evidence/dataset_catalog.json

# Validate chunks + quick stats
python scripts/validate_chunks.py artifacts/open_evidence/icd11_ch06.jsonl
