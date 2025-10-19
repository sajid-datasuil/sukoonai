import os, uuid
from datetime import datetime

AUDIO_ROOT = os.getenv("SUKOON_AUDIO_ROOT", "artifacts/audio")

class SapiTTS:
    """Lightweight Windows SAPI TTS fallback. Produces 16kHz mono WAV."""
    def synth(self, text: str, lang_hint: str = "ur") -> str:
        day = datetime.utcnow().strftime("%Y%m%d")
        out_dir = os.path.join(AUDIO_ROOT, "tts", day)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{datetime.utcnow().strftime('%H%M%S')}_{uuid.uuid4().hex[:8]}.wav")

        import win32com.client  # requires pywin32
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        stream = win32com.client.Dispatch("SAPI.SpFileStream")
        fmt = win32com.client.Dispatch("SAPI.SpAudioFormat")
        fmt.Type = 39  # SAFT16kHz16BitMono
        stream.Format = fmt
        stream.Open(out_path, 3, False)  # SSFMCreateForWrite
        voice.AudioOutputStream = stream

        # Try choose Urdu voice if available; otherwise fallback to default
        try:
            tokens = voice.GetVoices()
            wanted = "Urdu" if lang_hint.lower().startswith("ur") else "English"
            for i in range(tokens.Count):
                if wanted.lower() in tokens.Item(i).GetDescription().lower():
                    voice.Voice = tokens.Item(i)
                    break
        except Exception:
            pass

        voice.Speak(text)
        stream.Close()
        return out_path
