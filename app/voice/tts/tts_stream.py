"""
Early toggle for local TTS (piper) — default OFF.

Env: VOICE_BACKEND_TTS={mock|piper}
This is a Week-2 placeholder that preserves the TTS cache hook.
"""
import os

def tts_backend_name() -> str:
    return os.environ.get("VOICE_BACKEND_TTS", "mock")

def synthesize(text: str):
    if tts_backend_name() != "piper":
        return b""  # mock audio bytes
    # Placeholder for piper synth; implement later; return WAV/PCM bytes
    return b""
