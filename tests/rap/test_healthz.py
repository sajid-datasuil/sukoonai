import requests, os
BASE = os.environ.get("SUKOON_BASE","http://127.0.0.1:8001")
def test_healthz():
    r = requests.get(f"{BASE}/healthz", timeout=5)
    j = r.json()
    assert j.get("status")=="ok"
    assert "engine" in j
