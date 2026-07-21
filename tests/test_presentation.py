"""Ask metric formatting remains semantic rather than query-specific."""

import pandas as pd
import pytest

from presentation import correlation_summary, is_percent_metric


@pytest.mark.parametrize(
    "column",
    ["daily_return", "cumulative_return", "ytd_return", "drawdown", "annualized_vol_30d"],
)
def test_percent_metrics(column):
    assert is_percent_metric(column)


@pytest.mark.parametrize("column", ["ticker", "adj_close", "observations", "as_of_date"])
def test_non_percent_columns(column):
    assert not is_percent_metric(column)


@pytest.mark.parametrize(
    ("coefficient", "description"),
    [
        (0.1, "very weak positive"),
        (-0.45, "moderate negative"),
        (0.81, "very strong positive"),
    ],
)
def test_correlation_summary_uses_executed_value(coefficient, description):
    summary = correlation_summary(pd.DataFrame({"correlation": [coefficient] * 3}))
    assert f"{coefficient:.2f}" in summary
    assert description in summary
    assert "does not establish causation" in summary


def test_correlation_summary_ignores_missing_coefficient():
    assert correlation_summary(pd.DataFrame({"ticker": ["SPY"]})) == ""
