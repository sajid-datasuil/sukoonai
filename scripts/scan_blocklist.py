# scripts/scan_blocklist.py  (guardrail: count leaked real tokens before commit)
# -*- coding: utf-8 -*-
import sys, re
from pathlib import Path
from app.redaction import _load_blocklist_yaml

PAT_CODE = re.compile(r"\.(py|jsonl|yaml|yml|md|txt)$", re.I)

def scan(paths):
    cfg = _load_blocklist_yaml(Path("configs/blocklist_chat.yaml"))
    terms = []
    for k in ("intent","means","time"):
        terms += cfg.get(k, [])
    terms = [t for t in terms if t and not t.startswith("<")]
    if not terms:
        return {"files": 0, "hits": 0}
    pat = re.compile("|".join(re.escape(t) for t in terms), re.I)
    files = 0; hits = 0
    for p in paths:
        p = Path(p)
        if p.is_dir():
            for q in p.rglob("*"):
                if q.is_file() and PAT_CODE.search(q.suffix):
                    files += 1
                    txt = q.read_text(encoding="utf-8", errors="ignore")
                    hits += len(pat.findall(txt))
        elif p.is_file():
            files += 1
            txt = p.read_text(encoding="utf-8", errors="ignore")
            hits += len(pat.findall(txt))
    return {"files": files, "hits": hits}

if __name__ == "__main__":
    roots = sys.argv[1:] or ["."]
    res = scan(roots)
    print({"scanned_files": res["files"], "potential_leaks": res["hits"]})
    # Non-fatal: just report. You can change to non-zero exit to block commits.
    sys.exit(0)
