"""Tests des préférences de l'éditeur (projets récents)."""

from __future__ import annotations

from pathlib import Path

from pyventure.editor import settings


def test_recent_projects_round_trip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert settings.recent_projects() == []
    settings.remember_project("/a/game.yaml")
    settings.remember_project("/b/game.yaml")
    assert settings.recent_projects() == ["/b/game.yaml", "/a/game.yaml"]


def test_recent_dedupes_and_limits(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    for index in range(settings.MAX_RECENT + 5):
        settings.remember_project(f"/p{index}/game.yaml")
    recent = settings.recent_projects()
    assert len(recent) == settings.MAX_RECENT
    assert recent[0] == f"/p{settings.MAX_RECENT + 4}/game.yaml"

    settings.remember_project("/p10/game.yaml")
    recent = settings.recent_projects()
    assert recent[0] == "/p10/game.yaml"
    assert len(recent) == len(set(recent))


def test_load_settings_handles_corrupt_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = settings.config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ pas du json", encoding="utf-8")
    assert settings.load_settings() == {}
    assert settings.recent_projects() == []
