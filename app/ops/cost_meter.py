# app/ops/cost_meter.py
import csv
import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional, Any

try:
    import yaml  # PyYAML
except ImportError:
    yaml = None


class CostMeter:
    """
    Minimal cost/event logger.
    Reads PKR unit costs and plan caps from configs/costing.yaml,
    writes per-event rows to artifacts/ops/costs_daily.csv.
    """

    def __init__(self, config_path: str = "configs/costing.yaml", log_path: str = "artifacts/ops/costs_daily.csv"):
        self.config_path = config_path
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        self._config = self._load_config()
        self._ensure_header()

    def _load_config(self) -> Dict[str, Any]:
        if yaml is None or not os.path.exists(self.config_path):
            return {}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _ensure_header(self) -> None:
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    "ts_utc", "component", "unit", "units",
                    "unit_cost_pkr", "cost_pkr", "plan", "metadata_json"
                ])

    def _unit_cost_pkr(self, component: str, unit: str) -> float:
        """
        Supports:
          - flat: unit_costs[component][f"{unit}_pkr"]
          - nested llm: unit_costs["llm"][model][f"{unit}_pkr"] when component == "llm:model"
        """
        try:
            table = self._config.get("unit_costs", {})
            if ":" in component:
                comp, model = component.split(":", 1)
                return float(table[comp][model][f"{unit}_pkr"])
            return float(table[component][f"{unit}_pkr"])
        except Exception:
            return 0.0

    def current_plan(self) -> str:
        return os.getenv("SUKOON_PLAN", "standard")

    def log_event(self, component: str, unit: str, units: float = 1.0,
                  metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        uc = self._unit_cost_pkr(component, unit)
        cost = round(uc * float(units), 6)
        plan = self.current_plan()
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)

        with open(self.log_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                datetime.now(timezone.utc).isoformat(),
                component,
                unit,
                units,
                uc,
                cost,
                plan,
                meta_json
            ])

        return {
            "component": component,
            "unit": unit,
            "units": units,
            "unit_cost_pkr": uc,
            "cost_pkr": cost,
            "plan": plan
        }

    # Additive timings logger (no header changes; data goes into metadata_json)
    def log_timings(self, route: str, timings: Dict[str, float]) -> None:
        meta = {"route": route, **timings}
        self.log_event(component="timings", unit="per_turn", units=1.0, metadata=meta)
