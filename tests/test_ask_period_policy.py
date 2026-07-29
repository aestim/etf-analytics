"""Ask prompt defaults ambiguous return rankings to a comparable window."""

import pytest

import ask
from ask import (
    DEFAULT_RELATIONSHIP_LOOKBACK,
    DEFAULT_RETURN_LOOKBACK,
    FEW_SHOTS,
    FULL_PERIOD_BOUNDARY_TOLERANCE_DAYS,
    MAX_ASK_LOOKBACK_YEARS,
    MIN_OBSERVATIONS_PER_YEAR,
    MIN_RELATIONSHIP_OBSERVATIONS,
    MIN_DEFAULT_RETURN_OBSERVATIONS,
    SQL_SYSTEM_PROMPT,
    _question_with_period_context,
    historical_lookback_years,
    historical_window_limit_reason,
)
from sql_guard import validate


def test_ambiguous_return_ranking_has_explicit_default_window():
    assert DEFAULT_RETURN_LOOKBACK == "1 year"
    assert "default lookback" in SQL_SYSTEM_PROMPT.lower()
    assert "period_start" in SQL_SYSTEM_PROMPT
    assert "as_of_date" in SQL_SYSTEM_PROMPT
    assert "observations" in SQL_SYSTEM_PROMPT


def test_default_ranking_requires_enough_observations():
    assert MIN_DEFAULT_RETURN_OBSERVATIONS == 200
    assert "at least 200 in-window returns" in SQL_SYSTEM_PROMPT
    assert "COUNT(*) - 1 >= 200" in SQL_SYSTEM_PROMPT


def test_ticker_definitions_have_one_policy_per_side_of_the_universe():
    """Use stored descriptions in-universe and labelled knowledge outside it."""
    # In-universe: grounded in dim_etf, not the model's memory.
    assert "IS in the universe list below is a\n  data_query" in SQL_SYSTEM_PROMPT
    assert "that stored description in the user's language" in SQL_SYSTEM_PROMPT
    # Out-of-universe: general knowledge with an explicit provenance caveat,
    # no invented figures, and a pointer to the Add ETF search.
    assert "NOT in the universe list below" in SQL_SYSTEM_PROMPT
    assert "general\n  knowledge rather than this app's data" in SQL_SYSTEM_PROMPT
    assert "Never\n  state precise current figures" in SQL_SYSTEM_PROMPT
    assert "Add ETF search" in SQL_SYSTEM_PROMPT
    # The refusal bullet must defer to those rules rather than catching them.
    assert "describing what a fund is, per the rules above" in SQL_SYSTEM_PROMPT


def test_universe_definition_sql_passes_the_guard():
    """The exact query shape the prompt prescribes must survive validation."""
    validate(
        "SELECT ticker, name, asset_class, sub_class, leverage, description "
        "FROM public_marts.dim_etf WHERE ticker = 'SGOV'"
    )


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
    assert MAX_ASK_LOOKBACK_YEARS == 20
    assert MIN_OBSERVATIONS_PER_YEAR == 200
    assert historical_lookback_years("over the past 10 years") == 10
    assert historical_lookback_years("over the past 20 years") == 20
    assert historical_lookback_years("지난 5년 변동성") == 5
    assert historical_lookback_years("최근 20년 변동성") == 20
    assert historical_lookback_years("10-year CAGR and volatility") == 10
    assert historical_lookback_years("10년 CAGR 비교") == 10
    assert historical_lookback_years("in 10 years") == 10
    assert (
        historical_lookback_years("Will it be more volatile 10 years from now?") is None
    )
    assert historical_lookback_years("Predict the 10-year return") is None

    contents = _question_with_period_context(
        "Are high-volume ETFs more volatile over the past 10 years?"
    )
    assert "historical 10-year window" in contents
    assert "at least 2000 paired" in contents
    assert "not a future prediction" in contents


def test_twenty_year_context_requires_count_and_calendar_coverage():
    contents = _question_with_period_context(
        "Compare SPY and QQQ over the past 20 years"
    )

    assert FULL_PERIOD_BOUNDARY_TOLERANCE_DAYS == 14
    assert "historical 20-year window" in contents
    assert "at least 4000 paired" in contents
    assert "period_start and period_end within 14 days" in contents
    assert "never describe stale or post-inception partial history" in contents


