from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from typing import Any, Dict
import os, tempfile, uuid, json
from datetime import datetime
from pathlib import Path

from app.safety.router import SafetyRouter
from app.ops.cost_meter import CostMeter
from app.audio.stt_faster_whisper import STTEngine
from app.pipeline.turn import run_turn  # merged previously

import csv  # (snippet) for feedback logging

router = APIRouter(prefix="/api/web", tags=["web"])

# Singletons
safety = SafetyRouter()
meter = CostMeter(config_path="configs/costing.yaml")
stt = STTEngine()

AUDIO_ROOT = os.getenv("SUKOON_AUDIO_ROOT", "artifacts/audio")


# ----------------------------- /api/web/chat -----------------------------
class ChatIn(BaseModel):
    text: str

@router.post("/chat")
def chat(inp: ChatIn) -> Dict[str, Any]:
    safety_result = safety.detect(inp.text)
    cost_info = meter.log_event(
        component="web",
        unit="per_message",
        units=1,
        metadata={"channel": "web", "bytes_in": len(inp.text.encode("utf-8"))}
    )
    reply = {
        "type": "placeholder",
        "text": "Thanks for your message! Full voice/chat loop lands in the next micro-step."
    }
    return {"ok": True, "safety": safety_result, "reply": reply, "cost": cost_info}


# ------------------------------ /api/web/stt ------------------------------
@router.post("/stt")
async def stt_upload(file: UploadFile = File(...)) -> Dict[str, Any]:
    # Ensure dated folders exist
    day = datetime.utcnow().strftime("%Y%m%d")
    up_dir = os.path.join(AUDIO_ROOT, "uploads", day)
    stt_dir = os.path.join(AUDIO_ROOT, "stt_json", day)
    os.makedirs(up_dir, exist_ok=True)
    os.makedirs(stt_dir, exist_ok=True)

    # Build deterministic file names
    base_ext = os.path.splitext(file.filename or "")[1] or ".wav"
    base_id  = f"{datetime.utcnow().strftime('%H%M%S')}_{uuid.uuid4().hex[:8]}"
    up_path  = os.path.join(up_dir, f"{base_id}{base_ext}")
    stt_path = os.path.join(stt_dir, f"{base_id}.json")

    # Persist upload to disk
    with open(up_path, "wb") as fout:
        fout.write(await file.read())

    # Transcribe
    result = stt.transcribe_file(up_path)

    # Minutes for metering (avoid zero)
    minutes = 0.0
    if result.get("duration_sec") is not None:
        minutes = round(float(result["duration_sec"]) / 60.0, 3)
        if minutes <= 0:
            minutes = 0.001

    cost_info = meter.log_event(
        component="stt",
        unit="per_minute",
        units=minutes,
        metadata={"filename": file.filename, "duration_sec": result.get("duration_sec"), "stored_path": up_path}
    )

    # Save STT JSON
    with open(stt_path, "w", encoding="utf-8") as f:
        json.dump({"input_file": up_path, "stt": result, "cost": cost_info}, f, ensure_ascii=False, indent=2)

    return {"ok": True, "paths": {"audio": up_path, "stt_json": stt_path}, "stt": result, "cost": cost_info}


# ----------------------------- /api/web/turn -----------------------------
class TurnIn(BaseModel):
    text: str
    lang: str | None = None  # align with snippet

@router.post("/turn")
def run_full_turn(inp: TurnIn):
    # Preserve existing behavior
    result = run_turn(inp.text, lang_hint=inp.lang or "ur")
    # Add browser-servable URL alongside existing tts_path (if present).
    tts_path = result.get("tts_path")
    if tts_path:
        web_path = Path(tts_path).as_posix()
        # Our audio writer already uses artifacts/*; expose it at /artifacts/*
        if web_path.startswith("artifacts/"):
            result["tts_url"] = "/" + web_path  # e.g., /artifacts/audio/tts/20251009/xyz.wav
    return result


# --------------------------- /api/web/feedback ---------------------------
class FeedbackIn(BaseModel):
    thumbs: str
    route: str | None = None
    had_evidence: bool | None = None
    text_len: int | None = None

@router.post("/feedback")
def feedback(inp: FeedbackIn) -> Dict[str, Any]:
    os.makedirs("artifacts/ops", exist_ok=True)
    path = "artifacts/ops/feedback_daily.csv"
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["ts_utc", "thumbs", "route", "had_evidence", "text_len"])
        from datetime import datetime, timezone
        w.writerow([
            datetime.now(timezone.utc).isoformat(),
            inp.thumbs,
            inp.route or "",
            bool(inp.had_evidence),
            int(inp.text_len or 0)
        ])
    return {"ok": True}
