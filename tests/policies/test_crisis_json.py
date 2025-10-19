from app.agent.graph import SAFETY, CrisisDecision

def test_crisis_decision_schema_ok():
    state = {
        "policy_tags": ["crisis.self_harm"],
        "lang": "en",
        "crisis_signals": {
            "intent": "yes",
            "plan": "unspecified",
            "means": "unknown",
            "timeframe": "today",
            "location": "home"
        }
    }
    out = SAFETY(state)
    assert out["halt"] is True
    dj = out["decision_json"]
    CrisisDecision.model_validate(dj)  # schema fit
    assert dj["actions"]["connect_human"] is True
    assert dj["actions"]["send_whatsapp"] is True

def test_escalate_deadline_bound():
    # Ensure the configured SLA is within 5s
    import json, pathlib
    cfg = json.loads(pathlib.Path("app/policies/crisis_flow.json").read_text(encoding="utf-8"))
    assert cfg["escalate_deadline_seconds"] <= 5
