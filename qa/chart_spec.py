"""
Week 3 (1/2): ChartSpec — the chart "form" the LLM fills in, and its validation.

Same core principle as the SQL layer: the LLM never writes chart code.
It only fills this form (JSON); drawing is done by the whitelisted
functions in render.py.

Validation philosophy: if the LLM names a column that doesn't exist, we
don't crash — we **fall back to a table**. Fail-safe by design.

Covered by tests/test_chart_spec.py.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd
from pydantic import BaseModel

ChartType = Literal["line", "bar", "scatter", "table"]


class ChartSpec(BaseModel):
    chart_type: ChartType
    x: str | None = None  # column name (not needed for table)
    y: str | None = None  # column name — must be numeric
    group_by: str | None = None  # column to color by (e.g. ticker)
    title: str = ""


TABLE_FALLBACK_REASONS: dict[str, str] = {}  # observability: last fallback reason


def validate_spec(spec: ChartSpec, df: pd.DataFrame) -> ChartSpec:
    """Check the spec is drawable against df — otherwise fall back to a table.

    Fallback triggers: x/y missing, unknown column, non-numeric y.
    If only group_by is wrong, keep the chart and just drop group_by.
    """

    def fallback(reason: str) -> ChartSpec:
        TABLE_FALLBACK_REASONS["last"] = reason
        return ChartSpec(chart_type="table", title=spec.title)

    TABLE_FALLBACK_REASONS.pop("last", None)  # clear the previous call's reason
    if spec.chart_type == "table":
        return spec
    cols = set(df.columns)
    if not spec.x or not spec.y:
        return fallback("x/y not specified")
    if spec.x not in cols or spec.y not in cols:
        return fallback(f"unknown column: {spec.x if spec.x not in cols else spec.y}")
    if not pd.api.types.is_numeric_dtype(df[spec.y]):
        return fallback(f"y is not numeric: {spec.y}")
    if spec.group_by and spec.group_by not in cols:
        spec = spec.model_copy(update={"group_by": None})
    return spec
