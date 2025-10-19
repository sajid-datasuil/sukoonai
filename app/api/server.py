# app/api/server.py  — Urdu TTS + Indian English TTS (female) via ElevenLabs (opt-in) + SAPI fallback + persona "Sukoon"
from __future__ import annotations

import logging, hashlib, time, os, re, json, pathlib, tempfile, subprocess, shutil
from time import perf_counter
from typing import Dict, Any, Optional, Tuple
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import urllib.request, urllib.error  # for ElevenLabs HTTP calls

import yaml
from fastapi import FastAPI, Body, Response, Request, UploadFile, File, HTTPException, Query, Form
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.middleware import PIIRedactionMiddleware
# from app.agent.graph import plan_say   # removed per B1 patch
from app.policies.term_gates import detect_route
try:
    from app.graph.langgraph_pipeline import run as run_graph
except Exception:
    run_graph = None

log = logging.getLogger("app.server")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    log.info("Server starting...")
    yield
    log.info("Server stopping...")

app = FastAPI(title="SukoonAI", lifespan=lifespan)
app.add_middleware(PIIRedactionMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://127.0.0.1:8002", "http://localhost:8002", "file://"],
    allow_credentials=False, allow_methods=["*"], allow_headers=["*"],
)

_DEMO_DIR = "artifacts/ICP"
if os.path.isdir(_DEMO_DIR):
    app.mount("/static", StaticFiles(directory=_DEMO_DIR), name="static")
if os.path.isdir("artifacts"):
    app.mount("/media", StaticFiles(directory="artifacts"), name="media")

# ---------------- Feature flags & persona ----------------
ENABLE_VOICE_TURN = os.getenv("SUKOON_ENABLE_VOICE_TURN", "0") == "1"
ALLOW_URDU_TTS    = os.getenv("SUKOON_TTS_URDU", "0") == "1"
USE_TTS_FALLBACK  = os.getenv("SUKOON_TTS_FALLBACK", "0") == "1"
DET_MODE          = os.getenv("SUKOON_DET", "0") == "1"
DEBUG_GATES       = os.getenv("SUKOON_DEBUG", "0") == "1"
GRAPH_ON          = (os.getenv("SUKOON_GRAPH", "on").lower() != "off")

# Persona / brand
AGENT_NAME        = os.getenv("SUKOON_AGENT_NAME", "Sukoon")
AGENT_NAME_UR     = os.getenv("SUKOON_AGENT_NAME_UR", "سکون")

# English (India) preference + exact-name overrides
EN_IN_CULTURE     = os.getenv("SUKOON_TTS_EN_CULTURE", "en-IN")
EN_FORCE_NAME     = os.getenv("SUKOON_TTS_EN_NAME", "").strip()
UR_FORCE_NAME     = os.getenv("SUKOON_TTS_UR_NAME", "").strip()

# ---------- /ui ----------
@app.get("/ui", response_class=HTMLResponse)
def ui():
    primary = Path("artifacts/ICP/web/index.html").resolve()
    legacy  = Path("artifacts/ICP/demo_ui.html").resolve()
    html_path = primary if primary.exists() else legacy
    if html_path.exists():
        return FileResponse(html_path, headers={
            "Cache-Control": "no-store, max-age=0", "Pragma": "no-cache", "Expires": "0",
        })
    return {
        "ok": False,
        "error": "Web Demo UI not found",
        "expected_paths": [str(primary), str(legacy)],
    }

_CONSENT_TTL_S = 3600 * 4
_consent_map: Dict[str, Dict[str, Any]] = {}
def _purge_expired() -> None:
    ts = time.time()
    for sid, rec in list(_consent_map.items()):
        if ts - rec.get("ts", 0) > _CONSENT_TTL_S:
            _consent_map.pop(sid, None)

class ConsentIn(BaseModel):
    session_id: str
    agree: bool
    locale: Optional[str] = "en"
    timestamp_ms: Optional[int] = None

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/version")
def version():
    return {"name": "SukoonAI", "version": "0.2.0-week2"}

@app.get("/status")
def status_root():
    return {
        "ok": True,
        "service": "SukoonAI",
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "channels": {"web": "ok", "voice": "ok", "wa_guard": "on"},
        "safety_sla": {"crisis_sec": 5, "wa_24h_guard": True},
        "agent": {"name": AGENT_NAME, "name_ur": AGENT_NAME_UR, "voice_pref": {"en": "female en-IN", "ur": "female ur-*"}},
    }

@app.get("/privacy")
def privacy_root():
    return {
        "product": "SukoonAI",
        "logging": "minimal",
        "retention_days": 0,
        "notes": "No transcripts stored; only aggregate cost/latency counters for ops.",
    }

@app.get("/api/status")
def status_api():
    return status_root()

@app.get("/api/privacy")
def privacy_api():
    return privacy_root()

