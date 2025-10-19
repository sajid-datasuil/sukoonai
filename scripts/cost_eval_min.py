import csv, json
from pathlib import Path

plans = {
  "Free":     {"minutes": 15,  "price_pkr":    0, "turns":  50},
  "Standard": {"minutes": 75,  "price_pkr":  499, "turns": 200},
  "Premium":  {"minutes": 200, "price_pkr":  999, "turns": 600},
}
PKR_PER_TEXT_TURN = 0.35
PKR_PER_VOICE_MIN = 2.10

mix = [
  {"scenario":"starter_light", "text_turns":40,  "voice_min":10},   # Free fits
  {"scenario":"web_first",     "text_turns":200, "voice_min":60},   # Standard fits
  {"scenario":"mixed_50_50",   "text_turns":200, "voice_min":150},  # Premium fits
  {"scenario":"phone_heavy",   "text_turns":80,  "voice_min":300},  # requires overage/hotline
]

out_csv   = Path("artifacts/rap/cost_report.csv")
out_json  = Path("artifacts/rap/plan_checks.json")
plans_yaml= Path("configs/plan_meter.yaml")

rows = []
for m in mix:
    text_cost = round(m["text_turns"] * PKR_PER_TEXT_TURN, 2)
    voice_cost = round(m["voice_min"] * PKR_PER_VOICE_MIN, 2)
    rows.append({**m, "text_pkr": text_cost, "voice_pkr": voice_cost, "total_pkr": round(text_cost + voice_cost, 2)})

def fits(plan, m):
    return (m["voice_min"] <= plan["minutes"] * 1.1) and (m["text_turns"] <= plan["turns"] * 1.1)

checks = {}
for name, p in plans.items():
    checks[name] = {"price_pkr": p["price_pkr"], "caps": {"minutes": p["minutes"], "turns": p["turns"]}, "scenarios": {}}
    for m in mix:
        checks[name]["scenarios"][m["scenario"]] = {"fits": fits(p, m)}

out_csv.parent.mkdir(parents=True, exist_ok=True)
with out_csv.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["scenario", "text_turns", "voice_min", "text_pkr", "voice_pkr", "total_pkr"])
    w.writeheader()
    w.writerows(rows)

out_json.write_text(json.dumps(checks, indent=2), encoding="utf-8")
plans_yaml.parent.mkdir(parents=True, exist_ok=True)
plans_yaml.write_text(
"""# Caps for RAP plans
Free:
  minutes: 15
  turns: 50
  price_pkr: 0
Standard:
  minutes: 75
  turns: 200
  price_pkr: 499
Premium:
  minutes: 200
  turns: 600
  price_pkr: 999
""",
    encoding="utf-8",
)

print("WROTE", out_csv, out_json, plans_yaml, sep="\n")
