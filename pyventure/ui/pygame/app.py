"""Point d'entrée de la fenêtre pygame."""

from __future__ import annotations

from pathlib import Path

from ...core.loader import load_project
from .game import DEFAULT_SIZE, GameApp


def run(
    project_path: Path,
    *,
    language: str | None = None,
    save_path: Path | None = None,
    size: tuple[int, int] = DEFAULT_SIZE,
    resume: bool = True,
    autosave: bool = True,
) -> int:
    project = load_project(project_path)
    app = GameApp(
        project,
        language=language,
        save_path=save_path,
        size=size,
        resume=resume,
        autosave=autosave,
    )
    return app.run()
