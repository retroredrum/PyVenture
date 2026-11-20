"""Boucle de jeu en terminal."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

from ...core.engine import Engine
from ...core.errors import SaveError
from ...core.events import OutputLine, Style
from ...core.i18n import normalize
from ...core.loader import load_project
from ...core.model import GameProject
from ...core.save import default_save_path, load_state, save_state
from ...core.state import INVENTORY, GameState
from .render import print_result

APP_COMMANDS = {"save", "sauvegarder", "load", "charger", "undo", "annuler"}
LANGUAGE_COMMANDS = {"lang", "language", "langue"}


class TerminalApp:
    """Application terminal autour du moteur."""

    def __init__(
        self,
        project: GameProject,
        *,
        language: str | None = None,
        save_path: Path | None = None,
        color: bool = True,
        resume: bool = True,
        autosave: bool = True,
    ) -> None:
        self.project = project
        self.engine = Engine(project)
        self.state = self.engine.new_state(language)
        self.save_path = save_path or default_save_path(project)
        self.color = color
        self.history: list[GameState] = []
        self.autosave_enabled = autosave
        self.autosave_path = self.save_path.with_name(f"{self.save_path.stem}.autosave.json")
        self.resumed = False
        if resume and autosave:
            self._resume()

    def _resume(self) -> None:
        if not self.autosave_path.is_file():
            return
        try:
            self.state = load_state(self.project, self.autosave_path)
        except SaveError:
            return
        self.resumed = True

    def run(self) -> int:
        print_result(self.engine.start(self.state), color=self.color)
        if self.resumed:
            self._say("game.resumed")
        while True:
            try:
                prompt = self.engine.translator.t("command.prompt", self.state.language)
                raw = input(prompt)
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if self._handle(raw):
                return 0

    # -- Traitement -----------------------------------------------------
    def _handle(self, raw: str) -> bool:
        text = raw.strip()
        if not text:
            return False

        normalized = normalize(text)
        first = normalized.split()[0]

        if first.startswith("/"):
            self._debug(normalized)
            return False
        if first in LANGUAGE_COMMANDS:
            self._set_language(normalized)
            return False
        if first in APP_COMMANDS:
            return self._app_command(first, normalized)

        self.history.append(copy.deepcopy(self.state))
        if len(self.history) > 20:
            self.history.pop(0)

        result = self.engine.execute(text, self.state)
        print_result(result, color=self.color)
        if result.ended:
            self._clear_autosave()
            self._after_ending()
            return True
        self._autosave()
        return result.quit

    def _app_command(self, first: str, normalized: str) -> bool:
        if first in {"save", "sauvegarder"}:
            save_state(self.project, self.state, self.save_path)
            self._say("game.saved")
        elif first in {"load", "charger"}:
            if self.save_path.is_file():
                self.state = load_state(self.project, self.save_path)
                self._say("game.loaded")
            else:
                self._say("game.no_save")
        elif first in {"undo", "annuler"}:
            if self.history:
                self.state = self.history.pop()
                self._say("game.undone")
            else:
                self._say("game.nothing_to_undo")
        return False

    def _set_language(self, normalized: str) -> None:
        parts = normalized.split()
        if len(parts) < 2:
            self._say("game.language_list", languages=", ".join(self.project.languages))
            return
        code = parts[1]
        if code in self.project.languages:
            self.state.language = code
            self._say("game.language_set", code=code)
        else:
            self._say("game.unknown_language", code=code)

    def _debug(self, normalized: str) -> None:
        parts = normalized.split()
        command = parts[0]
        args = parts[1:]
        if command == "/goto" and args and args[0] in self.project.rooms:
            self.state.room = args[0]
            print_result(self.engine.start(self.state), color=self.color)
        elif command == "/give" and args:
            object_id = self._match_object(" ".join(args))
            if object_id:
                self.state.move_object(object_id, INVENTORY)
                self._say("debug.gave", object=object_id)
            else:
                self._say("debug.unknown_object", name=" ".join(args))
        elif command == "/flags":
            for name, value in sorted(self.state.flags.items()):
                print(OutputLine(f"{name} = {value}", Style.SYSTEM).text)
        elif command == "/state":
            for key, value in self.state.to_dict().items():
                print(OutputLine(f"{key} = {value}", Style.SYSTEM).text)
        else:
            self._say("debug.unknown")

    def _match_object(self, phrase: str) -> str | None:
        wanted = normalize(phrase)
        for object_id, game_object in self.project.objects.items():
            names = [normalize(str(game_object.name))]
            if isinstance(game_object.name, dict):
                names = [normalize(text) for text in game_object.name.values()]
            synonyms = [
                normalize(word) for words in game_object.synonyms.values() for word in words
            ]
            if wanted in names or wanted in synonyms or wanted == normalize(object_id):
                return object_id
        return None

    def _after_ending(self) -> None:
        self._say("game.replay_hint")

    def _autosave(self) -> None:
        if not self.autosave_enabled:
            return
        try:
            save_state(self.project, self.state, self.autosave_path)
        except SaveError:
            self._say("game.autosave_failed")

    def _clear_autosave(self) -> None:
        if self.autosave_path.is_file():
            self.autosave_path.unlink()

    def _say(self, key: str, **params: object) -> None:
        text = self.engine.translator.t(key, self.state.language, **params)
        print(OutputLine(text, Style.SYSTEM).text)


def run(
    project_path: Path,
    *,
    language: str | None = None,
    save_path: Path | None = None,
    color: bool | None = None,
    resume: bool = True,
    autosave: bool = True,
) -> int:
    project = load_project(project_path)
    if color is None:
        color = sys.stdout.isatty()
    app = TerminalApp(
        project,
        language=language,
        save_path=save_path,
        color=color,
        resume=resume,
        autosave=autosave,
    )
    return app.run()
