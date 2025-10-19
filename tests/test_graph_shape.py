# tests/test_graph_shape.py
from app.graph.langgraph_pipeline import run

def test_graph_shape_minimal():
    out = run("brief breathing help", mode="text", ui_lang="en")
    assert isinstance(out, dict)
    assert "graph" in out and "trace" in out["graph"]
    assert len(out["graph"]["trace"]) >= 2
    nm = out.get("metrics", {}).get("node_ms", {})
    for k in ["input", "policy_gate", "retrieve", "respond"]:
        assert k in nm and isinstance(nm[k], int) and nm[k] > 0
