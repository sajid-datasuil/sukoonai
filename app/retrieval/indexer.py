# Purpose: Offline index builder + search (tries FAISS, falls back to pure Python cosine).
from __future__ import annotations
import json, os, math, pickle
from typing import List, Dict, Tuple
from pathlib import Path
import hashlib
from datetime import datetime

try:
    import faiss  # optional
except Exception:
    faiss = None  # type: ignore

from app.retrieval.schema import EvidenceRecord

# Offline embedding: stable, deterministic, no network
def embed(text: str, dim: int = 384) -> List[float]:
    h = hashlib.sha1(text.encode("utf-8")).digest()
    # Repeat hash to fill dim, then L2 normalize
    raw = (h * ((dim // len(h)) + 1))[:dim]
    vec = [(b - 128) / 128.0 for b in raw]
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]

def build_index(records: List[EvidenceRecord], out_dir: str = "data/index") -> Dict[str, str]:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    vectors, metas = [], []
    for r in records:
        vectors.append(embed(r.text))
        metas.append(r.model_dump())

    # Persist portable pickle (fallback index)
    with open(os.path.join(out_dir, "meta.pkl"), "wb") as f:
        pickle.dump(metas, f)

    backend = "python"
    if faiss:
        import numpy as np
        xb = np.array(vectors, dtype="float32")
        index = faiss.IndexFlatIP(xb.shape[1])
        index.add(xb)
        faiss.write_index(index, os.path.join(out_dir, "faiss.index"))
        backend = "faiss"
    else:
        # Save vectors for python fallback
        with open(os.path.join(out_dir, "vectors.pkl"), "wb") as f:
            pickle.dump(vectors, f)

    # Write manifest for audits
    manifest = {
        "backend": backend,
        "count": len(metas),
        "embedding_dim": len(vectors[0]) if vectors else 0,
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return {"backend": backend, "count": str(len(metas))}

def search(query: str, k: int = 5, index_dir: str = "data/index") -> List[Dict]:
    import numpy as np
    q = np.array(embed(query), dtype="float32")

    with open(os.path.join(index_dir, "meta.pkl"), "rb") as f:
        metas = pickle.load(f)

    faiss_idx = None
    if faiss and os.path.exists(os.path.join(index_dir, "faiss.index")):
        faiss_idx = faiss.read_index(os.path.join(index_dir, "faiss.index"))

    if faiss_idx is not None:
        D, I = faiss_idx.search(q.reshape(1, -1), k)
        idxs = I[0].tolist()
        sims = D[0].tolist()
    else:
        with open(os.path.join(index_dir, "vectors.pkl"), "rb") as f:
            vectors = pickle.load(f)
        X = np.array(vectors, dtype="float32")
        sims = (X @ q).tolist()
        idxs = list(np.argsort(sims)[::-1][:k])

    out = []
    for i, idx in enumerate(idxs):
        rec = metas[idx]
        out.append({
            "rank": i + 1,
            "similarity": float(sims[idx]) if not faiss_idx else float(sims[i]),
            "evidence_id": rec["evidence_id"],
            "doc_id": rec["doc_id"],
            "text": rec["text"],
            "cited_as": rec["cited_as"],
            "license": rec["license"],
            "topic": rec["topic"],
            "ctype": rec["ctype"],
            "source_path": rec["source_path"],
        })
    return out
