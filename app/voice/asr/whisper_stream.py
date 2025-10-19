"""
Early toggle for local ASR (whisper.cpp) — default OFF.

Env: VOICE_BACKEND_ASR={mock|whispercpp}, NO_NETWORK=1 required for local offline.
This module is a stub for Week-2; returns mock partials unless explicitly toggled.
"""
import os

def asr_backend_name() -> str:
    return os.environ.get("VOICE_BACKEND_ASR", "mock")

def transcribe_stream(chunks):
    if asr_backend_name() != "whispercpp":
        for c in chunks:
            yield {"text": c, "final": True}  # mock passthrough
        return
    # Placeholder for whisper.cpp binding; implement in Week-3/5
    for c in chunks:
        yield {"text": c, "final": True}
