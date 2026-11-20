"""Parseur de commandes en langage naturel restreint."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import ParseError
from .i18n import normalize
from .model import GameObject, GameProject
from .state import INVENTORY, GameState

ARTICLES: dict[str, set[str]] = {
    "fr": {"le", "la", "les", "l", "un", "une", "des", "du", "de", "d"},
    "en": {"the", "a", "an"},
}

BUILTIN_VERBS = {
    "look",
    "inventory",
    "get",
    "drop",
    "examine",
    "use",
    "push",
    "go",
    "wait",
    "help",
    "quit",
    "score",
    "undo",
    "language",
    "save",
    "load",
}

CANONICAL_DIRECTIONS = {"n", "s", "e", "w", "u", "d", "in", "out"}


@dataclass(frozen=True)
class Command:
    """Commande interprétée, avec identifiants d'objets résolus."""

    verb: str
    direct: str | None = None
    indirect: str | None = None
    preposition: str | None = None
    raw: str = ""


class Parser:
    """Traduit une saisie texte en ``Command``."""

    def __init__(self, project: GameProject, language: str, state: GameState) -> None:
        self.project = project
        self.language = language
        self.state = state
        default = project.meta.default_language
        self.verbs = project.vocabulary.verbs_for(language, default)
        self.directions = project.vocabulary.directions_for(language, default)
        self.prepositions = project.vocabulary.prepositions_for(language, default)
        self.articles = ARTICLES.get(language, set()) | ARTICLES.get(default, set())

    # -- API ------------------------------------------------------------
    def parse(self, text: str) -> Command:
        normalized = normalize(text)
        if not normalized:
            raise ParseError("parser.empty")
        tokens = normalized.split()

        verb, consumed = self._match_verb(tokens)
        remaining = tokens[consumed:]

        if verb == "go":
            return self._parse_go(remaining, raw=text)

        direct_tokens, preposition, indirect_tokens = self._split_preposition(remaining)
        direct = self._resolve_object(direct_tokens) if direct_tokens else None
        indirect = self._resolve_object(indirect_tokens) if indirect_tokens else None
        return Command(
            verb=verb,
            direct=direct,
            indirect=indirect,
            preposition=preposition,
            raw=text,
        )

    # -- Interne --------------------------------------------------------
    def _match_verb(self, tokens: list[str]) -> tuple[str, int]:
        if self._is_direction(tokens[0]):
            return "go", 0
        if len(tokens) >= 2:
            two = f"{tokens[0]} {tokens[1]}"
            if two in self.verbs:
                return self.verbs[two], 2
        if tokens[0] in self.verbs:
            return self.verbs[tokens[0]], 1
        raise ParseError("command.unknown_verb", verb=tokens[0])

    def _is_direction(self, token: str) -> bool:
        return token in self.directions or token in CANONICAL_DIRECTIONS

    def _direction_code(self, token: str) -> str | None:
        if token in self.directions:
            return self.directions[token]
        if token in CANONICAL_DIRECTIONS:
            return token
        return None

    def _parse_go(self, tokens: list[str], raw: str) -> Command:
        if not tokens:
            raise ParseError("parser.go_where")
        code = self._direction_code(tokens[0])
        if code is None:
            raise ParseError("parser.go_where")
        return Command(verb="go", direct=code, raw=raw)

    def _split_preposition(self, tokens: list[str]) -> tuple[list[str], str | None, list[str]]:
        for index, token in enumerate(tokens):
            if token in self.prepositions:
                return (
                    self._strip_articles(tokens[:index]),
                    self.prepositions[token],
                    self._strip_articles(tokens[index + 1 :]),
                )
        return self._strip_articles(tokens), None, []

    def _strip_articles(self, tokens: list[str]) -> list[str]:
        return [token for token in tokens if token not in self.articles]

    def _scope(self) -> list[GameObject]:
        in_scope: list[GameObject] = []
        for object_id, game_object in self.project.objects.items():
            location = self.state.location_of(object_id)
            if location == INVENTORY or location == self.state.room:
                in_scope.append(game_object)
        return in_scope

    def _keywords(self, game_object: GameObject) -> set[str]:
        words: set[str] = set()
        default = self.project.meta.default_language
        for language in (self.language, default):
            name = game_object.name
            if isinstance(name, dict):
                text = name.get(language) or name.get(default) or ""
            else:
                text = str(name)
            words.update(normalize(text).split())
            for synonym in game_object.synonyms.get(language, ()):
                words.update(normalize(synonym).split())
        return words

    def _resolve_object(self, tokens: list[str]) -> str | None:
        if not tokens:
            return None
        phrase = " ".join(tokens)
        candidates: list[tuple[int, str]] = []
        for game_object in self._scope():
            keywords = self._keywords(game_object)
            if all(token in keywords for token in tokens):
                candidates.append((len(tokens), game_object.id))
        if not candidates:
            return None
        best = max(score for score, _ in candidates)
        winners = [object_id for score, object_id in candidates if score == best]
        if len(winners) > 1:
            raise ParseError("command.ambiguous", name=phrase)
        return winners[0]


def parse(project: GameProject, state: GameState, text: str) -> Command:
    """Raccourci : crée un parseur et interprète ``text``."""
    return Parser(project, state.language, state).parse(text)
