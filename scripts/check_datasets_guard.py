"""
Datasets guard: if PR touches app/retrieval/* or configs/planner.yaml,
then docs/datasets.md must also be changed in the same commit range.

Usage (CI):
  python scripts/check_datasets_guard.py --base "$BASE" --head "$HEAD"
"""
from __future__ import annotations
import argparse, subprocess, sys

def git_changed(base: str, head: str) -> list[str]:
    out = subprocess.check_output(["git", "diff", "--name-only", f"{base}..{head}"], text=True)
    return [p.strip() for p in out.splitlines() if p.strip()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    args = ap.parse_args()

    changed = git_changed(args.base, args.head)
    touched_sensitive = any(p.startswith("app/retrieval/") or p == "configs/planner.yaml" for p in changed)
    if not touched_sensitive:
        print("datasets-guard: OK (no sensitive paths changed)")
        return 0
    if "docs/datasets.md" in changed:
        print("datasets-guard: OK (datasets.md updated)")
        return 0
    print("ERROR: Changing retrieval/planner requires docs/datasets.md to be updated with license/topic tags.")
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
