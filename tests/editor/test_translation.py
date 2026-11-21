"""Tests du workflow de traduction (sans Tkinter)."""

from __future__ import annotations

from pathlib import Path

from pyventure.editor import translation
from pyventure.editor.document import ProjectDocument


def _entries(example_path: Path) -> list[translation.TranslationEntry]:
    document = ProjectDocument.load(example_path)
    return translation.collect_entries(document.data)


def test_collect_entries_finds_every_kind(example_path: Path) -> None:
    keys = {entry.key for entry in _entries(example_path)}
    assert "meta.title" in keys
    assert "rooms.bedroom.name" in keys
    assert "rooms.cave.variants.lit.description" in keys
    assert "objects.flashlight.name" in keys
    assert "objects.flashlight.synonyms" in keys
    assert "messages.flashlight_on" in keys
    assert "endings.escaped.text" in keys


def test_coverage_is_complete_on_example(example_path: Path) -> None:
    report = translation.coverage(_entries(example_path), ["fr", "en"])
    assert report["fr"]["percent"] == 100
    assert report["en"]["percent"] == 100


def test_missing_detection(example_path: Path) -> None:
    document = ProjectDocument.load(example_path)
    document.data["rooms"]["bedroom"]["description"] = {"fr": "seulement en français"}
    entries = translation.collect_entries(document.data)
    entry = next(item for item in entries if item.key == "rooms.bedroom.description")
    assert entry.missing(["fr", "en"]) == ["en"]
    assert entry.text_for("fr") == "seulement en français"
    assert entry.text_for("en") == ""


def test_plain_string_counts_as_translated() -> None:
    entry = translation.TranslationEntry("k", "t", ("k",), "shared")
    assert entry.has("fr") and entry.has("en")
    assert entry.missing(["fr", "en"]) == []


def test_set_translation_converts_plain_string() -> None:
    data = {"meta": {"title": "Demo"}}
    translation.set_translation(data, ("meta", "title"), "fr", "Démo")
    assert data["meta"]["title"] == {"en": "Demo", "fr": "Démo"}


def test_set_translation_removes_empty_value() -> None:
    data = {"meta": {"title": {"fr": "a", "en": "b"}}}
    translation.set_translation(data, ("meta", "title"), "en", "")
    assert "en" not in data["meta"]["title"]


def test_set_translation_list() -> None:
    data = {"objects": {"x": {"synonyms": {"fr": ["a"]}}}}
    translation.set_translation(data, ("objects", "x", "synonyms"), "en", "b, c", is_list=True)
    assert data["objects"]["x"]["synonyms"]["en"] == ["b", "c"]


def test_placeholder_problems() -> None:
    entries = [
        translation.TranslationEntry("k", "t", ("k",), {"fr": "Bonjour {nom}", "en": "Hello"})
    ]
    problems = translation.placeholder_problems(entries, ["fr", "en"], "fr")
    assert problems
    assert "k" in problems[0]


def test_no_placeholder_problem_when_consistent() -> None:
    entries = [
        translation.TranslationEntry("k", "t", ("k",), {"fr": "Bonjour {nom}", "en": "Hello {nom}"})
    ]
    assert translation.placeholder_problems(entries, ["fr", "en"], "fr") == []


def test_missing_problems() -> None:
    entries = [translation.TranslationEntry("k", "t", ("k",), {"fr": "x"})]
    problems = translation.missing_problems(entries, ["fr", "en"])
    assert problems == ["k : traduction manquante (en)"]


def test_pseudo_locale_expands_and_accents() -> None:
    assert translation.pseudo_locale("") == ""
    output = translation.pseudo_locale("Salut")
    assert output != "Salut"
    assert len(output) > len("Salut")


def test_csv_round_trip(example_path: Path) -> None:
    entries = _entries(example_path)
    text = translation.to_csv(entries, ["fr", "en"], "fr")
    updates = translation.from_csv(text, ["fr", "en"])
    assert updates["rooms.bedroom.name"]["fr"] == "Chambre"
    assert updates["rooms.bedroom.name"]["en"] == "Bedroom"


def test_apply_csv_updates_document(example_path: Path) -> None:
    document = ProjectDocument.load(example_path)
    entries = translation.collect_entries(document.data)
    updates = {"rooms.bedroom.name": {"en": "The Bedroom"}}
    applied = translation.apply_csv(document.data, entries, updates, "fr")
    assert applied == 1
    assert document.section("rooms")["bedroom"]["name"]["en"] == "The Bedroom"


def test_apply_csv_ignores_unknown_keys(example_path: Path) -> None:
    document = ProjectDocument.load(example_path)
    entries = translation.collect_entries(document.data)
    applied = translation.apply_csv(document.data, entries, {"unknown.key": {"en": "x"}}, "fr")
    assert applied == 0