@app.get("/api/debug/gates")
def debug_gates(q: Optional[str] = Query(default=None, description="probe text")):
    if not DEBUG_GATES:
        raise HTTPException(status_code=404, detail="Not found")
    import app.policies.term_gates as tg, hashlib, inspect
    src = inspect.getsource(tg.detect_route).encode("utf-8", "ignore")
    out = {"module_file": getattr(tg, "__file__", None), "sha1": hashlib.sha1(src).hexdigest()[:12]}
    if q is not None:
        try:
            probed = tg.detect_route(q)
            out["probe"] = {"route": probed.get("route"),
                            "matched_terms": probed.get("matched_terms") or [],
                            "reason": probed.get("reason", None)}
        except Exception as e:
            out["probe_error"] = str(e)
    return out

@app.post("/consent")
def consent(c: ConsentIn):
    _purge_expired()
    _consent_map[c.session_id] = {"agree": c.agree, "locale": c.locale, "ts": time.time()}
    return {"ok": True, "meta": {"consent": c.agree, "session_id": c.session_id}}

try:
    from app.pipeline.turn import run_turn
except Exception:
    run_turn = None

class TurnIn(BaseModel):
    text: str
    mode: Optional[str] = "text"         # "text" | "voice"
    ui_lang: Optional[str] = None        # "auto"|"en"|"ur"
    ui_script: Optional[str] = None      # "roman"|"arabic"
    ui_auto: Optional[bool] = None

try:
    with open("configs/plan_meter.yaml", "r", encoding="utf-8") as _f:
        _PLAN_CFG = yaml.safe_load(_f)
except Exception:
    _PLAN_CFG = {"plans": {"Free": {"minutes_cap": 15}, "Standard": {"minutes_cap": 75}, "Premium": {"minutes_cap": 200}}}

def _cap(plan: str) -> int:
    try:
        return int(_PLAN_CFG.get("plans", {}).get(plan, {}).get("minutes_cap", 15))
    except Exception:
        return 15

_PLAN_USAGE: Dict[Tuple[str, str], int] = {}

def _cap_and_shape_evidence(items, cap: int = 3):
    if not items:
        return []
    out = []
    idx = 0
    for x in items:
        if not isinstance(x, dict):
            continue
        idx += 1
        iid   = (x.get("id") or x.get("doc_id") or x.get("docId") or x.get("source_id") or x.get("url") or "")
        title = (x.get("title") or x.get("name") or x.get("heading") or x.get("page_title") or "")
        snip  = (x.get("snippet") or x.get("summary") or x.get("text") or x.get("content") or "")
        iid   = str(iid).strip()
        title = str(title).strip()
        snip  = str(snip).strip()
        if not snip:
            any_txt = next((str(v) for k, v in x.items() if isinstance(v, str) and v.strip()), "")
            snip = any_txt.strip()[:280]
        if not title and snip:
            title = (snip[:80] + ("…" if len(snip) > 80 else ""))
        if not iid:
            iid = f"auto-{idx}"
        if iid and title and snip:
            out.append({"id": iid, "title": title, "snippet": snip})
        if len(out) >= cap:
            break
    return out

def _maybe_fix_mojibake(s: Any) -> Any:
    try:
        if not isinstance(s, str):
            return s
        suspect_chars = "ØÙÚÛÂÃàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþ"
        suspect = sum(ch in suspect_chars for ch in s) >= 2
        if not suspect:
            return s
        fixed = bytes(s, "latin-1", errors="ignore").decode("utf-8", errors="ignore")
        def arabic_count(text: str) -> int:
            return sum('\u0600' <= ch <= '\u06FF' for ch in text)
        if arabic_count(fixed) > arabic_count(s):
            return fixed
        return s
    except Exception:
        return s

def _looks_urdu(s: str) -> bool:
    try:
        return any('\u0600' <= ch <= '\u06FF' for ch in s)
    except Exception:
        return False

def _wants_roman_urdu(s: str) -> bool:
    if not s:
        return False
    if re.search(r'[\u0600-\u06FF]', s):
        return False
    low = s.lower()
    ru_particles = ("mujhe","mujh","mujhay","mujhei","tumhe","usko","isko","hai","hain","tha","thi","hun","hoon","ho",
                    "ka","ke","ki","mein","mai","me","par","per","se","ko","kr","kar","karo","karen","karenge",
                    "batao","samjhao","sikhao","do","karo")
    ru_wellness = ("saans","gehri saans","saans ki","mashq","ghabrahat","bechaini","sukoon","sakoon",
                   "tawajjo","tawajjoh","tawajju")
    particles_hits = sum(1 for w in ru_particles if w in low)
    wellness_hits  = sum(1 for w in ru_wellness  if w in low)
    has_54321      = bool(re.search(r'\b5-4-3-2-1\b|\b54321\b', low))
    return wellness_hits >= 1 or particles_hits >= 2 or has_54321

