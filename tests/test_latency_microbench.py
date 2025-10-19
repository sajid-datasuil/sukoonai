import os
import pytest
from fastapi.testclient import TestClient
from app.api.server import app

skip = pytest.mark.skipif(not os.environ.get("SLOW_TESTS"), reason="Set SLOW_TESTS=1 to run micro-bench")

@skip
def test_mouth_to_ear_p95_under_gate():
    client = TestClient(app)
    vals = []
    for _ in range(20):
        d = client.post("/say", json={"text":"I feel anxious","locale":"en"}).json()
        vals.append(float(d["latency_ms"]["mouth_to_ear"]))
    vals.sort()
    p95 = vals[int(round(0.95*(len(vals)-1)))]
    assert p95 <= 1500.0
