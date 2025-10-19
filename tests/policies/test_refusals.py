import yaml
from app.agent.graph import SAFETY

def test_medication_refusal_en(tmp_path):
    # Simulate planner tagging a medication request
    state = {"policy_tags": ["clinical.ask_medication"], "lang": "en"}
    out = SAFETY(state)
    assert out["halt"] is True
    assert "I can’t advise on medicines" in out["final_text"]
    assert out["actions"]["whatsapp"] is True

def test_out_of_scope_ur(tmp_path):
    state = {"policy_tags": ["scope.out_of_scope"], "lang": "ur"}
    out = SAFETY(state)
    assert out["halt"] is True
    assert "دائرہ کار" in out["final_text"]
