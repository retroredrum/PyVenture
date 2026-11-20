"""Tests de l'i18n et du repli de traduction."""

from __future__ import annotations

from pyventure.core.i18n import Translator, normalize, resolve_text


def test_resolve_plain_string() -> None:
    assert resolve_text("hello", "fr", "fr") == "hello"


def test_resolve_language() -> None:
    value = {"fr": "bonjour", "en": "hello"}
    assert resolve_text(value, "en", "fr") == "hello"


def test_resolve_fallback_to_default() -> None:
    value = {"fr": "bonjour"}
    missing: list[str] = []
    assert resolve_text(value, "en", "fr", missing=missing, key="greeting") == "bonjour"
    assert missing == ["greeting"]


def test_resolve_fallback_to_first() -> None:
    value = {"de": "hallo"}
    assert resolve_text(value, "en", "fr") == "hallo"


def test_normalize_accents_and_case() -> None:
    assert normalize("  Clé   EN Fer ") == "cle en fer"


def test_translator_formats_placeholders() -> None:
    translator = Translator({"fr": {"greet": "Bonjour {name}."}}, default_language="fr")
    assert translator.t("greet", "fr", name="Zork") == "Bonjour Zork."


def test_translator_fallback_records_missing() -> None:
    translator = Translator({"en": {"only": "Only"}}, default_language="en")
    assert translator.t("only", "fr") == "Only"
    assert "fr:only" in translator.missing


def test_translator_unknown_key_returns_key() -> None:
    translator = Translator({"en": {}}, default_language="en")
    assert translator.t("nope", "en") == "nope"
