
### 3) Create `docs/CONTRIBUTING-Graph.md`
```powershell
@'
# Contributing — Graph Layer

- Keep `app/policies/term_gates.py` **unchanged** (source of truth for routes).
- Graph pipeline must remain **additive**: enrich response; never override A-phase fields.
- Timings must be integers (ms) and **> 0** for visibility (ns-precision timer with 1 ms floor).
- New nodes: add a `TraceItem` with `ms` and minimal shape for `hits`.
- Tests: extend `tests/test_graph_shape.py` (assert trace len ≥ 2 and node_ms > 0).
- Flag: `SUKOON_GRAPH=on|off` must gate all graph behavior.
'@ | Out-File -Encoding utf8 docs/CONTRIBUTING-Graph.md -Force
