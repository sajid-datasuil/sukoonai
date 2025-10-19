from __future__ import annotations
import json, os, sys, subprocess
from pathlib import Path

def _ensure_index():
    env = {**os.environ, "NO_NETWORK": "1"}
    if not Path("data/index/meta.pkl").exists():
        cp = subprocess.run([sys.executable, "-m", "app.cli.ingest_cli", "datasets"],
                            text=True, capture_output=True, env=env)
        assert cp.returncode == 0, cp.stderr

def _run(ask: str) -> dict:
    env = {**os.environ, "NO_NETWORK": "1"}
    cmd = [sys.executable, "-m", "app.agent.grounded_planner", "--ask", ask]
    cp = subprocess.run(cmd, text=True, capture_output=True, env=env)
    assert cp.returncode == 0, cp.stderr
    return json.loads(cp.stdout)

def test_grounded_anxiety():
    _ensure_index()
    d = _run("How do I reduce anxiety?")
    assert d["abstain"] is False
    assert any(e["doc_id"] in ("gad7", "phq9") for e in d["evidence"])

def test_abstain_out_of_scope():
    _ensure_index()
    d = _run("Explain diabetes treatment options")
    assert d["abstain"] is True
