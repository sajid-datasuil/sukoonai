import json, pathlib

ALLOWED = {"ALLOW", "REFUSE", "CRISIS"}
FIXDIR = pathlib.Path("datasets/fixtures/anxiety_depression/v1")

def iter_rows():
    for name in ("train.jsonl", "dev.jsonl", "test.jsonl"):
        p = FIXDIR / name
        assert p.exists(), f"Missing file: {p}"
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                raise AssertionError(f"{name}:{i} invalid JSON: {e}") from e
            yield name, i, row

def test_jsonl_rows_valid():
    seen_ids = set()
    for name, i, row in iter_rows():
        gl = row.get("gold_label")
        assert gl in ALLOWED, f"{name}:{i} bad gold_label={gl}"
        txt = row.get("text", "")
        assert isinstance(txt, str) and txt.strip(), f"{name}:{i} empty text"
        rid = row.get("id")
        assert isinstance(rid, str) and rid.strip(), f"{name}:{i} missing id"
        assert rid not in seen_ids, f"Duplicate id {rid} at {name}:{i}"
        seen_ids.add(rid)
