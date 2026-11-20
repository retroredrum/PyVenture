"""Modèle de données immuable du contenu d'un jeu."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LocalizedText = str | dict[str, str]


@dataclass(frozen=True)
class Meta:
    id: str
    title: LocalizedText
    start_room: str
    default_language: str
    version: str = "0.0.0"
    max_score: int = 0
    authors: tuple[str, ...] = ()
    description: LocalizedText | None = None
    art_width: int = 320
    art_height: int = 180
    art_scale: int = 3


@dataclass(frozen=True)
class Condition:
    """Condition déclarative : ``kind`` + arguments."""

    kind: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Effect:
    """Effet déclaratif : ``kind`` + arguments."""

    kind: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Exit:
    room: str
    when: tuple[Condition, ...] = ()
    locked_message: LocalizedText | None = None
    hidden: bool = False


@dataclass(frozen=True)
class RoomVariant:
    description: LocalizedText
    art: str | None = None
    name: LocalizedText | None = None


@dataclass(frozen=True)
class Room:
    id: str
    name: LocalizedText
    description: LocalizedText
    art: str | None = None
    exits: dict[str, Exit] = field(default_factory=dict)
    variants: dict[str, RoomVariant] = field(default_factory=dict)
    on_enter: tuple[Effect, ...] = ()
    comment: str | None = None


@dataclass(frozen=True)
class ObjectState:
    description: LocalizedText | None = None
    art: str | None = None
    name: LocalizedText | None = None


@dataclass(frozen=True)
class GameObject:
    id: str
    name: LocalizedText
    description: LocalizedText
    synonyms: dict[str, tuple[str, ...]] = field(default_factory=dict)
    location: str | None = None
    portable: bool = True
    art: str | None = None
    states: dict[str, ObjectState] = field(default_factory=dict)
    initial_state: str | None = None
    comment: str | None = None


@dataclass(frozen=True)
class Interaction:
    id: str
    verbs: tuple[str, ...]
    effects: tuple[Effect, ...]
    objects: tuple[str, ...] = ()
    indirect_objects: tuple[str, ...] = ()
    prepositions: tuple[str, ...] = ()
    when: tuple[Condition, ...] = ()
    once: bool = False
    priority: int = 0
    comment: str | None = None


@dataclass(frozen=True)
class Ending:
    id: str
    title: LocalizedText
    text: LocalizedText
    art: str | None = None


@dataclass(frozen=True)
class Vocabulary:
    """Vocabulaire du parseur, par langue."""

    verbs: dict[str, dict[str, str]] = field(default_factory=dict)
    directions: dict[str, dict[str, str]] = field(default_factory=dict)
    prepositions: dict[str, dict[str, str]] = field(default_factory=dict)

    def verbs_for(self, language: str, default_language: str) -> dict[str, str]:
        merged = dict(self.verbs.get(default_language, {}))
        merged.update(self.verbs.get(language, {}))
        return merged

    def directions_for(self, language: str, default_language: str) -> dict[str, str]:
        merged = dict(self.directions.get(default_language, {}))
        merged.update(self.directions.get(language, {}))
        return merged

    def prepositions_for(self, language: str, default_language: str) -> dict[str, str]:
        merged = dict(self.prepositions.get(default_language, {}))
        merged.update(self.prepositions.get(language, {}))
        return merged


@dataclass(frozen=True)
class GameProject:
    meta: Meta
    languages: tuple[str, ...]
    rooms: dict[str, Room]
    objects: dict[str, GameObject]
    interactions: tuple[Interaction, ...]
    endings: dict[str, Ending]
    vocabulary: Vocabulary
    messages: dict[str, LocalizedText]
    flags: dict[str, bool]
    counters: dict[str, int]
    root: Path

    def text(
        self,
        value: LocalizedText | None,
        language: str,
        *,
        missing: list[str] | None = None,
        key: str | None = None,
    ) -> str:
        from .i18n import resolve_text

        return resolve_text(
            value,
            language,
            self.meta.default_language,
            missing=missing,
            key=key,
        )
