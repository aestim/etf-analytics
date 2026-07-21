"""Ask prompt defaults ambiguous return rankings to a comparable window."""

from ask import (
    DEFAULT_RELATIONSHIP_LOOKBACK,
    DEFAULT_RETURN_LOOKBACK,
    MIN_RELATIONSHIP_OBSERVATIONS,
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


def test_relationship_questions_are_in_scope_with_a_default_window():
    assert DEFAULT_RELATIONSHIP_LOOKBACK == "1 year"
    assert MIN_RELATIONSHIP_OBSERVATIONS == 200
    assert "full ETF universe is supported" in SQL_SYSTEM_PROMPT
    assert (
        "Relationship questions over all ETFs are descriptive data queries"
        in SQL_SYSTEM_PROMPT
    )
    assert "CORR(...) OVER ()" in SQL_SYSTEM_PROMPT


def test_known_relationship_questions_are_canonical_examples():
    assert "레버리지 배수와 연환산 변동성의 상관관계는?" in SQL_SYSTEM_PROMPT
    assert "거래량과 변동성 사이에 관계가 있나?" in SQL_SYSTEM_PROMPT
    assert "avg_daily_volume" in SQL_SYSTEM_PROMPT
    assert "avg_annualized_vol_30d" in SQL_SYSTEM_PROMPT
