"""Sauvegarde et chargement d'une partie au format JSON versionné."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from .errors import SaveError
from .model import GameProject
from .state import GameState

FORMAT = "pyventure-save"
FORMAT_VERSION = 1


def default_save_path(project: GameProject) -> Path:
    """Chemin de sauvegarde par défaut, dans le dossier de données utilisateur."""
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "pyventure" / f"{project.meta.id}.json"


def state_to_payload(project: GameProject, state: GameState) -> dict:
    return {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "project": {"id": project.meta.id, "version": project.meta.version},
        "saved_at": datetime.now(UTC).isoformat(),
        "language": state.language,
        "state": state.to_dict(),
    }


def save_state(project: GameProject, state: GameState, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(
            json.dumps(state_to_payload(project, state), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise SaveError(f"impossible d'écrire {path} : {exc}") from exc
    return path


def load_state(project: GameProject, path: Path) -> GameState:
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SaveError(f"impossible de lire {path} : {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SaveError(f"sauvegarde illisible : {exc}") from exc

    if payload.get("format") != FORMAT:
        raise SaveError("ce fichier n'est pas une sauvegarde PyVenture")
    if payload.get("format_version") != FORMAT_VERSION:
        raise SaveError(
            f"version de sauvegarde non prise en charge : {payload.get('format_version')}"
        )
    project_info = payload.get("project", {})
    if project_info.get("id") != project.meta.id:
        raise SaveError(
            f"cette sauvegarde appartient au projet « {project_info.get('id')} », "
            f"pas à « {project.meta.id} »"
        )
    return GameState.from_dict(payload["state"])
