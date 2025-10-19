
### `docs/SAFETY_POLICY.md`
```md
# Safety & Crisis Policy (SukoonAI)

- **Scope**: Anxiety & depression only.
- **ABSTAIN**:
  - Clinical medication advice → "I can’t advise on medicines."
  - Diagnosis → "I can’t diagnose conditions."
  - Legal → "I can’t provide legal advice."
- **Crisis**: Tags `crisis.self_harm` / `crisis.harm_others` route to `crisis_flow`:
  - Emit `decision_json`
  - `halt = true`
  - Escalation SLA < 5s
- **Languages**: Urdu / English / Roman-Urdu with culturally neutral urban PK accent.
