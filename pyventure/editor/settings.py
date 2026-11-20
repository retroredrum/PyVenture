"""Préférences de l'éditeur : projets récents, stockées en JSON."""

from __future__ import annotations

import json
import os
from pathlib import Path

MAX_RECENT = 10


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "pyventure"


def config_file() -> Path:
    return config_dir() / "editor.json"


def load_settings() -> dict:
    path = config_file()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_settings(data: dict) -> None:
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    config_file().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def recent_projects() -> list[str]:
    recent = load_settings().get("recent", [])
    if not isinstance(recent, list):
        return []
    return [str(item) for item in recent]


def remember_project(path: Path | str) -> list[str]:
    """Ajoute un projet en tête des récents (dédoublonné, limité)."""
    entry = str(path)
    recent = [item for item in recent_projects() if item != entry]
    recent.insert(0, entry)
    recent = recent[:MAX_RECENT]
    data = load_settings()
    data["recent"] = recent
    save_settings(data)
    return recent
