# Purpose: Evidence chunk schema for ingestion/indexing/grounding.
# Safety: No PHI/PII is stored; only public, curated text + licensing/meta.
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict
from datetime import datetime

Topic = Literal["anxiety", "depression"]
ChunkType = Literal["exercise", "psychoeducation", "hotline", "faq"]

class EvidenceRecord(BaseModel):
    # Stable identifiers
    evidence_id: str = Field(..., description="Global unique ID for this chunk (doc_id:chunk_n).")
    doc_id: str = Field(..., description="Stable document/source ID, e.g., 'phq9', 'gad7', 'mhgap'.")

    # Content + chunking
    text: str = Field(..., description="Chunk text (300–500 chars, voice-ready).")
    tokens_estimate: int = Field(..., description="Rough token count for budgeting.")

    # Retrieval metadata
    topic: Topic
    ctype: ChunkType
    locale: Literal["en", "ur", "roman-ur"] = "en"
    voice_ready: bool = True
    score_hint: Optional[float] = Field(None, description="Optional curation hint [0..1].")

    # Provenance/licensing
    license: str = Field(..., description="License string or short name.")
    source_path: str = Field(..., description="Local path or URL of the curated source.")
    cited_as: str = Field(..., description="Short, speakable citation line (e.g., 'WHO mhGAP, 2023').")

    # Ops
    created_at: datetime = Field(default_factory=datetime.utcnow)
    hash: str = Field(..., description="SHA1 of normalized text + key metadata for idempotency.")
