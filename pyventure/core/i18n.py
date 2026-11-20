"""Résolution des textes localisés et catalogue d'interface."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LocalizedText = "str | dict[str, str]"


def resolve_text(
    value: Any,
    language: str,
    default_language: str,
    *,
    missing: list[str] | None = None,
    key: str | None = None,
) -> str:
    """Résout un texte localisé avec la chaîne de repli.

    Ordre : langue demandée -> langue par défaut -> première langue disponible.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return str(value)

    if language in value:
        return str(value[language])
    if default_language in value:
        if missing is not None and language != default_language:
            missing.append(key or default_language)
        return str(value[default_language])
    for text in value.values():
        if missing is not None:
            missing.append(key or "<unknown>")
        return str(text)
    return ""


def normalize(text: str) -> str:
    """Normalise une saisie : minuscules, sans accents, espaces réduits."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(stripped.split())


@dataclass
class Translator:
    """Traducteur du catalogue d'interface, avec repli entre langues."""

    catalogs: dict[str, dict[str, str]]
    default_language: str = "en"
    missing: list[str] = field(default_factory=list)

    @classmethod
    def from_directory(cls, directory: Path, default_language: str = "en") -> Translator:
        from ruamel.yaml import YAML

        yaml = YAML(typ="safe")
        catalogs: dict[str, dict[str, str]] = {}
        for path in sorted(directory.glob("ui.*.yaml")):
            language = path.stem.split(".", 1)[1]
            data = yaml.load(path) or {}
            catalogs[language] = {str(k): str(v) for k, v in data.items()}
        return cls(catalogs=catalogs, default_language=default_language)

    def available_languages(self) -> list[str]:
        return sorted(self.catalogs)

    def raw(self, key: str, language: str) -> str | None:
        catalog = self.catalogs.get(language)
        if catalog and key in catalog:
            return catalog[key]
        default = self.catalogs.get(self.default_language)
        if default and key in default:
            self.missing.append(f"{language}:{key}")
            return default[key]
        for catalog in self.catalogs.values():
            if key in catalog:
                self.missing.append(f"{language}:{key}")
                return catalog[key]
        return None

    def t(self, key: str, language: str | None = None, **params: object) -> str:
        """Traduit une clé et applique les placeholders ``{nom}``."""
        language = language or self.default_language
        template = self.raw(key, language)
        if template is None:
            self.missing.append(f"{language}:{key}")
            return key
        try:
            return template.format(**params)
        except (KeyError, IndexError):
            return template
