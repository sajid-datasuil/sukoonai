import os, sys, subprocess, json
from pathlib import Path

def test_grounding_eval_offline():
    # 1) Build index offline
    env = {**os.environ, "NO_NETWORK": "1"}
    cp = subprocess.run([sys.executable, "-m", "app.cli.ingest_cli", "datasets"],
                        capture_output=True, text=True, env=env)
    assert cp.returncode == 0, cp.stderr

    # 2) Run eval (recall@k >= 0.90)
    cp2 = subprocess.run([sys.executable, "-m", "app.eval.grounding_eval",
                          "--gold", "data/golden/anxiety_depression.json",
                          "--k", "5", "--min_recall", "0.90"],
                         capture_output=True, text=True, env=env)
    assert cp2.returncode == 0, cp2.stdout + "\n" + cp2.stderr
    out = json.loads(cp2.stdout)
    assert out["recall"] >= 0.90 and out["passed"] is True
