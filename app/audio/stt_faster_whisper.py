from typing import Dict, Any, List, Optional
import os
from faster_whisper import WhisperModel

class STTEngine:
    """
    Minimal wrapper around faster-whisper.
    Defaults to CPU-friendly settings; configurable via env:
      STT_MODEL  (e.g., "small", "medium", "large-v3")
      STT_DEVICE ("cpu" or "cuda")
      STT_COMPUTE ("int8", "int8_float16", "float16", "float32")
    """

    def __init__(self) -> None:
        model_size = os.getenv("STT_MODEL", "small")         # multilingual, good for Urdu
        device     = os.getenv("STT_DEVICE", "cpu")
        compute    = os.getenv("STT_COMPUTE", "int8")        # CPU-friendly

        self._model = WhisperModel(model_size, device=device, compute_type=compute)

    def transcribe_file(self, path: str, language: Optional[str] = None) -> Dict[str, Any]:
        # beam_size=1 keeps it fast for MVP; we can tune later
        segments, info = self._model.transcribe(
            path,
            beam_size=1,
            language=language,          # None = auto-detect
            vad_filter=True
        )
        segs: List[Dict[str, Any]] = []
        text_parts: List[str] = []
        for s in segments:
            segs.append({"start": s.start, "end": s.end, "text": s.text.strip()})
            text_parts.append(s.text.strip())

        return {
            "text": " ".join([t for t in text_parts if t]),
            "segments": segs,
            "duration_sec": getattr(info, "duration", None),
            "language": getattr(info, "language", language),
            "language_probability": getattr(info, "language_probability", None),
        }
