"""Load the canonical financial-metric definitions used by Ask."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRIC_CONTRACT_PATH = ROOT / "docs" / "metric-contract.md"


def build_metric_contract_prompt() -> str:
    """Return the canonical contract verbatim so prompt and docs cannot drift."""

    return METRIC_CONTRACT_PATH.read_text(encoding="utf-8").strip()
