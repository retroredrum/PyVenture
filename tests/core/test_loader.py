"""Tests du chargement et de la validation."""

from __future__ import annotations

import pytest
from pyventure.core.errors import ProjectError, ValidationError
from pyventure.core.loader import load_project, project_from_data, read_yaml
from pyventure.core.model import GameProject
from pyventure.core.schema import validate_data, validate_project


def test_load_example(project: GameProject) -> None:
    assert project.meta.id == "mini-game"
    assert project.meta.default_language == "fr"
    assert set(project.rooms) == {"bedroom", "corridor", "cave", "vault"}
    assert project.objects["flashlight"].location == "bedroom"
    assert project.objects["flashlight"].portable is True
    assert len(project.interactions) == 2


def test_read_yaml_rejects_non_mapping(tmp_path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ProjectError):
        read_yaml(path)


def test_schema_reports_errors() -> None:
    data = {
        "format": "pyventure-game",
        "format_version": 1,
        "meta": {"id": "x", "title": "X", "start_room": "a", "default_language": "fr"},
        "languages": ["fr"],
        "rooms": {"a": {"name": "A"}},  # description manquante
    }
    problems = validate_data(data)
    assert problems


def test_semantic_validation_catches_unknown_exit(project: GameProject) -> None:
    data = read_yaml(project.root / "game.yaml")
    data["rooms"]["bedroom"]["exits"]["north"] = "does-not-exist"
    broken = project_from_data(data, project.root)
    problems = validate_project(broken)
    assert any("does-not-exist" in problem for problem in problems)


def test_strict_i18n_flags_missing_translation(project: GameProject) -> None:
    data = read_yaml(project.root / "game.yaml")
    data["rooms"]["bedroom"]["description"] = {"fr": "seulement en français"}
    broken = project_from_data(data, project.root)
    assert validate_project(broken) == []
    problems = validate_project(broken, strict_i18n=True)
    assert any("traduction manquante (en)" in problem for problem in problems)


def test_validation_error_raises(tmp_path, example_path) -> None:
    from ruamel.yaml import YAML

    data = read_yaml(example_path)
    data["meta"]["start_room"] = "ghost"
    path = tmp_path / "game.yaml"
    with path.open("w", encoding="utf-8") as handle:
        YAML().dump(data, handle)
    with pytest.raises(ValidationError):
        load_project(path)
