# app/web/status.py
from fastapi import APIRouter
from datetime import datetime, timezone
from app.ops.cost_meter import CostMeter

router = APIRouter()

@router.get("/status")
def status():
    return {
        "ok": True,
        "service": "SukoonAI",
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "channels": {"web": "ok", "voice": "ok", "wa_guard": "on"},
        "safety_sla": {"crisis_sec": 5, "wa_24h_guard": True},
    }

@router.get("/privacy")
def privacy():
    return {
        "product": "SukoonAI",
        "logging": "minimal",
        "retention_days": 0,
        "notes": "No transcripts stored; only aggregate cost/latency counters for ops."
    }
