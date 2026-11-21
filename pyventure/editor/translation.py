"""Workflow de traduction : inventaire des textes, couverture, CSV, pseudo-locale.

Cette couche ne dépend pas de Tkinter.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from typing import Any

PLACEHOLDER = re.compile(r"\{(\w+)\}")

_PSEUDO_TABLE = str.maketrans("aeioultsAEIOULTS", "àéîôùlţšÀÉÎÔÙLŢŠ")


@dataclass(frozen=True)
class TranslationEntry:
    """Un texte localisé du contenu."""

    key: str
    kind: str
    path: tuple[str, ...]
    raw: Any
    is_list: bool = False

    def text_for(self, language: str) -> str:
        if isinstance(self.raw, str):
            return self.raw
        if isinstance(self.raw, dict):
            value = self.raw.get(language)
            if isinstance(value, list):
                return ", ".join(str(item) for item in value)
            return str(value) if value is not None else ""
        return ""

    def has(self, language: str) -> bool:
        if isinstance(self.raw, str):
            return True
        if isinstance(self.raw, dict):
            return language in self.raw
        return False

    def missing(self, languages: list[str]) -> list[str]:
        return [language for language in languages if not self.has(language)]

    def source_language(self, languages: list[str], default: str) -> str:
        if isinstance(self.raw, dict):
            for language in [default, *languages]:
                if language in self.raw:
                    return language
        return default

    def source_text(self, languages: list[str], default: str) -> str:
        return self.text_for(self.source_language(languages, default))


def _localized(value: Any) -> bool:
    if isinstance(value, str):
        return True
    if isinstance(value, dict):
        return all(isinstance(item, (str, list)) for item in value.values())
    return False


def collect_entries(data: dict[str, Any]) -> list[TranslationEntry]:
    """Liste tous les textes localisés du contenu."""
    entries: list[TranslationEntry] = []

    def add(key: str, kind: str, path: tuple[str, ...], value: Any, is_list: bool = False) -> None:
        if value is None:
            return
        entries.append(TranslationEntry(key, kind, path, value, is_list))

    meta = data.get("meta")
    if isinstance(meta, dict):
        for field in ("title", "description"):
            if _localized(meta.get(field)):
                add(f"meta.{field}", f"meta.{field}", ("meta", field), meta[field])

    rooms = data.get("rooms")
    if isinstance(rooms, dict):
        for room_id, room in rooms.items():
            if not isinstance(room, dict):
                continue
            for field in ("name", "description"):
                if _localized(room.get(field)):
                    add(
                        f"rooms.{room_id}.{field}",
                        f"room.{field}",
                        ("rooms", room_id, field),
                        room[field],
                    )
            variants = room.get("variants")
            if isinstance(variants, dict):
                for name, variant in variants.items():
                    if not isinstance(variant, dict):
                        continue
                    for field in ("name", "description"):
                        if _localized(variant.get(field)):
                            add(
                                f"rooms.{room_id}.variants.{name}.{field}",
                                f"variant.{field}",
                                ("rooms", room_id, "variants", name, field),
                                variant[field],
                            )

    objects = data.get("objects")
    if isinstance(objects, dict):
        for object_id, game_object in objects.items():
            if not isinstance(game_object, dict):
                continue
            for field in ("name", "description"):
                if _localized(game_object.get(field)):
                    add(
                        f"objects.{object_id}.{field}",
                        f"object.{field}",
                        ("objects", object_id, field),
                        game_object[field],
                    )
            synonyms = game_object.get("synonyms")
            if isinstance(synonyms, dict) and synonyms:
                add(
                    f"objects.{object_id}.synonyms",
                    "object.synonyms",
                    ("objects", object_id, "synonyms"),
                    synonyms,
                    is_list=True,
                )
            states = game_object.get("states")
            if isinstance(states, dict):
                for name, state in states.items():
                    if not isinstance(state, dict):
                        continue
                    for field in ("name", "description"):
                        if _localized(state.get(field)):
                            add(
                                f"objects.{object_id}.states.{name}.{field}",
                                f"state.{field}",
                                ("objects", object_id, "states", name, field),
                                state[field],
                            )

    messages = data.get("messages")
    if isinstance(messages, dict):
        for key, value in messages.items():
            if _localized(value):
                add(f"messages.{key}", "message", ("messages", key), value)

    endings = data.get("endings")
    if isinstance(endings, dict):
        for ending_id, ending in endings.items():
            if not isinstance(ending, dict):
                continue
            for field in ("title", "text"):
                if _localized(ending.get(field)):
                    add(
                        f"endings.{ending_id}.{field}",
                        f"ending.{field}",
                        ("endings", ending_id, field),
                        ending[field],
                    )

    return entries


def coverage(entries: list[TranslationEntry], languages: list[str]) -> dict[str, dict[str, int]]:
    """Nombre de textes traduits par langue."""
    result: dict[str, dict[str, int]] = {}
    total = len(entries)
    for language in languages:
        done = sum(1 for entry in entries if entry.has(language))
        result[language] = {
            "translated": done,
            "total": total,
            "percent": round(100 * done / total) if total else 100,
        }
    return result


def placeholders(text: str) -> set[str]:
    return set(PLACEHOLDER.findall(text))


def placeholder_problems(
    entries: list[TranslationEntry], languages: list[str], default: str
) -> list[str]:
    problems: list[str] = []
    for entry in entries:
        expected = placeholders(entry.source_text(languages, default))
        for language in languages:
            if not entry.has(language):
                continue
            found = placeholders(entry.text_for(language))
            if found != expected:
                problems.append(
                    f"{entry.key} [{language}] : placeholders {sorted(found)} "
                    f"au lieu de {sorted(expected)}"
                )
    return problems


def missing_problems(entries: list[TranslationEntry], languages: list[str]) -> list[str]:
    problems: list[str] = []
    for entry in entries:
        for language in entry.missing(languages):
            problems.append(f"{entry.key} : traduction manquante ({language})")
    return problems


def pseudo_locale(text: str) -> str:
    """Transforme un texte pour tester les débordements (accents + allongement)."""
    if not text:
        return ""
    return f"[{text.translate(_PSEUDO_TABLE)}···]"


def _resolve(data: Any, path: tuple[str, ...]) -> tuple[Any, str]:
    container = data
    for step in path[:-1]:
        container = container[step]
    return container, path[-1]


def set_translation(
    data: dict[str, Any],
    path: tuple[str, ...],
    language: str,
    value: str,
    *,
    is_list: bool = False,
    default_language: str = "en",
) -> None:
    """Écrit une traduction, en convertissant un texte simple en objet multilingue."""
    container, key = _resolve(data, path)
    current = container.get(key)
    if isinstance(current, str):
        current = {default_language: current}
        container[key] = current
    if not isinstance(current, dict):
        current = {}
        container[key] = current
    if is_list:
        items = [item.strip() for item in value.split(",") if item.strip()]
        if items:
            current[language] = items
        else:
            current.pop(language, None)
        return
    if value:
        current[language] = value
    else:
        current.pop(language, None)


CSV_HEADER = ["key", "kind", "source"]


def to_csv(entries: list[TranslationEntry], languages: list[str], default: str) -> str:
    """Sérialise les textes en CSV (clé, type, source, puis une colonne par langue)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([*CSV_HEADER, *languages])
    for entry in entries:
        row = [entry.key, entry.kind, entry.source_text(languages, default)]
        row.extend(entry.text_for(language) for language in languages)
        writer.writerow(row)
    return buffer.getvalue()


def from_csv(text: str, languages: list[str]) -> dict[str, dict[str, str]]:
    """Lit un CSV et renvoie {clé: {langue: valeur}} pour les valeurs non vides."""
    reader = csv.DictReader(io.StringIO(text))
    updates: dict[str, dict[str, str]] = {}
    for row in reader:
        key = (row.get("key") or "").strip()
        if not key:
            continue
        values: dict[str, str] = {}
        for language in languages:
            if language in row:
                value = row.get(language) or ""
                if value.strip():
                    values[language] = value
        if values:
            updates[key] = values
    return updates


def apply_csv(
    data: dict[str, Any],
    entries: list[TranslationEntry],
    updates: dict[str, dict[str, str]],
    default_language: str = "en",
) -> int:
    """Applique des traductions issues d'un CSV. Renvoie le nombre de clés appliquées."""
    by_key = {entry.key: entry for entry in entries}
    applied = 0
    for key, values in updates.items():
        entry = by_key.get(key)
        if entry is None:
            continue
        for language, value in values.items():
            set_translation(
                data,
                entry.path,
                language,
                value,
                is_list=entry.is_list,
                default_language=default_language,
            )
        applied += 1
    return applied
