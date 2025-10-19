@'
# Decision JSON (Phase-B Surface)

**Minimal example**
```json
{
  "route": "assist",
  "answer": "Here to help. Let's slow your breathing together…",
  "graph": {
    "trace": [
      {"node":"input","ms":5},
      {"node":"policy_gate","ms":2,"out":"assist"},
      {"node":"retrieve","ms":7,"k":3,"hits":[{"title":"PHQ-9 Official","score":0.71}]},
      {"node":"respond","ms":11}
    ]
  },
  "metrics": { "total_ms": 34, "node_ms": {"input":5,"policy_gate":2,"retrieve":7,"respond":11} }
}
