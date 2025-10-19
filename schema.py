# schema.py
SCHEMA = {
    "type": "object",
    "required": ["id", "text", "gold_label"],
    "properties": {
        "id": {"type": "string", "minLength": 1},
        "lang": {"type": "string"},
        "text": {"type": "string", "minLength": 1},
        "gold_label": {"enum": ["ALLOW", "REFUSE", "CRISIS"]},
        "triggers": {"type": "array", "items": {"type": "string"}},
        "policy_tag": {"type": "string"},
        "expected_action": {"type": "string"},
        "notes": {"type": "string"}
    },
    "additionalProperties": False
}
