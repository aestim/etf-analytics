"""The dashboard has one complete English-first interface language contract."""

import pandas as pd

from i18n import (
    COPY,
    DEFAULT_LANGUAGE,
    LANGUAGE_OPTIONS,
    TICKER_DESCRIPTIONS_KO,
    tr,
)


def test_english_is_the_default_interface_language():
    assert DEFAULT_LANGUAGE == "en"
    assert next(iter(LANGUAGE_OPTIONS.items())) == ("English", "en")


def test_every_interface_key_has_both_languages():
    assert COPY
    assert all(set(messages) == {"en", "ko"} for messages in COPY.values())
    assert all(messages["en"].strip() for messages in COPY.values())
    assert all(messages["ko"].strip() for messages in COPY.values())


def test_translation_lookup_keeps_each_interface_language_separate():
    assert tr("home.subtitle", "en").startswith("Compare historical prices")
    assert tr("home.subtitle", "ko").startswith("기본 ETF와 현재 세션")
    assert tr("ask.truncated", "en", rows=200).startswith("Only 200 rows")


def test_infinite_buying_strategy_is_not_labeled_as_generic_split_buying():
    assert tr("strategy.split_short", "ko") == "무한매수법 · TQQQ"
    assert tr("strategy.split_short", "en") == "Infinite Buying · TQQQ"


def test_interface_copy_avoids_internal_or_translation_heavy_phrases():
    all_messages = "\n".join(
        message for translations in COPY.values() for message in translations.values()
    )

    assert "Ask the data" not in all_messages
    assert "fallback model" not in all_messages
    assert "warehouse schema" not in all_messages
    assert "결과 모양" not in all_messages
    assert tr("ask.title", "en") == "💬 Ask About ETFs"
    assert tr("ask.title", "ko") == "💬 ETF 정보 물어보기"


def test_ask_copy_advertises_concepts_without_promising_investment_advice():
    assert "positive correlation" in tr("ask.examples", "en")
    assert "양의 상관관계" in tr("ask.examples", "ko")
    # Both disclaimers survive rewording: no forecast, no advice.
    assert "forecast" in tr("ask.subtitle", "en")
    assert "investment advice" in tr("ask.subtitle", "en")
    assert "예측" in tr("ask.subtitle", "ko")
    assert "투자 조언" in tr("ask.subtitle", "ko")
    assert "AI key" in tr("ask.unavailable", "en")
    assert "AI 키" in tr("ask.unavailable", "ko")


def test_ask_intro_does_not_narrate_what_the_page_already_shows():
    """The sidebar has a language toggle and answers follow the question's
    language, so saying so in prose only lengthened the page."""
    for lang in ("en", "ko"):
        assert "Korean" not in tr("ask.subtitle", lang)
        assert "한국어" not in tr("ask.subtitle", lang)
    # One short line, not a paragraph, above the input.
    assert len(tr("ask.subtitle", "en")) < 140
    assert len(tr("ask.subtitle", "ko")) < 100


def test_korean_ticker_explanations_cover_the_configured_universe():
    seed = pd.read_csv("dbt/seeds/etf_info.csv")
    assert set(TICKER_DESCRIPTIONS_KO) == set(seed["ticker"])
