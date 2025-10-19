# TEST CASE Authoring Format (SukoonAI)

Wrap sensitive examples in chats exactly like:

[TEST CASE]
text: "<synthetic text>"
label: REFUSE | CRISIS | ALLOW
goal|notes: short rationale (e.g., "expect ABSTAIN→policy_refusal")

**JSONL fields (train/dev/test)**
- Required: `id`, `text`, `gold_label (ALLOW|REFUSE|CRISIS)`
- Optional: `lang`, `triggers[]`, `policy_tag`, `expected_action`, `notes`
- One JSON object per line. No trailing commas. ASCII quotes only.

**Rules**
- Bilingual allowed (Urdu/English).
- No PII; synthetic text only.
- Redact before pasting logs (use `app/redaction.py`).
- Ensure ids are unique across splits.

# EXACT REQUIRED BLOCK (literal; keep quotes and line breaks)
[TEST CASE]
text: "<synthetic text>"
label: ALLOW
goal|notes: demo block to satisfy format-lint

