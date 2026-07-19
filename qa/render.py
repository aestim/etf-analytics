"""
Week 3 ②: 렌더러 4종 — 검증된 ChartSpec만 받아 실제로 그린다.

여기 있는 함수만 차트를 그릴 수 있다(화이트리스트). LLM이 만든 코드가
아니라 LLM이 채운 양식을 받는 것뿐이므로, 렌더러는 평범한 내 코드다.
대시보드의 line_chart()를 일반화한 것.

Covered by tests/test_chart_spec.py.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px

from chart_spec import ChartSpec

CHARTS_DIR = Path(__file__).resolve().parent / "charts"


def render(spec: ChartSpec, df: pd.DataFrame):
    """spec → plotly Figure. table 스펙이면 None (호출자가 표로 출력)."""
    if spec.chart_type == "table":
        return None
    kwargs: dict = {"x": spec.x, "y": spec.y}
    if spec.group_by:
        kwargs["color"] = spec.group_by
    if spec.title:
        kwargs["title"] = spec.title
    renderers = {"line": px.line, "bar": px.bar, "scatter": px.scatter}
    return renderers[spec.chart_type](df, **kwargs)


def save_html(fig, name_hint: str = "chart") -> Path:
    """Figure를 qa/charts/*.html로 저장하고 경로 반환 (브라우저로 열면 됨)."""
    CHARTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = CHARTS_DIR / f"{name_hint}_{stamp}.html"
    fig.write_html(path, include_plotlyjs="cdn")
    return path
