"""Types de sortie du moteur, indépendants de toute interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Style(StrEnum):
    """Style sémantique d'une ligne de sortie."""

    NORMAL = "normal"
    ROOM_TITLE = "room_title"
    DESCRIPTION = "description"
    EXIT = "exit"
    ITEM = "item"
    ERROR = "error"
    SUCCESS = "success"
    SYSTEM = "system"
    DIALOGUE = "dialogue"


@dataclass(frozen=True)
class OutputLine:
    """Une ligne de texte produite par le moteur."""

    text: str
    style: Style = Style.NORMAL

    def __str__(self) -> str:  # pragma: no cover - confort de debug
        return self.text


@dataclass(frozen=True)
class ArtHint:
    """Indication d'illustration à afficher, résolue par le renderer."""

    room: str | None = None
    variant: str | None = None
    object_id: str | None = None
    ending: str | None = None


@dataclass
class TurnResult:
    """Résultat complet d'un tour de jeu."""

    lines: list[OutputLine] = field(default_factory=list)
    art: ArtHint | None = None
    sound: str | None = None
    ended: str | None = None
    quit: bool = False

    def text(self) -> str:
        """Concatène les lignes en texte brut (utile pour les tests)."""
        return "\n".join(line.text for line in self.lines)
