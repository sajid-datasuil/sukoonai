# Purpose: Minimal PHQ-9 loader (seed text embedded for offline dev).
# Replace with curated file path in later micro-steps.
from __future__ import annotations
from textwrap import dedent
from app.ingest.loaders.base import BaseLoader

PHQ9_CANON = dedent("""
PHQ-9 is a nine-item questionnaire for screening and monitoring depression severity.
Each item scored 0 (Not at all) to 3 (Nearly every day) over the past two weeks.
Cut points: 5, 10, 15, 20 suggest mild, moderate, moderately severe, severe. It is not a diagnosis.
If self-harm thoughts are present, seek immediate help. Use for education and discussion with clinicians.
""").strip()

class PHQ9Loader(BaseLoader):
    doc_id = "phq9"
    license = "Public/Clinical use permitted (check local policy)"
    ctype = "psychoeducation"
    topic = "depression"
    source_path = "docs/datasets/phq9"  # placeholder; to be replaced by curated path
    cited_as = "PHQ-9 (Kroenke et al., 2001)"

    def load_raw_text(self) -> str:
        return PHQ9_CANON
