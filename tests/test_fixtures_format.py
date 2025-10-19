# tests/test_fixtures_format.py
import json, re, pathlib
from jsonschema import validate
from schema import SCHEMA  # requires schema.py at repo root

BLOCK_RE = re.compile(r'^\[TEST CASE\]\ntext: ".*"\nlabel: (ALLOW|REFUSE|CRISIS)\ngoal\|notes: .+$', re.M)

def test_blocks_wrapped_correctly(markdown_path="docs/TESTCASE_FORMAT.md"):
    txt = pathlib.Path(markdown_path).read_text(encoding="utf-8")
    assert BLOCK_RE.search(txt), "Missing or malformed [TEST CASE] blocks"

def test_json_schema():
    for p in pathlib.Path("datasets/fixtures/anxiety_depression/v1").glob("*.jsonl"):
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            fx = json.loads(line)
            validate(instance=fx, schema=SCHEMA)