def test_window_above_twenty_years_is_refused_before_llm(monkeypatch):
    monkeypatch.setattr(
        ask,
        "generate_sql",
        lambda question: pytest.fail("Out-of-policy windows must not call the LLM"),
    )

    assert "최대 20년" in historical_window_limit_reason("지난 21년 수익률")
    result = ask.answer("지난 21년 수익률")

    assert result.status == "refused_gate"
    assert "최대 20년" in result.reason


def test_prompt_distinguishes_historical_and_future_year_phrasing():
    assert "Never claim that the dataset only supports one year" in SQL_SYSTEM_PROMPT
    assert 'descriptive "in N years"' in SQL_SYSTEM_PROMPT
    assert '"from now"' in SQL_SYSTEM_PROMPT
    assert "maximum vendor history available" in SQL_SYSTEM_PROMPT
    assert "4,000 for 20 years" in SQL_SYSTEM_PROMPT
    assert "never silently shorten it" in SQL_SYSTEM_PROMPT


def test_known_relationship_questions_are_canonical_examples():
    assert "레버리지 배수와 연환산 변동성의 상관관계는?" in SQL_SYSTEM_PROMPT
    assert "거래량과 변동성 사이에 관계가 있나?" in SQL_SYSTEM_PROMPT
    assert "avg_daily_dollar_volume" in SQL_SYSTEM_PROMPT
    assert "volume * p.adj_close" in SQL_SYSTEM_PROMPT
    assert "LN(NULLIF(avg_daily_dollar_volume, 0))" in SQL_SYSTEM_PROMPT
    assert "period_annualized_volatility" in SQL_SYSTEM_PROMPT
    assert "How do return performance and volatility move together" in SQL_SYSTEM_PROMPT
    assert "STDDEV_SAMP(period_daily_return) * SQRT(252)" in SQL_SYSTEM_PROMPT
    assert "AVG(m.annualized_vol_30d)" not in SQL_SYSTEM_PROMPT


def test_prompt_routes_general_concepts_without_sql_or_investment_advice():
    assert 'intent="concept_question"' in SQL_SYSTEM_PROMPT
    assert "양의 상관관계가 뭐야?" in SQL_SYSTEM_PROMPT
    assert "Why do bond prices generally fall" in SQL_SYSTEM_PROMPT
    assert 'Set sql=""' in SQL_SYSTEM_PROMPT
    assert 'General educational\n  "why" questions' in SQL_SYSTEM_PROMPT
    assert "personal investment advice" in SQL_SYSTEM_PROMPT


def test_long_term_performance_uses_cagr_policy():
    assert "performance windows of 2 years or longer" in SQL_SYSTEM_PROMPT
    assert "365.25 / NULLIF(period_end - period_start, 0)" in SQL_SYSTEM_PROMPT


def test_generic_relationships_default_to_unleveraged_scope():
    assert "generic cross-ETF relationship" in SQL_SYSTEM_PROMPT
    assert "d.leverage = 1" in SQL_SYSTEM_PROMPT
    assert "the current unleveraged ETF subset (leverage = 1)" in SQL_SYSTEM_PROMPT
    assert "including leveraged funds" in SQL_SYSTEM_PROMPT


def test_ten_year_liquidity_and_cagr_examples_lock_the_contract():
    assert "higher average trading volume" in SQL_SYSTEM_PROMPT
    assert "CURRENT_DATE - INTERVAL '10 years'" in SQL_SYSTEM_PROMPT
    assert "HAVING COUNT(period_daily_return) >= 2000" in SQL_SYSTEM_PROMPT
    assert "relationship between 10-year CAGR" in SQL_SYSTEM_PROMPT
    assert "CORR(cagr, period_annualized_volatility)" in SQL_SYSTEM_PROMPT


def test_prompt_uses_canonical_period_metric_contract():
    assert "# Metric Contract" in SQL_SYSTEM_PROMPT
    assert "Recompute returns after filtering the price window" in SQL_SYSTEM_PROMPT
    assert "Reset the running peak at the first in-window price" in SQL_SYSTEM_PROMPT
    assert "Do not use the average of `rolling_vol_30d`" in SQL_SYSTEM_PROMPT
    assert "MIN(adj_close / period_peak - 1) AS period_max_drawdown" in (
        SQL_SYSTEM_PROMPT
    )


def test_every_data_query_few_shot_passes_the_sql_guard():
    queries = []
    for example in FEW_SHOTS.split("Example ")[1:]:
        if "Intent: data_query" not in example:
            continue
        queries.append(example.split("SQL:", 1)[1].split("\n\n", 1)[0].strip())

    assert len(queries) == 10
    for query in queries:
        validate(query)
