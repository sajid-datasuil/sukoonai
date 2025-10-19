# app/audio/tts/__init__.py
import os
import logging

logger = logging.getLogger("uvicorn.error")

# Prefer any existing legacy SAPI engine if present
try:
    # legacy path (some repos keep the old module name)
    from app.audio.tts_sapi import synth as _legacy_sapi_synth
except Exception:
    _legacy_sapi_synth = None

# Week-7 SAPI engine (current)
from .tts_engine_sapi import synth as _sapi_synth
from .tts_engine_sapi import sapi_synth  # low-level: returns str | None

def synth(*args, **kwargs):
    """
    Week-7 MVP: SAPI-only TTS returning a dict:
      {"tts_path": "<posix_path>|None", "duration_sec": <float|None>}
    We still read SUKOON_TTS_ENGINE for future flexibility, but we always
    dispatch to SAPI to honor the MVP hard constraint.
    """
    engine = os.getenv("SUKOON_TTS_ENGINE", "sapi").lower()
    if engine != "sapi":
        logger.warning("[tts] Non-SAPI engine requested (%s); forcing SAPI for MVP.", engine)

    if _legacy_sapi_synth is not None:
        try:
            return _legacy_sapi_synth(*args, **kwargs)
        except Exception:
            # fall through to current engine
            pass

    return _sapi_synth(*args, **kwargs)

def tts_synth(text: str, *args, **kwargs) -> str | None:
    """
    Low-level helper returning only the synthesized file path (or None).
    Never throws: gracefully handles missing/failed SAPI engine.
    """
    try:
        return sapi_synth(text, *args, **kwargs)
    except Exception:
        return None
