from __future__ import annotations
from textwrap import dedent
from app.ingest.loaders.base import BaseLoader

GAD7_CANON = dedent("""
GAD-7 is a seven-item questionnaire for screening and assessing severity of generalized anxiety.
Items are scored 0 to 3 based on symptoms over the last two weeks. Cut points: 5, 10, 15 suggest mild, moderate, severe.
It does not replace professional care. For acute distress or self-harm risk, seek urgent help.
""").strip()

class GAD7Loader(BaseLoader):
    doc_id = "gad7"
    license = "Public/Clinical use permitted (check local policy)"
    ctype = "psychoeducation"
    topic = "anxiety"
    source_path = "docs/datasets/gad7"
    cited_as = "GAD-7 (Spitzer et al., 2006)"

    def load_raw_text(self) -> str:
        return GAD7_CANON
