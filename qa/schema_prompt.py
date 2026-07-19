"""
Week 2 ①: 스키마 프롬프트 자동 생성기.

dbt 문서(marts/schema.yml)와 dim_etf 시드를 읽어 "우리 DB에는 이런
테이블·컬럼이 있다" 텍스트를 만든다. 손으로 쓰면 테이블이 바뀔 때마다
낡으므로 항상 파일에서 생성한다 — Week 1에서 schema.yml 설명을 공들여
채운 이유가 바로 이것.

실행:  python qa/schema_prompt.py   (생성 결과를 눈으로 확인)
"""

from __future__ import annotations

import csv
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MARTS_SCHEMA_YML = ROOT / "dbt" / "models" / "marts" / "schema.yml"
SEED_CSV = ROOT / "dbt" / "seeds" / "etf_info.csv"

# LLM이 질의할 수 있는 테이블 — sql_guard 화이트리스트와 단일 원천(single source)
SCHEMA_NAME = "public_marts"
ALLOWED_TABLES = ("dim_etf", "mart_etf_returns", "mart_etf_risk_metrics")


def _model_section(model: dict) -> str:
    lines = [f"Table: {SCHEMA_NAME}.{model['name']} — {model.get('description', '').strip()}"]
    for col in model.get("columns", []):
        lines.append(f"  - {col['name']}: {col.get('description', '').strip()}")
    return "\n".join(lines)


def _universe_section() -> str:
    """dim_etf 시드 요약 — '미국 장기채' 같은 말을 sub_class 값으로 잇게 해준다."""
    with open(SEED_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    lines = ["Current ETF universe (ticker / asset_class / sub_class / leverage):"]
    for r in rows:
        lines.append(f"  - {r['ticker']} / {r['asset_class']} / {r['sub_class']} / {r['leverage']}x")
    return "\n".join(lines)


def build_schema_prompt() -> str:
    models = yaml.safe_load(MARTS_SCHEMA_YML.read_text(encoding="utf-8"))["models"]
    sections = [_model_section(m) for m in models if m["name"] in ALLOWED_TABLES]
    sections.append(_universe_section())
    return "\n\n".join(sections)


if __name__ == "__main__":
    print(build_schema_prompt())
