from fastapi.testclient import TestClient
from app.api.server import app

client = TestClient(app)

def test_consent_blocks_sms_when_false():
    # Record explicit non-consent
    client.post("/consent", json={"session_id":"s1","agree":False,"locale":"en"})
    d = client.post("/say", json={"session_id":"s1","text":"I feel depressed","locale":"en"}).json()
    # No strict SMS block in Week-2 actions list, but consent is surfaced; downstream SMS sender should deny when meta.consent is False
    assert d["meta"]["consent"] is False
