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
    assert tr("home.subtitle", "ko").startswith("17개 ETF의 과거 가격")
    assert tr("ask.truncated", "en", rows=200).startswith("Only 200 rows")


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


def test_korean_ticker_explanations_cover_the_configured_universe():
    seed = pd.read_csv("dbt/seeds/etf_info.csv")
    assert set(TICKER_DESCRIPTIONS_KO) == set(seed["ticker"])
