"""
PII-safe logging middleware.

- Redacts phone numbers, emails, and 10+ digit sequences.
- Never logs raw audio.
- Logs Decision JSON (shape only) and latencies.

Note: This is a conservative redactor; extend patterns as needed.
"""
from __future__ import annotations
import json
import logging
import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = logging.getLogger("app.middleware")

PHONE_EMAIL_RE = re.compile(
    r"(?P<email>[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})|(?P<digits>\b\d{10,}\b)|(?P<pk>\+92\d{7,})",
    re.IGNORECASE
)

def _redact(text: str) -> str:
    return PHONE_EMAIL_RE.sub(lambda m: "+92***" if m.group("pk") or m.group("digits") else "***@***", text)

class PIIRedactionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/voice"):  # no raw audio logs
            response = await call_next(request)
            return response

        try:
            body = (await request.body()).decode("utf-8", "ignore")
        except Exception:
            body = ""
        body_safe = _redact(body) if body else ""

        response: Response = await call_next(request)
        try:
            if response.media_type == "application/json":
                payload = json.loads(response.body.decode("utf-8"))
                # Summarize Decision JSON instead of dumping full PII-prone text
                summary = {
                    "path": request.url.path,
                    "status": response.status_code,
                    "latency_ms": payload.get("latency_ms"),
                    "actions_len": len(payload.get("actions", [])),
                    "evidence_ids": payload.get("evidence_ids", []),
                    "meta": {"asr": payload.get("meta", {}).get("asr_backend"),
                             "tts": payload.get("meta", {}).get("tts_backend"),
                             "consent": payload.get("meta", {}).get("consent")}
                }
                log.info("DECISION_JSON %s", _redact(json.dumps(summary)))
            else:
                log.info("REQ %s %s", request.url.path, body_safe[:256])
        except Exception:
            # Best-effort logging only.
            pass

        return response
