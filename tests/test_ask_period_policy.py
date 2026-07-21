"""Ask prompt defaults ambiguous return rankings to a comparable window."""

from ask import (
    DEFAULT_RELATIONSHIP_LOOKBACK,
    DEFAULT_RETURN_LOOKBACK,
    MAX_HISTORICAL_LOOKBACK_YEARS,
    MIN_OBSERVATIONS_PER_YEAR,
    MIN_RELATIONSHIP_OBSERVATIONS,
    MIN_DEFAULT_RETURN_OBSERVATIONS,
    SQL_SYSTEM_PROMPT,
    _question_with_period_context,
    historical_lookback_years,
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
    assert "analysis across\n  the ETF universe is supported" in SQL_SYSTEM_PROMPT
    assert (
        "Cross-ETF relationship questions are descriptive data queries"
        in SQL_SYSTEM_PROMPT
    )
    assert "CORR(...) OVER ()" in SQL_SYSTEM_PROMPT


def test_explicit_historical_window_overrides_relationship_default():
    assert MAX_HISTORICAL_LOOKBACK_YEARS == 10
    assert MIN_OBSERVATIONS_PER_YEAR == 200
    assert historical_lookback_years("over the past 10 years") == 10
    assert historical_lookback_years("지난 5년 변동성") == 5
    assert historical_lookback_years("10-year CAGR and volatility") == 10
    assert historical_lookback_years("10년 CAGR 비교") == 10
    assert historical_lookback_years("in 10 years") == 10
    assert historical_lookback_years("Will it be more volatile 10 years from now?") is None
    assert historical_lookback_years("Predict the 10-year return") is None

    contents = _question_with_period_context(
        "Are high-volume ETFs more volatile over the past 10 years?"
    )
    assert "historical 10-year window" in contents
    assert "at least 2000 paired" in contents
    assert "not a future prediction" in contents


def test_prompt_distinguishes_historical_and_future_year_phrasing():
    assert "Never claim that the dataset only supports one year" in SQL_SYSTEM_PROMPT
    assert 'descriptive "in N years"' in SQL_SYSTEM_PROMPT
    assert '"from now"' in SQL_SYSTEM_PROMPT
    assert "2,000 for 10 years" in SQL_SYSTEM_PROMPT


def test_known_relationship_questions_are_canonical_examples():
    assert "레버리지 배수와 연환산 변동성의 상관관계는?" in SQL_SYSTEM_PROMPT
    assert "거래량과 변동성 사이에 관계가 있나?" in SQL_SYSTEM_PROMPT
    assert "avg_daily_dollar_volume" in SQL_SYSTEM_PROMPT
    assert "volume * p.adj_close" in SQL_SYSTEM_PROMPT
    assert "LN(NULLIF(avg_daily_dollar_volume, 0))" in SQL_SYSTEM_PROMPT
    assert "avg_annualized_vol_30d" in SQL_SYSTEM_PROMPT
    assert "How do return performance and volatility move together" in SQL_SYSTEM_PROMPT
    assert "AVG(m.annualized_vol_30d)" in SQL_SYSTEM_PROMPT


def test_long_term_performance_uses_cagr_policy():
    assert "performance windows of 2 years or longer" in SQL_SYSTEM_PROMPT
    assert "365.25 / NULLIF(MAX(price_date) - MIN(price_date), 0)" in SQL_SYSTEM_PROMPT


def test_generic_relationships_default_to_unleveraged_scope():
    assert "generic cross-ETF relationship" in SQL_SYSTEM_PROMPT
    assert "d.leverage = 1" in SQL_SYSTEM_PROMPT
    assert "the current unleveraged ETF subset (leverage = 1)" in SQL_SYSTEM_PROMPT
    assert "including leveraged funds" in SQL_SYSTEM_PROMPT


def test_ten_year_liquidity_and_cagr_examples_lock_the_contract():
    assert "higher average trading volume" in SQL_SYSTEM_PROMPT
    assert "CURRENT_DATE - INTERVAL '10 years'" in SQL_SYSTEM_PROMPT
    assert "HAVING COUNT(r.annualized_vol_30d) >= 2000" in SQL_SYSTEM_PROMPT
    assert "relationship between 10-year CAGR" in SQL_SYSTEM_PROMPT
    assert "CORR(cagr, avg_annualized_vol_30d)" in SQL_SYSTEM_PROMPT
