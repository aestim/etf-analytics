"""
The four renderers — draw only validated ChartSpecs.

Only the functions here can produce charts (a whitelist). They receive a
deterministically selected form, so the renderers remain plain, reviewable
code. A generalisation of the dashboard's line_chart().

Covered by tests/test_chart_spec.py.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px

from chart_spec import ChartSpec
from presentation import is_percent_metric

CHARTS_DIR = Path(__file__).resolve().parent / "charts"


def render(spec: ChartSpec, df: pd.DataFrame):
    """spec → plotly Figure. Returns None for a table spec (caller prints the df)."""
    if spec.chart_type == "table":
        return None
    kwargs: dict = {"x": spec.x, "y": spec.y}
    if spec.group_by:
        kwargs["color"] = spec.group_by
    if spec.title:
        kwargs["title"] = spec.title
    renderers = {"line": px.line, "bar": px.bar, "scatter": px.scatter}
    fig = renderers[spec.chart_type](df, **kwargs)
    if spec.chart_type == "scatter" and is_percent_metric(spec.x):
        fig.update_xaxes(tickformat=".1%")
    if is_percent_metric(spec.y):
        fig.update_yaxes(tickformat=".1%")
    return fig


def save_html(fig, name_hint: str = "chart") -> Path:
    """Save the figure to qa/charts/*.html and return the path."""
    CHARTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = CHARTS_DIR / f"{name_hint}_{stamp}.html"
    fig.write_html(path, include_plotlyjs="cdn")
    return path
