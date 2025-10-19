import os, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
dirs = ["app","artifacts","configs","data","datasets","docs","logs","prompts","schemas","scripts","tests"]
report = {}
for d in dirs:
    p = ROOT/d
    if p.exists():
        report[d] = sorted([x.name for x in p.iterdir() if x.is_dir()][:25])
with open(ROOT/"docs/Repo-Scan.json","w",encoding="utf-8") as f:
    json.dump(report, f, indent=2)
print("Wrote docs/Repo-Scan.json")