_ROMAN_2_URDU = [
    (r"\bgehri saans\b", "گہری سانس"),
    (r"\bsaans ki\b",    "سانس کی"),
    (r"\bsaans\b",       "سانس"),
    (r"\bmashq\b",       "مشق"),
    (r"\bghabrahat\b",   "گھبراہٹ"),
    (r"\bbechaini\b",    "بے چینی"),
    (r"\bsukoon\b|\bsakoon\b", "سکون"),
    (r"\btawajj?o+h?\b", "توجہ"),
    (r"\bmein\b|\bmei\b|\bmai\b", "میں"),
    (r"\bhoon\b|\bhun\b", "ہوں"),
    (r"\bho\b",          "ہو"),
    (r"\bka\b",          "کا"), (r"\bke\b", "کے"), (r"\bki\b", "کی"),
    (r"\bkr\b|\bkar\b",  "کر"),
]
def _roman_urdu_to_urdu(s: str) -> str:
    out = s
    for pat, rep in _ROMAN_2_URDU:
        out = re.sub(pat, rep, out, flags=re.IGNORECASE)
    return out

_URDU2ROMAN = [
  ("،", ", "), ("۔", "."),
  ("ہے", "hai"), ("ہیں", "hain"), ("ہوں","hoon"),
  ("اور","aur"), ("لیں","lein"), ("سانس","saans"), ("گہری","gehri"),
  ("باہر","bahar"), ("اندر","andar"), ("دھیان","dhyaan"), ("قدم","qadam"),
  ("آہستہ","aahista"), ("تیز","tez"), ("مشورہ","mashwara"),
]
def _urdu_to_roman(s: str) -> str:
    out = s
    for u, r in _URDU2ROMAN:
        out = out.replace(u, r)
    if any('\u0600' <= ch <= '\u06FF' for ch in out):
        out = ''.join(ch if ch < '\u0600' or ch > '\u06FF' else ' ' for ch in out)
    return re.sub(r'\s{2,}', ' ', out).strip()

