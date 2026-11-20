"""Exceptions du moteur PyVenture."""

from __future__ import annotations


class PyVentureError(Exception):
    """Erreur de base du moteur."""


class ProjectError(PyVentureError):
    """Erreur de chargement ou de validation d'un projet."""


class SchemaError(ProjectError):
    """Le fichier ne respecte pas le schéma JSON."""


class ValidationError(ProjectError):
    """Références cassées ou incohérences sémantiques."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("\n".join(problems))


class ParseError(PyVentureError):
    """La saisie du joueur n'a pas pu être interprétée."""

    def __init__(self, key: str, **params: object) -> None:
        self.key = key
        self.params = params
        super().__init__(key)


class SaveError(PyVentureError):
    """Erreur de sauvegarde ou de chargement d'une partie."""
