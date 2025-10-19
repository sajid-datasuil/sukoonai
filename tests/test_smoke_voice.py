from fastapi.testclient import TestClient
from app.api.server import app

client = TestClient(app)

def test_say_decision_json():
    payload = {"text": "Assalam o Alaikum, aaj kaisa mehsoos kar rahe hain?"}
    r = client.post("/say", json=payload)
    assert r.status_code == 200
    data = r.json()
    # Accept both legacy shape {"decision": {...}} and new root-level decision JSON
    d = data.get("decision", data)

    # Minimal sanity checks on the decision json
    assert isinstance(d, dict)
    assert "actions" in d
    assert "latency_ms" in d
    assert "meta" in d
