# sukoonai
## Quickstart (Windows)
```powershell
git clone https://github.com/DataSuil/sukoonai.git
cd sukoonai
.\setup.ps1
# in another terminal:
$payload = @{ text = 'Assalam o Alaikum, aaj kaisa mehsoos ho raha hai?' } | ConvertTo-Json -Compress
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/say -ContentType 'application/json' -Body $payload
## Governance
See our [TRUST CENTER](./TRUST-CENTER.md) for scope, data handling, citations, and safety policies.

## Documentation

- [Phase-B · B2 — Minimal BM25 Retriever + Per-Source Diversity](docs/Phase-B-B2-Retriever.md)
- [RAG-README](docs/RAG-README.md)
