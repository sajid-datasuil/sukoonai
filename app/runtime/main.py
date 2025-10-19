from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from datetime import datetime, timezone
import os

# --- startup fingerprint (kept) ---
import inspect
import logging
from app.pipeline import turn as TURN
from app.safety.router import SafetyRouter
# ----------------------------------

# Extras from snippet
import glob, time, shutil
from fastapi.staticfiles import StaticFiles
from app.channels.web.router import router as web_router
from app.audio.tts import synth as tts_synth  # warmup

app = FastAPI(title="SukoonAI Runtime (Week-7)")

# Ensure artifacts dir exists (safe if already present)
os.makedirs("artifacts", exist_ok=True)

# Expose generated audio (and other files) at /artifacts/*
app.mount("/artifacts", StaticFiles(directory="artifacts"), name="artifacts")

# Mount routers
app.include_router(web_router)

# Ensure essential dirs at startup + warmup + purge + fingerprint
@app.on_event("startup")
async def _ensure_dirs():
    os.makedirs("logs", exist_ok=True)
    os.makedirs("configs", exist_ok=True)
    os.makedirs("artifacts/audio/tts", exist_ok=True)

    # Optional TTS warmup (prevents first-turn stutter)
    if os.getenv("SUKOON_TTS_WARMUP", "0") == "1":
        out = tts_synth("آواز کی جانچ ہو رہی ہے", lang_hint="ur") or {}
        # best-effort cleanup of warmup file
        p = out.get("tts_path") if isinstance(out, dict) else None
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    # Optional purge of old WAVs (artifacts hygiene)
    ndays = os.getenv("ARTIFACT_RETENTION_DAYS")
    if ndays and ndays.isdigit():
        cutoff = time.time() - (int(ndays) * 86400)
        for wav in glob.glob("artifacts/audio/tts/**/*.*", recursive=True):
            try:
                if os.path.getmtime(wav) < cutoff:
                    os.remove(wav)
            except Exception:
                pass

    # --- startup fingerprint (no behavior change) ---
    logger = logging.getLogger("uvicorn.error")
    has_abstain = "کریپٹو" in inspect.getsource(TURN.run_turn)
    crisis_probe = SafetyRouter().detect("مجھے خود کو نقصان پہنچانے کے خیالات آ رہے ہیں")
    logger.info(f"[startup-fingerprint] abstain_block={has_abstain} crisis_detect={crisis_probe}")
    # -------------------------------------------------

@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "service": "sukoonai-runtime",
        "ts": datetime.now(timezone.utc).isoformat(),
        "engine": os.getenv("SUKOON_TTS_ENGINE", "sapi"),
        "version": os.getenv("SUKOON_VERSION", "0.7.0"),
    }

@app.get("/privacy", response_class=PlainTextResponse)
def privacy_notice():
    return (
        "پرائیویسی نوٹس — سکوون اے آئی (MVP)\n"
        "• پہلے استعمال پر کوئی اکاؤنٹ نہیں بنتا؛ کم سے کم ڈیٹا محفوظ کیا جاتا ہے۔\n"
        "• مختصر مدت کے لیے ٹرانسکرپٹس/آڈیو عارضی فولڈرز میں رہ سکتے ہیں؛ بعد ازاں صاف کر دیے جاتے ہیں۔\n"
        "• ہنگامی/بحران کی صورت میں فوری رہنمائی دی جاتی ہے؛ یہ طبی تشخیص نہیں۔\n"
        "• حذف کی درخواست: privacy@sukoon.ai پر ای میل کریں۔\n"
    )