# ---- ElevenLabs TTS helpers ----
def _tts_urdu_elevenlabs(text: str) -> Optional[str]:
    try:
        api_key  = os.getenv("SUKOON_TTS_API_KEY", "").strip()
        voice_id = os.getenv("SUKOON_TTS_UR_VOICEID", "").strip()
        if not api_key or not voice_id:
            return None
        base = Path("artifacts") / "audio" / "tts" / time.strftime("%Y%m%d")
        base.mkdir(parents=True, exist_ok=True)
        stem = time.strftime("%H%M%S_") + hashlib.sha1(text.encode("utf-8","ignore")).hexdigest()[:8]
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        body = json.dumps({
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": { "stability": 0.4, "similarity_boost": 0.8 }
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("xi-api-key", api_key)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "audio/wav")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                audio = resp.read(); ctype = resp.headers.get("Content-Type","").lower()
        except urllib.error.HTTPError:
            url2 = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
            req2 = urllib.request.Request(url2, data=body, method="POST")
            req2.add_header("xi-api-key", api_key)
            req2.add_header("Content-Type", "application/json")
            req2.add_header("Accept", "audio/wav")
            with urllib.request.urlopen(req2, timeout=60) as resp2:
                audio = resp2.read(); ctype = resp2.headers.get("Content-Type","").lower()
        if "wav" in ctype:
            out_wav = base / f"{stem}.wav"; out_wav.write_bytes(audio)
            return str(out_wav).replace("\\","/") if out_wav.stat().st_size > 256 else None
        out_mp3 = base / f"{stem}.mp3"; out_mp3.write_bytes(audio)
        if out_mp3.stat().st_size <= 256: return None
        ff = shutil.which("ffmpeg")
        if ff:
            out_wav = base / f"{stem}.wav"
            cmd = [ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(out_mp3),
                   "-ar", "22050", "-ac", "1", "-c:a", "pcm_s16le", str(out_wav)]
            subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if out_wav.exists() and out_wav.stat().st_size > 256:
                return str(out_wav).replace("\\","/")
        return str(out_mp3).replace("\\","/")
    except Exception as e:
        log.warning("ElevenLabs Urdu TTS error: %s", e)
        return None

def _tts_en_elevenlabs(text: str) -> Optional[str]:
    try:
        api_key  = os.getenv("SUKOON_TTS_API_KEY", "").strip()
        voice_id = os.getenv("SUKOON_TTS_EN_VOICEID", "").strip()
        if not api_key or not voice_id:
            return None
        base = Path("artifacts") / "audio" / "tts" / time.strftime("%Y%m%d")
        base.mkdir(parents=True, exist_ok=True)
        stem = time.strftime("%H%M%S_") + hashlib.sha1(text.encode("utf-8","ignore")).hexdigest()[:8]
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        body = json.dumps({
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": { "stability": 0.4, "similarity_boost": 0.8 }
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("xi-api-key", api_key)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "audio/wav")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                audio = resp.read(); ctype = resp.headers.get("Content-Type","").lower()
        except urllib.error.HTTPError:
            url2 = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
            req2 = urllib.request.Request(url2, data=body, method="POST")
            req2.add_header("xi-api-key", api_key)
            req2.add_header("Content-Type", "application/json")
            req2.add_header("Accept", "audio/wav")
            with urllib.request.urlopen(req2, timeout=60) as resp2:
                audio = resp2.read(); ctype = resp2.headers.get("Content-Type","").lower()
        if "wav" in ctype:
            out_wav = base / f"{stem}.wav"; out_wav.write_bytes(audio)
            return str(out_wav).replace("\\","/") if out_wav.stat().st_size > 256 else None
        out_mp3 = base / f"{stem}.mp3"; out_mp3.write_bytes(audio)
        if out_mp3.stat().st_size <= 256: return None
        ff = shutil.which("ffmpeg")
        if ff:
            out_wav = base / f"{stem}.wav"
            cmd = [ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(out_mp3),
                   "-ar", "22050", "-ac", "1", "-c:a", "pcm_s16le", str(out_wav)]
            subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if out_wav.exists() and out_wav.stat().st_size > 256:
                return str(out_wav).replace("\\","/")
        return str(out_mp3).replace("\\","/")
    except Exception as e:
        log.warning("ElevenLabs EN TTS error: %s", e)
        return None

# ---- SAPI fallback ----
def _sapi_fallback_tts(text: str, lang_hint: str = "en") -> Optional[str]:
    try:
        base = Path("artifacts") / "audio" / "tts" / time.strftime("%Y%m%d")
        base.mkdir(parents=True, exist_ok=True)
        fname = time.strftime("%H%M%S_") + hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()[:8] + ".wav"
        wav_path = base / fname
        tmp_txt = base / (fname.replace(".wav", ".txt"))
        tmp_txt.write_text(text, encoding="utf-8")

        if lang_hint == "ur":
            force_name = UR_FORCE_NAME.replace("'", "''")
            pick_voice = (
                "$fn='{force}';".format(force=force_name) +
                "$v=$null; Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                "if($fn){ try{ $synth.SelectVoice($fn); $v=$fn }catch{ $v=$null } }"
                "if(-not $v){"
                "  $f=@(); $a=@();"
                "  foreach($vv in $synth.GetInstalledVoices()){"
                "    $c=$vv.VoiceInfo.Culture.Name; $d=$vv.VoiceInfo.Description; $n=$vv.VoiceInfo.Name; $g=$vv.VoiceInfo.Gender.ToString();"
                "    if(($c -like 'ur*') -or ($d -match 'Urdu|Pakistan') -or ($n -match 'Urdu')){"
                "      if($g -eq 'Female'){ $f+=$n } else { $a+=$n }"
                "    }"
                "  }"
                "  if($f.Count -gt 0){ $v=$f[0] } elseif($a.Count -gt 0){ $v=$a[0] }"
                "}"
                "if($v){ $synth.SelectVoice($v) }"
            )
        else:
            force_name = EN_FORCE_NAME.replace("'", "''")
            pick_voice = (
                f"$pref='{EN_IN_CULTURE}';"
                "$fn='{force}';".format(force=force_name) +
                "$v=$null; Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                "if($fn){ try{ $synth.SelectVoice($fn); $v=$fn }catch{ $v=$null } }"
                "if(-not $v){"
                "  $f=@(); $a=@();"
                "  foreach($vv in $synth.GetInstalledVoices()){"
                "    $c=$vv.VoiceInfo.Culture.Name; $d=$vv.VoiceInfo.Description; $n=$vv.VoiceInfo.Name; $g=$vv.VoiceInfo.Gender.ToString();"
                "    if(($c -like ($pref+'*')) -or ($d -match 'India|English \\(India\\)|en-IN')){"
                "      if($g -eq 'Female'){ $f+=$n } else { $a+=$n }"
                "    }"
                "  }"
                "  if($f.Count -gt 0){ $v=$f[0] } elseif($a.Count -gt 0){ $v=$a[0] }"
                "}"
                "if($v){ $synth.SelectVoice($v) }"
            )

        ps = (
            "$ErrorActionPreference='Stop';"
            "Add-Type -AssemblyName System.Speech;"
            f"$p='{str(wav_path).replace('\\', '/')}';"
            f"$t='{str(tmp_txt).replace('\\', '/')}';"
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            f"{pick_voice}"
            "$txt=Get-Content -Raw -Encoding UTF8 $t;"
            "$s.SetOutputToWaveFile($p);"
            "$s.Rate = -2;"  # slower, warmer fallback delivery
            "$s.Speak($txt);"
            "$s.Dispose();"
        )
        res = subprocess.run(
            ["powershell","-NoProfile","-NonInteractive","-ExecutionPolicy","Bypass","-Command", ps],
            capture_output=True, text=True, timeout=60
        )
        try: tmp_txt.unlink(missing_ok=True)
        except Exception: pass

        if res.returncode != 0:
            log.warning("SAPI fallback failed: %s", res.stderr.strip() if res.stderr else "unknown")
            return None
        if wav_path.exists() and wav_path.stat().st_size > 256:
            return str(wav_path).replace("\\", "/")
        return None
    except Exception as e:
        log.warning("SAPI fallback exception: %s", e)
        return None

# ---- Optional STT (offline) via faster-whisper --------------------------------
def _stt_transcribe(path: str, lang_hint: Optional[str] = None) -> str:
    """
    If SUKOON_STT=whisper, attempt offline STT with faster-whisper.
    Model name via SUKOON_STT_MODEL (default 'base'). Returns '' on failure.
    Optionally pass lang_hint = 'en' or 'ur' to lock language.
    """
    try:
        from faster_whisper import WhisperModel
        model_name = os.getenv("SUKOON_STT_MODEL", "base")
        model = WhisperModel(model_name, device="cpu")
        # Ensure *transcribe* (not translate); help Whisper stay in the requested language
        kw = {"beam_size": 1, "vad_filter": True, "task": "transcribe"}
        if lang_hint in ("en", "ur"):
            kw["language"] = "en" if lang_hint == "en" else "ur"
        segments, info = model.transcribe(path, **kw)
        txt = " ".join(seg.text.strip() for seg in segments if getattr(seg, "text", "").strip())
        return (txt or "").strip()
    except Exception as e:
        log.info("Whisper STT not used or failed: %s", e)
        return ""

# ---------- Unified endpoint ----------
@app.post("/api/web/turn")
async def web_turn(request: Request, response: Response) -> Dict[str, Any]:
    assert run_turn is not None, "run_turn() not found; check app.pipeline.turn"
    _t0 = perf_counter()

    user_id = request.headers.get("X-User-Id", "demo")
    plan    = request.headers.get("X-Plan", "Free")
    today   = time.strftime("%Y%m%d")
    used    = int(_PLAN_USAGE.get((user_id, today), 0))
    capm    = _cap(plan)
    try:
        consume = max(1, int(request.headers.get("X-Debug-Plan-Use", "1")))
    except Exception:
        consume = 1
    next_used = used + consume
    if next_used > capm:
        over = {"user": user_id, "plan": plan, "cap_minutes": capm, "day": today, "used": used, "would_use": next_used}
        return {
            "ok": True,
            "route": "abstain",
            "answer": f"Plan cap reached for {plan}. Please upgrade to continue today.",
            "abstain": True,
            "overage": over,
        }

    _PLAN_USAGE[(user_id, today)] = next_used

    # ---------- Parse body ----------
    content_type = request.headers.get("content-type","").lower()
    is_multipart = "multipart/form-data" in content_type
    is_json      = "application/json" in content_type

    body_text: str = ""
    req_mode  : str = "text"
    ui_lang   : Optional[str] = None
    ui_script : Optional[str] = None
    ui_auto   : Optional[bool] = None

    inbound_audio_path: Optional[str] = None
    stt_text_for_echo: Optional[str] = None

    if is_multipart:
        form = await request.form()
        req_mode = (form.get("mode") or "voice").strip().lower()
        ui_lang  = (form.get("ui_lang") or "auto").strip().lower()
        file: UploadFile = form.get("audio")
        if not file:
            raise HTTPException(status_code=400, detail="audio file required")

        inc_dir = Path("artifacts") / "audio" / "incoming" / time.strftime("%Y%m%d")
        inc_dir.mkdir(parents=True, exist_ok=True)
        ext = ".webm"
        fpath = inc_dir / (time.strftime("%H%M%S_") + (file.filename or "voice") )
        if not str(fpath).lower().endswith((".webm",".wav",".ogg",".mp3")):
            fpath = fpath.with_suffix(ext)
        with open(fpath, "wb") as wf:
            wf.write(await file.read())
        inbound_audio_path = str(fpath).replace("\\","/")
        try:
            small_in = os.path.getsize(fpath) <= 256
        except Exception:
            small_in = True

        # ---- STT
        if ui_lang in (None, "", "auto"):
            lang_for_stub = "en"
        elif ui_lang in ("en","english"): lang_for_stub = "en"
        else: lang_for_stub = "ur"

        body_text = ""
        if os.getenv("SUKOON_STT","").lower() == "whisper":
            body_text = _stt_transcribe(str(fpath), lang_hint=("en" if lang_for_stub=="en" else "ur"))
            stt_text_for_echo = body_text or ""
        if not body_text:
            # Last-resort demo text; we’ll keep it only if the clip was truly tiny
            body_text = "Please greet the user briefly and supportively." if lang_for_stub=="en" else "براہ کرم مختصر اور حوصلہ افزا انداز میں جواب دیں۔"
            if not small_in:
                body_text += " (STT uncertain; try speaking a bit longer for better transcript.)"

    elif is_json:
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="invalid JSON")
        req_mode  = (payload.get("mode") or "text").strip().lower()
        ui_lang   = (payload.get("ui_lang") or None)
        ui_script = (payload.get("ui_script") or None)
        ui_auto   = payload.get("ui_auto", None)
        body_text = str(payload.get("text") or "").strip()
        if not body_text:
            raise HTTPException(status_code=400, detail="text required")
    else:
        try:
            payload = await request.json()
            req_mode  = (payload.get("mode") or "text").strip().lower()
            ui_lang   = (payload.get("ui_lang") or None)
            ui_script = (payload.get("ui_script") or None)
            ui_auto   = payload.get("ui_auto", None)
            body_text = str(payload.get("text") or "").strip()
        except Exception:
            raise HTTPException(status_code=415, detail="Unsupported Content-Type")

    # ---- Fast gates ----
    gate = detect_route(body_text)
    if gate["route"] == "crisis":
        return {"route": "crisis", "abstain": False, "answer": "", "timings": {"handoff_ms": 0}, "evidence": [], "usage": {"total_tokens": 0}}
    if gate["route"] == "abstain":
        _refuse_en = "I can’t provide investment predictions or trading tips."
        _refuse_ur = "میں سرمایہ کاری سے متعلق پیش گوئیاں یا خرید/فروخت کی تجاویز فراہم نہیں کر سکتی۔"
        _refusal = _refuse_en
        try:
            _looks_ur = _looks_urdu(body_text) or _wants_roman_urdu(body_text)
            if (ui_lang and str(ui_lang).lower() in ("ur","urdu","اردو")) or _looks_ur:
                _refusal = _refuse_ur
        except Exception:
            pass
        return {"route": "abstain", "abstain": True, "answer": _refusal,
                "timings": {"handoff_ms": 0}, "evidence": [], "usage": {"total_tokens": 0}}

    # ---- Language hint (server-side enforcement) ----
    hinted = body_text
    tx = body_text.lower()
    lang = None
    force_lock = bool(ui_lang)
    if ui_lang:
        if str(ui_lang).lower() in ("en","english"): lang = "English"
        elif str(ui_lang).lower() in ("ur","urdu","اردو"): lang = "Urdu"
    if (not force_lock) and lang is None and ((" in english" in tx) or ("english" in tx)):
        lang = "English"
    elif (not force_lock) and lang is None and (("urdu" in tx) or ("اردو" in body_text)):
        lang = "Urdu"
    if lang == "English":
        hinted += f"\n\nRespond ONLY in English. If steps are requested, give 3 short numbered steps. Keep it concise. Introduce yourself briefly as {AGENT_NAME} only when explicitly asked."
    elif lang == "Urdu":
        hinted += f"\n\nبراہ کرم صرف اردو میں جواب دیں۔ اگر اقدامات مانگے جائیں تو 3 مختصر، نمبر شدہ قدم دیں۔ اپنا تعارف صرف سوال ہو تو {AGENT_NAME_UR} کے طور پر دیں۔"
    if lang == "Urdu" and ( ((ui_script or "").lower() == "roman") or _wants_roman_urdu(body_text) ):
        hinted = "Reply in Roman Urdu (Latin script) — not Urdu script. Keep sentences short and supportive.\n\n" + hinted

    try:
        def _stable_bit(s: str) -> int:
            return hashlib.sha256(s.encode("utf-8", "ignore")).digest()[-1] & 1
        _h = 0 if DET_MODE else _stable_bit(body_text)
        if _h == 0 and lang == "English":
            hinted += "\n\nTone: supportive female coach. Use plain, active sentences."
        elif _h == 1 and lang == "Urdu":
            hinted += "\n\nلہجہ: نرم، پرسکون اور حوصلہ افزا — جیسے ایک سمجھدار دوست (female)."
    except Exception:
        pass

    out = run_turn(hinted)

    # ---- Phase-B: LangGraph skeleton (B1/B3) — attach graph & merge metrics/evidence
    try:
        if GRAPH_ON and callable(run_graph):
            g = run_graph(
                text=body_text,
                mode=req_mode,
                ui_lang=ui_lang,
                ui_script=ui_script,
                predecided_route=gate.get("route"),
            )
            # Attach graph; merge timings; and B3 pass-through (evidence + metrics incl. ckg)
            if isinstance(out, dict) and isinstance(g, dict):
                # Keep full trace if available
                if "graph" in g:
                    out["graph"] = g["graph"]

                # Evidence list (reranked hits with blended score + optional _ckg)
                if "evidence" in g:
                    out["evidence"] = g["evidence"]

                # Merge metrics: preserve existing node_ms merge, plus include other graph metrics (e.g., ckg)
                gm = (g.get("metrics") or {})
                if gm:
                    om = out.setdefault("metrics", {})
                    if isinstance(om, dict):
                        # merge node_ms (existing behavior)
                        node_ms = om.setdefault("node_ms", {})
                        if isinstance(node_ms, dict) and isinstance(gm.get("node_ms"), dict):
                            node_ms.update(gm["node_ms"])
                        # attach graph_total_ms if present
                        if "total_ms" in gm and "graph_total_ms" not in om:
                            om["graph_total_ms"] = gm["total_ms"]
                        # B3: shallow-merge remaining metric keys (e.g., 'ckg')
                        for k, v in gm.items():
                            if k == "node_ms" or k == "total_ms":
                                continue
                            om[k] = v
    except Exception as _graph_err:
        out.setdefault("warnings", []).append(f"graph_skeleton_error:{_graph_err.__class__.__name__}")

    # ---- Final language enforcement ----
    try:
        if isinstance(out, dict):
            ans = (out.get("answer") or "").strip()
            if ans:
                if lang == "English" and _looks_urdu(ans):
                    out["answer"] = (
                        "I’m here. Let’s slow things down together. "
                        "Try a 4–6 breath: inhale 4, exhale 6, three times."
                    )
                elif lang == "Urdu":
                    if (ui_script or "").lower() == "arabic" and not _looks_urdu(ans) and _wants_roman_urdu(ans):
                        out["answer"] = _roman_urdu_to_urdu(ans)
                    if (ui_script or "").lower() == "roman" and _looks_urdu(ans):
                        out["answer"] = _urdu_to_roman(ans)
                    if not _looks_urdu(out["answer"]) and not _wants_roman_urdu(out["answer"]):
                        out["answer"] = f"میں {AGENT_NAME_UR} ہوں۔ آپ کی مدد کے لیے حاضر ہوں۔ آئیں آہستہ آہستہ ایک ہلکی سانس لیں: چار تک گن کر سانس اندر، چھ تک گن کر سانس باہر۔ آپ کا سوال کیا ہے؟"
    except Exception:
        pass

    try:
        if isinstance(out, dict) and out.get("abstain") and gate.get("reason") == "wellness-allowlist":
            if lang == "Urdu" or _looks_urdu(body_text):
                fixed = "دو گہری، ہلکی سانسیں لیں: چار تک گن کر سانس اندر، چھ تک گن کر سانس باہر۔ پھر اپنے پیروں کا احساس کریں اور اردگرد کی تین چیزوں کے نام لیں۔"
            else:
                fixed = "Take two gentle deep breaths: inhale 4, exhale 6. Feel your feet on the floor and name three things you can see."
            out.update({"route": "assist", "abstain": False, "answer": fixed})
    except Exception:
        pass

    # ---- Always TTS from final answer for parity (primary EN→EL, UR as configured, else SAPI) ----
    try:
        if isinstance(out, dict):
            answer = (out.get("answer") or "").strip()
            out["answer_for_tts"] = answer
            out["answer_tts_sha8"] = hashlib.sha1(answer.encode("utf-8","ignore")).hexdigest()[:8] if answer else ""
            out["tts_path"] = None  # force regeneration from the *final* answer

            if answer and USE_TTS_FALLBACK:
                # Voice tab selection wins in voice mode; otherwise infer
                if req_mode == "voice":
                    if str(ui_lang or "").lower() in ("ur","urdu","اردو"): lang_hint = "ur"
                    elif str(ui_lang or "").lower() in ("en","english"):  lang_hint = "en"
                    else: lang_hint = "en"
                else:
                    lang_hint = "ur" if (_looks_urdu(answer) or _looks_urdu(body_text) or _wants_roman_urdu(body_text)) else "en"

                speak_text = answer
                if ALLOW_URDU_TTS and lang_hint == "ur" and not _looks_urdu(answer) and _wants_roman_urdu(body_text):
                    mapped = _roman_urdu_to_urdu(answer)
                    if any('\u0600' <= ch <= '\u06FF' for ch in mapped):
                        speak_text = mapped
                if not ALLOW_URDU_TTS and lang_hint == "ur":
                    lang_hint = "en"

                # English first: ElevenLabs, then Urdu EL if requested, finally SAPI
                if lang_hint == "en" and os.getenv("SUKOON_TTS_EN_PROVIDER","").lower() == "elevenlabs":
                    elp_en = _tts_en_elevenlabs(speak_text)
                    if elp_en:
                        out["tts_path"] = elp_en
                        try:
                            fs = elp_en if os.path.isabs(elp_en) else os.path.join(".", elp_en.replace("/", os.sep))
                            out.setdefault("timings", {})["tts_bytes"] = os.path.getsize(fs) if os.path.exists(fs) else 0
                            out.setdefault("warnings", []).append("tts_primary_elevenlabs_en")
                        except Exception:
                            pass

                if (not out.get("tts_path")) and lang_hint == "ur" and os.getenv("SUKOON_TTS_UR_PROVIDER","").lower() == "elevenlabs":
                    elp = _tts_urdu_elevenlabs(speak_text)
                    if elp:
                        out["tts_path"] = elp
                        try:
                            fs = elp if os.path.isabs(elp) else os.path.join(".", elp.replace("/", os.sep))
                            out.setdefault("timings", {})["tts_bytes"] = os.path.getsize(fs) if os.path.exists(fs) else 0
                            out.setdefault("warnings", []).append("tts_fallback_elevenlabs")
                        except Exception:
                            pass

                if not out.get("tts_path"):
                    sapip = _sapi_fallback_tts(speak_text, lang_hint=lang_hint)
                    if sapip:
                        out["tts_path"] = sapip
                        try:
                            fs = sapip if os.path.isabs(sapip) else os.path.join(".", sapip.replace("/", os.sep))
                            out.setdefault("timings", {})["tts_bytes"] = os.path.getsize(fs) if os.path.exists(fs) else 0
                            out.setdefault("warnings", []).append("tts_fallback_sapi")
                        except Exception:
                            pass
    except Exception as e:
        out.setdefault("warnings", []).append(f"tts_chain_error:{e.__class__.__name__}")

    # ---- Cache-busted media URL for browser (avoid duplicate/old audio) ----
    try:
        if out.get("tts_path"):
            rel = out["tts_path"].replace("\\","/")
            if rel.startswith("artifacts/"):
                out["tts_url"] = "/media/" + rel.split("artifacts/",1)[-1] + f"?v={int(time.time()*1000)}"
    except Exception:
        pass

    # ---- TTS guards (size + language) ----
    try:
        tp = out.get("tts_path")
        if tp:
            fs = tp if os.path.isabs(tp) else os.path.join(".", tp.replace("/", os.sep))
            size = os.path.getsize(fs) if os.path.exists(fs) else 0
            out.setdefault("timings", {})["tts_bytes"] = size
            if size <= 256:
                out["tts_path"] = None
                out.setdefault("warnings", []).append("tts_empty")
    except Exception:
        out.setdefault("warnings", []).append("tts_check_error")

    try:
        if not ALLOW_URDU_TTS and (_looks_urdu(body_text) or _wants_roman_urdu(body_text)):
            if out.get("tts_path"):
                out["tts_path"] = None
            out.setdefault("warnings", []).append("tts_lang_disabled_urdu")
    except Exception:
        pass

    # ---- Final presence/size guard ----
    try:
        tp2 = out.get("tts_path")
        if tp2:
            fs2 = tp2 if os.path.isabs(tp2) else os.path.join(".", tp2.replace("/", os.sep))
            if (not os.path.exists(fs2)) or os.path.getsize(fs2) <= 256:
                out["tts_path"] = None
                out.setdefault("warnings", []).append("tts_missing_or_small")
    except Exception:
        out.setdefault("warnings", []).append("tts_final_check_error")

    # ---- Branding safe-answers (unchanged behavior) ----
    try:
        qlow = body_text.lower()
        SAFE_BRAND = ("what is sukoonai", "sukoonai", "who are you", "about sukoonai", "privacy", "status")
        if any(p in qlow for p in SAFE_BRAND):
            if isinstance(out, dict) and out.get("route") != "crisis":
                out["route"] = "assist"; out["abstain"] = False
                ans = (out.get("answer") or "").strip().lower()
                if (not ans) or ("can’t provide" in ans) or ("can't provide" in ans) or ("معذرت" in (out.get("answer") or "")):
                    out["answer"] = (f"{AGENT_NAME} is a hybrid mental-wellness agent (Urdu/English) with a safety-first design. "
                                     "Use Text Mode for visible answers or Voice Mode for audio-only replies.")
    except Exception:
        pass

    # ---- Mojibake fixups (unchanged) ----
    try:
        if isinstance(out, dict):
            if "answer" in out:
                out["answer"] = _maybe_fix_mojibake(out["answer"])
            if isinstance(out.get("evidence"), list):
                for ev in out["evidence"]:
                    if isinstance(ev, dict):
                        if "title" in ev:   ev["title"] = _maybe_fix_mojibake(ev["title"])
                        if "snippet" in ev: ev["snippet"] = _maybe_fix_mojibake(ev["snippet"])
            re_e = out.get("retrieval", {}).get("evidence")
            if isinstance(re_e, list):
                for ev in re_e:
                    if isinstance(ev, dict):
                        if "title" in ev:   ev["title"] = _maybe_fix_mojibake(ev["title"])
                        if "snippet" in ev: ev["snippet"] = _maybe_fix_mojibake(ev["snippet"])
                        if "excerpt" in ev: ev["excerpt"] = _maybe_fix_mojibake(ev["excerpt"])
    except Exception:
        pass

    # ---- Breadcrumb to artifacts/ICP/last_turn.json (rich out incl. metrics) ----
    try:
        total_ms = int(round((perf_counter() - _t0) * 1000))
        m = out.setdefault("metrics", {})
        if not isinstance(m, dict): out["metrics"] = m = {}
        m.setdefault("total_ms", total_ms)
        out.setdefault("warnings", [])

        out_dir = pathlib.Path("artifacts/ICP"); out_dir.mkdir(parents=True, exist_ok=True)
        final_path = out_dir / "last_turn.json"
        with tempfile.NamedTemporaryFile(mode="w", delete=False, dir=str(out_dir), prefix="last_turn.", suffix=".json", encoding="utf-8") as tf:
            json.dump(out, tf, ensure_ascii=False, indent=2); temp_name = tf.name
        os.replace(temp_name, final_path)
    except Exception:
        pass

    # ---- Evidence shaping (unchanged) ----
    try:
        if isinstance(out, dict) and out.get("route") == "assist":
            out["evidence"] = _cap_and_shape_evidence(out.get("evidence"), cap=3)
    except Exception:
        pass

    # ---- Voice meta echo ----
    if is_multipart and inbound_audio_path:
        out.setdefault("meta", {})["in_audio"] = {"path": inbound_audio_path}
        if stt_text_for_echo is not None:
            out["stt_text"] = stt_text_for_echo

    return out
