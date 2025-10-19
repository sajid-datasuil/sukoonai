import argparse
import json
import os
from collections import Counter, defaultdict
from jsonschema import Draft202012Validator

def load_schema(path="schemas/chunk.schema.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def iter_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl_path")
    args = ap.parse_args()

    # Preflight check (keeps failures clear)
    if not os.path.exists(args.jsonl_path):
        raise SystemExit(f"[validate_chunks] JSONL not found: {args.jsonl_path}")

    schema = load_schema()
    validator = Draft202012Validator(schema)

    n = 0
    lang = Counter()
    dist = Counter()
    missing_license = 0
    missing_source = 0
    crisis = 0
    by_license = Counter()
    by_source = Counter()
    by_topic = Counter()  # ← added

    issues = defaultdict(int)

    for rec in iter_jsonl(args.jsonl_path):
        errors = sorted(validator.iter_errors(rec), key=lambda e: e.path)
        if errors:
            for e in errors:
                issues[str(list(e.path)) + " :: " + e.message] += 1

        n += 1
        lang[rec.get("language", "other")] += 1

        d = rec.get("distribution")
        if d:
            dist[d] += 1

        if not rec.get("license"):
            missing_license += 1
        else:
            by_license[rec["license"]] += 1

        if not rec.get("source_url"):
            missing_source += 1
        else:
            by_source[rec.get("source_key", "unknown")] += 1

        if rec.get("crisis_flag"):
            crisis += 1

        # ← added: accumulate topic counts
        for t in rec.get("topics", []):
            if t:
                by_topic[t] += 1

    print(f"Validated: {n}")
    if issues:
        print("Schema issues:")
        for k, v in list(issues.items())[:10]:
            print(f"  {v} × {k}")
    else:
        print("Schema issues: 0")

    print(f"Languages: {dict(lang)}")
    print(f"Distribution: {dict(dist)}")
    print(f"License counts: {dict(by_license)}")
    print(f"Source counts: {dict(by_source)}")
    if by_topic:
        print(f"Topic counts: {dict(by_topic)}")  # ← added
    print(f"Missing license: {missing_license}")
    print(f"Missing source_url: {missing_source}")
    print(f"Crisis-flagged chunks: {crisis}")

if __name__ == "__main__":
    main()