@app.get("/web", response_class=HTMLResponse)
def web_placeholder():
    # Minimal debug UI with chat + STT upload + Full Turn (LLM+TTS)
    return """<!doctype html>
<html>
<head><meta charset="utf-8"><title>SukoonAI – Web Chat</title></head>
<body style="font-family: Arial, sans-serif; margin: 2rem; max-width: 720px;">
  <h2>SukoonAI – Web Chat</h2>

  <div id="price" style="background:#f0f8ff;border:1px solid #cfe; padding:.75rem; margin:.5rem 0;">
    <strong>Pricing (PKR):</strong> Free (1 voiced reply/day) · Weekly 199 · Monthly 499 —
    <a target="_blank" href="https://forms.gle/REQUEST-ACCESS">Request Access</a>
  </div>

  <p>Type a message and press Send. You can also run the full safety→LLM→TTS turn.</p>

  <!-- Text chat -->
  <textarea id="msg" rows="5" style="width:100%;"></textarea><br/>
  <button id="send">Send</button>
  <pre id="out" style="background:#f5f5f5; padding:1rem; white-space:pre-wrap;"></pre>

  <div id="fb" style="margin:.5rem 0;">
    <button id="fb_up">👍</button>
    <button id="fb_dn">👎</button>
    <span id="fb_msg" style="margin-left:.5rem;color:#555;"></span>
  </div>

  <hr/>
  <!-- STT upload -->
  <h3>STT Upload (WAV/MP3/M4A)</h3>
  <input type="file" id="audio" accept="audio/*">
  <button id="sttBtn">Transcribe</button>
  <pre id="sttOut" style="background:#f5f5f5; padding:1rem; white-space:pre-wrap;"></pre>

<script>
const $ = (id)=>document.getElementById(id);

$("send").onclick = async ()=>{
  const text = $("msg").value || "";
  const res = await fetch("/api/web/chat", {
    method:"POST", headers: {"Content-Type":"application/json"},
    body: JSON.stringify({text})
  });
  const json = await res.json();
  $("out").textContent = JSON.stringify(json, null, 2);
};

$("sttBtn").onclick = async ()=>{
  const f = $("audio").files[0];
  if(!f){ alert("Choose an audio file first."); return; }
  const fd = new FormData(); fd.append("file", f, f.name);
  const res = await fetch("/api/web/stt", { method: "POST", body: fd });
  const json = await res.json();
  $("sttOut").textContent = JSON.stringify(json, null, 2);
};

// NEW: full turn button
const turnBtn = document.createElement("button");
turnBtn.textContent = "Run Full Turn (LLM+TTS)";
turnBtn.style.marginLeft = "8px";
turnBtn.onclick = async ()=>{
  const text = $("msg").value || "";
  const res = await fetch("/api/web/turn", {
    method:"POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({text, lang: "ur"})
  });
  const json = await res.json();
  $("out").textContent =
    (json.tts_path ? `TTS saved: ${json.tts_path}\\n\\n` : "") +
    JSON.stringify(json, null, 2);

  // Auto-play SukoonAI audio if server provided a tts_url
  if (json && json.tts_url) {
    let audio = document.getElementById("sukoon-audio");
    if (!audio) {
      audio = document.createElement("audio");
      audio.id = "sukoon-audio";
      audio.controls = true;   // visible controls if autoplay is blocked
      audio.preload = "auto";
      document.body.appendChild(audio);
    }
    // cache-bust to avoid stale audio
    audio.src = json.tts_url + "?t=" + Date.now();
    audio.play().catch(() => { /* browsers may gate autoplay; controls remain */ });
  }
  // -----------------------------------------------------------------------
};
$("send").insertAdjacentElement('afterend', turnBtn);

// Feedback buttons
async function sendFeedback(thumbs){
  const last = $("out").textContent || "";
  let route=""; let had=false; let len=0;
  try { const obj = JSON.parse(last.replace(/^TTS saved:.*\\n\\n/,""));
        route = obj.route || "";
        had = !!(obj.retrieval && obj.retrieval.evidence && obj.retrieval.evidence.length);
        len = (obj.answer||"").length; } catch(e) {}
  await fetch("/api/web/feedback",{
    method:"POST", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({thumbs: thumbs, route: route, had_evidence: had, text_len: len})
  });
  $("fb_msg").textContent = "Thanks for the feedback!";
}
$("fb_up").onclick = ()=>sendFeedback("up");
$("fb_dn").onclick = ()=>sendFeedback("down");
</script>
</body>
</html>"""
