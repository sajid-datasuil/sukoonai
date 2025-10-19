# app/audio/tts/tts_engine_sapi.py
import os, uuid, wave, contextlib, datetime

# --- Optional pyttsx3 import (graceful degrade) ---
try:
    import pyttsx3  # offline, SAPI5 on Windows
    _PYTTSX3_OK = True
except Exception:
    pyttsx3 = None
    _PYTTSX3_OK = False

# Ensure base artifacts folder exists
os.makedirs("artifacts/audio/tts", exist_ok=True)

def _dated_dir(root: str = "artifacts/audio/tts") -> str:
    """Create/return a UTC-dated directory for TTS outputs."""
    day = datetime.datetime.utcnow().strftime("%Y%m%d")
    path = os.path.join(root, day)
    os.makedirs(path, exist_ok=True)
    return path

def _wav_duration(path: str) -> float | None:
    """Compute WAV duration (seconds) safely."""
    try:
        with contextlib.closing(wave.open(path, "rb")) as wf:
            frames = wf.getnframes()
            rate = wf.getframerate() or 1
            return round(frames / float(rate), 3)
    except Exception:
        return None

# --------------------------------------------------------------------
# Low-level engine function (as in your patch): returns str|None path
# --------------------------------------------------------------------
def sapi_synth(text: str, **kwargs) -> str | None:
    """
    Return path to synthesized wav, or None if the engine is unavailable.
    Never raises for missing engine.
    """
    if not _PYTTSX3_OK:
        # Graceful degrade: no audio file, caller can continue.
        return None

    out_dir = _dated_dir()
    name = f"{datetime.datetime.utcnow().strftime('%H%M%S')}_{uuid.uuid4().hex[:8]}.wav"
    out_path = os.path.join(out_dir, name)

    eng = pyttsx3.init()

    # Optional voice selection if caller/env specifies (no-ops if not found)
    env_voice = os.getenv("SUKOON_TTS_VOICE")
    sel_voice = kwargs.get("voice") or env_voice
    if sel_voice:
        try:
            for v in eng.getProperty("voices") or []:
                if sel_voice.lower() in (v.name or "").lower():
                    eng.setProperty("voice", v.id)
                    break
        except Exception:
            pass

    # Optional rate/volume hints via environment (safe defaults)
    try:
        rate = int(os.getenv("SUKOON_TTS_RATE", "0"))  # 0 = leave default
        if rate:
            eng.setProperty("rate", rate)
    except Exception:
        pass
    try:
        vol = float(os.getenv("SUKOON_TTS_VOLUME", "0"))
        if vol:
            eng.setProperty("volume", max(0.0, min(1.0, vol)))
    except Exception:
        pass

    # Generate speech to file
    eng.save_to_file(text, out_path)
    eng.runAndWait()

    # Normalize path to POSIX for web usage
    return out_path.replace("\\", "/")

# --------------------------------------------------------------------
# High-level helper kept for backward compatibility with callers:
# returns a dict with tts_path + duration (same shape as before).
# --------------------------------------------------------------------
def synth(text: str, lang_hint: str = "ur", voice: str | None = None) -> dict:
    """
    Minimal SAPI/pyttsx3-based TTS.

    Returns a dict (backward-compatible with callers that extract tts_path):
        {"tts_path": "<posix_path>|None", "duration_sec": <float|None>}
    """
    posix_path = sapi_synth(text, voice=voice)

    if not posix_path:
        # Engine unavailable → graceful degrade
        return {"tts_path": None, "duration_sec": None}

    duration_sec = _wav_duration(posix_path)
    return {"tts_path": posix_path, "duration_sec": duration_sec}
