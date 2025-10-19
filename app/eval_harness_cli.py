import json, argparse, pathlib
from app.eval_harness import evaluate

def read_jsonl(path):
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", required=True)
    ap.add_argument("--out", default="metrics.json")
    args = ap.parse_args()

    fixtures = list(read_jsonl(args.fixtures))
    metrics = evaluate(fixtures, model_call=None)
    pathlib.Path(args.out).write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
