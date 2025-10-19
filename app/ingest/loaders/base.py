# Purpose: Base loader API and helpers for curated datasets.
from __future__ import annotations
from typing import Iterable, Dict, Any
import hashlib, math

from app.ingest.chunker import split_into_chunks
from app.retrieval.schema import EvidenceRecord

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def est_tokens(text: str) -> int:
    # Cheap offline token heuristic
    return math.ceil(len(text) / 4)

class BaseLoader:
    doc_id: str
    license: str
    ctype: str
    topic: str
    locale: str = "en"
    source_path: str
    cited_as: str

    def load_raw_text(self) -> str:
        raise NotImplementedError

    def iter_records(self) -> Iterable[EvidenceRecord]:
        raw = self.load_raw_text()
        for i, chunk in enumerate(split_into_chunks(raw)):
            evidence_id = f"{self.doc_id}:{i+1:03d}"
            yield EvidenceRecord(
                evidence_id=evidence_id,
                doc_id=self.doc_id,
                text=chunk,
                tokens_estimate=est_tokens(chunk),
                topic=self.topic,  # type: ignore
                ctype=self.ctype,  # type: ignore
                locale=self.locale,  # type: ignore
                voice_ready=True,
                license=self.license,
                source_path=self.source_path,
                cited_as=self.cited_as,
                hash=sha1(f"{self.doc_id}|{chunk}|{self.license}|{self.source_path}|{self.cited_as}"),
            )
