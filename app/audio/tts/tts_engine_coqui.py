# app/audio/tts/tts_engine_coqui.py
import os, uuid, datetime
from pathlib import Path

_model = None

def _ensure_model():
    global _model
    if _model is None:
        from TTS.api import TTS  # pip install TTS
        model_name = os.getenv("SUKOON_TTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
        _model = TTS(model_name)

def _dated_dir(root="artifacts/audio/tts"):
    day = datetime.datetime.utcnow().strftime("%Y%m%d")
    path = Path(root) / day
    path.mkdir(parents=True, exist_ok=True)
    return path

def synth(text: str, lang_hint: str = "ur", voice: str | None = None):
    _ensure_model()
    out_dir = _dated_dir()
    name = f"{datetime.datetime.utcnow().strftime('%H%M%S')}_{uuid.uuid4().hex[:8]}.wav"
    out_path = out_dir / name

    # XTTS expects ISO language codes; "ur" works for Urdu.
    language = "ur" if (lang_hint or "").lower().startswith("ur") else "en"
    # You can provide a reference speaker wav via SUKOON_TTS_SPEAKER_WAV; else use default.
    ref_wav = os.getenv("SUKOON_TTS_SPEAKER_WAV", None)

    _model.tts_to_file(
        text=text,
        file_path=str(out_path),
        speaker_wav=ref_wav if ref_wav else None,
        language=language,
    )
    return {"tts_path": str(out_path).replace("\\", "/"), "duration_sec": None}
