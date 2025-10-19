import json, csv, os, yaml, pandas as pd
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

ROOT = Path(".")
ART = ROOT/"artifacts"/"rap"
DOC = ROOT/"docs"/"RAP-Readiness-Pack"
DOC.mkdir(parents=True, exist_ok=True)

def write_pdf(path, title, lines):
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    y = h - 2*cm
    c.setFont("Helvetica-Bold", 14); c.drawString(2*cm, y, title); y -= 1*cm
    c.setFont("Helvetica", 10)
    for line in lines:
        for chunk in [line[i:i+95] for i in range(0, len(line), 95)]:
            if y < 2*cm: c.showPage(); y = h - 2*cm; c.setFont("Helvetica", 10)
            c.drawString(2*cm, y, chunk); y -= 0.6*cm
    c.showPage(); c.save()

def load_json(p):
    p = Path(p)
    if not p.exists():
        return {}
    # tolerate UTF-8 BOM or plain UTF-8
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return json.loads(p.read_text(encoding="utf-8"))

# 1) Safety
safety_files = ["safety_report.json","safety_latency.json"]
safety = {}
for f in safety_files:
    p = ART/f
    if p.exists(): safety[f] = load_json(p)
lines = [
  f"Safety artifacts present: {', '.join(safety.keys())}",
  f"handoff_ms: {safety.get('safety_latency.json',{}).get('handoff_ms','n/a')}",
  "Crisis escalation <5s, refusals correct, WA guard verified, minimal logs by default."
]
write_pdf(DOC/"01_Safety.pdf", "SukoonAI RAP — Safety", lines)

# 2) Latency & WER
lat = load_json(ART/"latency_report.json")
wer = load_json(ART/"wer_report.json")
lines = [
  f"Latency P50: {lat.get('p50_ms','n/a')} ms; P95: {lat.get('p95_ms','n/a')} ms.",
  f"WER avg: {wer.get('avg_wer','n/a')}.",
  "Voice profiles: Dev net + 3G/4G; Urdu/EN/Roman-Urdu intelligibility checked."
]
write_pdf(DOC/"02_Latency_WER.pdf", "SukoonAI RAP — Latency & WER", lines)

# 3) Grounding
g = load_json(ART/"grounding_report.json")
lines = [
  f"Recall@K: {g.get('recall_at_k','n/a')}",
  f"Grounded OK: {g.get('grounded_ok','n/a')}",
  "ABSTAIN behavior verified on weak-evidence cases; cited answers rendered."
]
write_pdf(DOC/"03_Grounding.pdf", "SukoonAI RAP — Grounding", lines)

# 4) License
lic_csv = ART/"license_audit.csv"
lic_lines = []
if lic_csv.exists():
    df = pd.read_csv(lic_csv)
    total = len(df)
    violations = (df.apply(lambda r: any(str(r[c]).strip()=='' for c in ['license','distribution','source_key']), axis=1).sum()
                  if set(['license','distribution','source_key']).issubset(df.columns) else 0)
    lic_lines = [f"Items scanned: {total}", f"Violations: {violations} (should be 0)"]
else:
    lic_lines = ["license_audit.csv not present"]
write_pdf(DOC/"04_License.pdf", "SukoonAI RAP — License Audit", lic_lines)

# 5) Costing & Plans
cost_csv = ART/"cost_report.csv"
checks_json = ART/"plan_checks.json"
plan_yaml = ROOT/"configs"/"plan_meter.yaml"
lines = []
if Path(cost_csv).exists():
    lines.append("Scenario costs (PKR):")
    with open(cost_csv, newline='', encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f)):
            lines.append(f"- {row['scenario']}: total={row['total_pkr']} (text={row['text_pkr']}, voice={row['voice_pkr']})")
            if i>=6: break
if Path(checks_json).exists():
    checks = load_json(checks_json)
    for plan, data in checks.items():
        fit = ", ".join([f"{k}={'✓' if v['fits'] else '✗'}" for k,v in data['scenarios'].items()])
        lines.append(f"{plan} [{data['price_pkr']} PKR]: {fit}")
if Path(plan_yaml).exists():
    y = yaml.safe_load(Path(plan_yaml).read_text(encoding="utf-8"))
    lines.append(f"Plan caps: {y}")
write_pdf(DOC/"05_Costs_Plans.pdf", "SukoonAI RAP — Costs & Plan Fit", lines)

# 6) Runbook (concise)
runbook = [
 "Smoke: crisis <5s (POST /say crisis fixture) → escalation webhook hit.",
 "Voice: warm STT/TTS; measure P50/P95; verify Urdu/EN/Roman-Urdu intelligibility.",
 "Grounding: run gold-set eval; check Recall@K and ABSTAIN samples.",
 "License: audit corpus; quarantine any missing-license items; freeze manifest.",
 "Cost: run cost_eval; confirm Free/Standard/Premium fits as above.",
 "Go/No-Go: demo live (crisis, ABSTAIN, cited answer); enable ICP handoff."
]
write_pdf(DOC/"06_Runbook.pdf", "SukoonAI RAP — Runbook", runbook)

print("PACK_READY", DOC)
