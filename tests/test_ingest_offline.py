from pathlib import Path
import json
from app.cli import ingest_cli  # noqa: F401

def test_ingest_offline(tmp_path, monkeypatch):
    # Run CLI
    import subprocess, sys, os
    cmd = [sys.executable, "-m", "app.cli.ingest_cli", "datasets"]
    cp = subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, "NO_NETWORK":"1"})
    assert cp.returncode == 0, cp.stderr
    out = json.loads(cp.stdout)
    assert out["total_chunks"] >= 2
    assert "phq9" in out["docs"] and out["docs"]["phq9"] >= 1
    assert "gad7" in out["docs"] and out["docs"]["gad7"] >= 1
    # Index files exist
    assert Path("data/index/meta.pkl").exists()
