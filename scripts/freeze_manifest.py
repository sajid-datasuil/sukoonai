import json, hashlib
from pathlib import Path
import argparse

def sha256_file(p: Path):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True)
ap.add_argument("--out", required=True)
args = ap.parse_args()

src = Path(args.src)
items = []
for p in src.rglob("*"):
    if p.is_file():
        items.append({"path": str(p.relative_to(src)), "sha256": sha256_file(p)})

out = Path(args.out)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"version":"1.0","root":str(src), "count": len(items), "items": items}, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {len(items)} items → {out}")
