"""Tests « golden » : transcripts de référence.

Deux familles :

- le nouveau moteur, sur le projet d'exemple, en FR et EN ;
- le moteur historique, capturé dans un sous-processus.

Régénérer les transcripts du nouveau moteur :

    UPDATE_GOLDEN=1 pytest tests/golden -q
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from pyventure.core.engine import Engine
from pyventure.core.loader import load_project
from pyventure.core.state import GameState

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = Path(__file__).resolve().parent
MINI_GAME = ROOT / "examples" / "mini-game" / "game.yaml"
ANSI = re.compile(r"\x1b\[[0-9;]*m")

FR_SESSION = [
    "regarder",
    "prendre lampe",
    "nord",
    "nord",
    "est",
    "utiliser lampe",
    "examiner lampe",
    "est",
    "prendre cle",
    "utiliser cle",
]

EN_SESSION = [
    "look",
    "take flashlight",
    "n",
    "n",
    "e",
    "use flashlight",
    "examine flashlight",
    "e",
    "take key",
    "use key",
]

LEGACY_SESSION = ["look", "push statue", "d", "look", "quit"]


def normalize(text: str) -> str:
    text = ANSI.sub("", text)
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip() + "\n"


def run_new_engine(language: str, commands: list[str]) -> str:
    project = load_project(MINI_GAME)
    engine = Engine(project)
    state: GameState = engine.new_state(language)
    chunks = [engine.start(state).text()]
    for command in commands:
        chunks.append(f"> {command}")
        chunks.append(engine.execute(command, state).text())
    return normalize("\n".join(chunks))


def check_golden(name: str, actual: str) -> None:
    path = GOLDEN_DIR / name
    if os.environ.get("UPDATE_GOLDEN") == "1" or not path.is_file():
        path.write_text(actual, encoding="utf-8")
        pytest.skip(f"transcript régénéré : {path}")
    expected = path.read_text(encoding="utf-8")
    assert actual == expected, f"transcript différent de {path}"


@pytest.mark.parametrize(
    ("name", "language", "session"),
    [
        ("mini_game_fr.txt", "fr", FR_SESSION),
        ("mini_game_en.txt", "en", EN_SESSION),
    ],
)
def test_new_engine_golden(name: str, language: str, session: list[str]) -> None:
    check_golden(name, run_new_engine(language, session))


def test_legacy_engine_golden() -> None:
    completed = subprocess.run(
        [sys.executable, "start.py"],
        cwd=ROOT,
        input="\n".join(LEGACY_SESSION) + "\n",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0
    check_golden("legacy_session.txt", normalize(completed.stdout + completed.stderr))
