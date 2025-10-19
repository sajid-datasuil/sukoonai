from fastapi.testclient import TestClient
from app.api.server import app

client = TestClient(app)

def test_out_of_scope_abstain():
    r = client.post("/say", json={"text": "Tell me about diabetes", "locale": "en", "session_id": "t1"})
    d = r.json()
    assert d["intent"] == "out_of_scope"
    assert d["evidence_ids"] == []
    spoken = " ".join(a.get("text","") for a in d["actions"] if a.get("type")=="say")
    assert "trained for anxiety and depression" in spoken.lower()
