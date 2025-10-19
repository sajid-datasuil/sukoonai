import json, os, numpy as np
from faster_whisper import WhisperModel

OUT = r"artifacts/rap/wer_report.json"
FIX = [
    (r"artifacts/audio/wer/ur_1.wav",  "مجھے بے چینی محسوس ہو رہی ہے", "ur"),
    (r"artifacts/audio/wer/en_1.wav",  "I am feeling stressed and restless", "en"),
    (r"artifacts/audio/wer/rom_1.wav", "Today I feel a little anxious", "en")
]
MODEL_NAME = os.environ.get("WHISPER_MODEL", "small")
model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8", download_root="models/whisper")

def normalize(s: str) -> str:
    import re
    s = s.lower().strip()
    s = re.sub(r"[^\w\s\u0600-\u06FF]", " ", s)  # keep Urdu block & word chars
    return " ".join(s.split())

def wer(ref: str, hyp: str) -> float:
    r = normalize(ref).split()
    h = normalize(hyp).split()
    R, H = len(r), len(h)
    import numpy as np
    D = np.zeros((R+1, H+1), dtype=int)
    for i in range(R+1): D[i,0] = i
    for j in range(H+1): D[0,j] = j
    for i in range(1, R+1):
        for j in range(1, H+1):
            D[i,j] = min(D[i-1,j] + 1,
                         D[i,j-1] + 1,
                         D[i-1,j-1] + (r[i-1] != h[j-1]))
    return D[R,H] / max(1, R)

rows = []
for wav, ref, lang in FIX:
    segments, info = model.transcribe(
        wav, language=lang, vad_filter=True, beam_size=1, temperature=0.0
    )
    hyp = "".join(seg.text for seg in segments).strip()
    rows.append({"wav": wav, "ref": ref, "hyp": hyp, "wer": wer(ref, hyp)})

avg = float(np.mean([x["wer"] for x in rows])) if rows else 1.0
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump({"version":"1.0","avg_wer":avg,"items":rows}, f, ensure_ascii=False, indent=2)
print(f"avg_wer={avg:.4f} → {OUT}")
