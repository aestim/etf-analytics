"""Ask prompt defaults ambiguous return rankings to a comparable window."""

from ask import (
    DEFAULT_RETURN_LOOKBACK,
    MIN_DEFAULT_RETURN_OBSERVATIONS,
    SQL_SYSTEM_PROMPT,
)


def test_ambiguous_return_ranking_has_explicit_default_window():
    assert DEFAULT_RETURN_LOOKBACK == "1 year"
    assert "default lookback" in SQL_SYSTEM_PROMPT.lower()
    assert "period_start" in SQL_SYSTEM_PROMPT
    assert "as_of_date" in SQL_SYSTEM_PROMPT
    assert "observations" in SQL_SYSTEM_PROMPT


def test_default_ranking_requires_enough_observations():
    assert MIN_DEFAULT_RETURN_OBSERVATIONS == 200
    assert "HAVING COUNT(daily_return) >= 200" in SQL_SYSTEM_PROMPT
