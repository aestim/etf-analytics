"""Ask metric formatting remains semantic rather than query-specific."""

import pytest

from presentation import is_percent_metric


@pytest.mark.parametrize(
    "column",
    ["daily_return", "cumulative_return", "ytd_return", "drawdown", "annualized_vol_30d"],
)
def test_percent_metrics(column):
    assert is_percent_metric(column)


@pytest.mark.parametrize("column", ["ticker", "adj_close", "observations", "as_of_date"])
def test_non_percent_columns(column):
    assert not is_percent_metric(column)
