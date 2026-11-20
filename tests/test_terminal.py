"""Tests du terminal : autosave et reprise."""

from __future__ import annotations

from pyventure.core.model import GameProject
from pyventure.ui.terminal.app import TerminalApp


def test_autosave_written_after_turn(project: GameProject, tmp_path) -> None:
    app = TerminalApp(project, save_path=tmp_path / "save.json", color=False)
    app._handle("prendre lampe")
    assert app.autosave_path.is_file()


def test_resume_from_autosave(project: GameProject, tmp_path) -> None:
    save = tmp_path / "save.json"
    first = TerminalApp(project, save_path=save, color=False)
    first._handle("prendre lampe")

    second = TerminalApp(project, save_path=save, color=False)
    assert second.resumed is True
    assert second.state.carries("flashlight")


def test_fresh_ignores_autosave(project: GameProject, tmp_path) -> None:
    save = tmp_path / "save.json"
    first = TerminalApp(project, save_path=save, color=False)
    first._handle("prendre lampe")

    fresh = TerminalApp(project, save_path=save, color=False, resume=False)
    assert fresh.resumed is False
    assert not fresh.state.carries("flashlight")


def test_autosave_disabled(project: GameProject, tmp_path) -> None:
    app = TerminalApp(project, save_path=tmp_path / "save.json", color=False, autosave=False)
    app._handle("prendre lampe")
    assert not app.autosave_path.is_file()
