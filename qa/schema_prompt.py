"""
Week 2 (1/3): schema-prompt generator.

Reads the dbt docs (marts/schema.yml) and the dim_etf seed to build the
"here is what our database contains" text for the LLM. Hand-written schema
prompts go stale the moment a table changes, so this is always generated
from the files — which is exactly why the schema.yml descriptions were
written carefully in Week 1.

Run:  python qa/schema_prompt.py   (eyeball the generated prompt)
"""

from __future__ import annotations

import csv
from pathlib import Path

import yaml

from metric_contract import build_metric_contract_prompt

ROOT = Path(__file__).resolve().parents[1]
MARTS_SCHEMA_YML = ROOT / "dbt" / "models" / "marts" / "schema.yml"
SEED_CSV = ROOT / "dbt" / "seeds" / "etf_info.csv"

# Tables the LLM may query — single source of truth shared with sql_guard
SCHEMA_NAME = "public_marts"
ALLOWED_TABLES = ("dim_etf", "mart_etf_returns", "mart_etf_risk_metrics")


def _documented_models() -> list[dict]:
    return yaml.safe_load(MARTS_SCHEMA_YML.read_text(encoding="utf-8"))["models"]


def _model_section(model: dict) -> str:
    lines = [f"Table: {SCHEMA_NAME}.{model['name']} — {model.get('description', '').strip()}"]
    for col in model.get("columns", []):
        lines.append(f"  - {col['name']}: {col.get('description', '').strip()}")
    return "\n".join(lines)


def _universe_section() -> str:
    """Summary of the dim_etf seed — lets phrases like "long-term treasuries"
    (or Korean equivalents) be mapped to sub_class values."""
    with open(SEED_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    lines = ["Current ETF universe (ticker / asset_class / sub_class / leverage):"]
    for r in rows:
        lines.append(f"  - {r['ticker']} / {r['asset_class']} / {r['sub_class']} / {r['leverage']}x")
    return "\n".join(lines)


def build_schema_prompt() -> str:
    models = _documented_models()
    sections = [_model_section(m) for m in models if m["name"] in ALLOWED_TABLES]
    sections.append(_universe_section())
    sections.append(build_metric_contract_prompt())
    return "\n\n".join(sections)


def build_sqlglot_schema() -> dict[str, dict[str, dict[str, str]]]:
    """Return documented mart columns in sqlglot's schema-mapping format."""
    tables = {
        model["name"]: {
            column["name"]: "UNKNOWN" for column in model.get("columns", [])
        }
        for model in _documented_models()
        if model["name"] in ALLOWED_TABLES
    }
    return {SCHEMA_NAME: tables}


if __name__ == "__main__":
    print(build_schema_prompt())
