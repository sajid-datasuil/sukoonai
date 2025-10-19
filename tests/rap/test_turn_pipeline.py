import requests, os
BASE = os.environ.get("SUKOON_BASE","http://127.0.0.1:8001")
def test_turn_minimal():
    r = requests.post(f"{BASE}/api/web/turn", json={"text":"salaam"}, timeout=30)
    j = r.json()
    assert "audio_url" in j and "cost" in j and "evidence" in j
