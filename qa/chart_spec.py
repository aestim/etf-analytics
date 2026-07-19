"""
Week 3 ①: ChartSpec — LLM이 채우는 차트 "양식"과 그 검증.

대원칙 그대로: LLM은 차트 코드를 짜지 않는다. 이 양식(JSON)만 채우고,
그리는 건 render.py의 화이트리스트 함수들이 한다.

검증 철학: LLM이 없는 컬럼을 지정해도 에러로 죽지 않는다 —
**표(table)로 폴백**한다. "실패해도 안 죽는" 설계.

Covered by tests/test_chart_spec.py.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd
from pydantic import BaseModel

ChartType = Literal["line", "bar", "scatter", "table"]


class ChartSpec(BaseModel):
    chart_type: ChartType
    x: str | None = None  # 컬럼명 (table이면 불필요)
    y: str | None = None  # 컬럼명 — 수치형이어야 함
    group_by: str | None = None  # 색으로 구분할 컬럼 (예: ticker)
    title: str = ""


TABLE_FALLBACK_REASONS: dict[str, str] = {}  # 관찰용: 마지막 폴백 사유


def validate_spec(spec: ChartSpec, df: pd.DataFrame) -> ChartSpec:
    """스펙이 df에 대해 그릴 수 있는지 검사 — 아니면 표로 폴백.

    폴백 조건: x/y 미지정, 없는 컬럼, y가 수치형이 아님.
    group_by만 잘못된 경우엔 차트는 살리고 group_by만 버린다.
    """

    def fallback(reason: str) -> ChartSpec:
        TABLE_FALLBACK_REASONS["last"] = reason
        return ChartSpec(chart_type="table", title=spec.title)

    TABLE_FALLBACK_REASONS.pop("last", None)  # 이전 호출의 사유 제거
    if spec.chart_type == "table":
        return spec
    cols = set(df.columns)
    if not spec.x or not spec.y:
        return fallback("x/y 미지정")
    if spec.x not in cols or spec.y not in cols:
        return fallback(f"없는 컬럼: {spec.x if spec.x not in cols else spec.y}")
    if not pd.api.types.is_numeric_dtype(df[spec.y]):
        return fallback(f"y가 수치형 아님: {spec.y}")
    if spec.group_by and spec.group_by not in cols:
        spec = spec.model_copy(update={"group_by": None})
    return spec
