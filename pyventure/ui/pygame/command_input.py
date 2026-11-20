"""Champ de saisie de commande, avec historique et complétion."""

from __future__ import annotations

import os
from collections.abc import Callable

import pygame

from .theme import Fonts, Theme


class CommandInput:
    """Saisie clavier d'une commande."""

    def __init__(self, theme: Theme, fonts: Fonts) -> None:
        self.theme = theme
        self.fonts = fonts
        self.text = ""
        self.history: list[str] = []
        self.history_index = 0

    def submit(self) -> str | None:
        """Valide la saisie et renvoie la commande, ou ``None`` si vide."""
        text = self.text.strip()
        self.text = ""
        if not text:
            self.history_index = len(self.history)
            return None
        if not self.history or self.history[-1] != text:
            self.history.append(text)
        self.history_index = len(self.history)
        return text

    def handle_event(
        self,
        event: pygame.event.Event,
        completer: Callable[[str], list[str]] | None = None,
    ) -> str | None:
        if event.type == pygame.TEXTINPUT:
            self.text += event.text
            return None
        if event.type != pygame.KEYDOWN:
            return None

        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return self.submit()
        if event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        elif event.key == pygame.K_ESCAPE:
            self.text = ""
        elif event.key == pygame.K_UP:
            self._history_move(-1)
        elif event.key == pygame.K_DOWN:
            self._history_move(1)
        elif event.key == pygame.K_TAB and completer is not None:
            self._complete(completer)
        return None

    def _history_move(self, direction: int) -> None:
        if not self.history:
            return
        self.history_index = max(0, min(len(self.history), self.history_index + direction))
        self.text = (
            self.history[self.history_index] if self.history_index < len(self.history) else ""
        )

    def _complete(self, completer: Callable[[str], list[str]]) -> None:
        prefix = self.text.split(" ")[-1]
        options = [
            option
            for option in completer(self.text)
            if option.lower().startswith(prefix.lower()) and option.lower() != prefix.lower()
        ]
        if not options:
            return
        head = self.text[: len(self.text) - len(prefix)]
        if len(options) == 1:
            self.text = f"{head}{options[0]} "
        else:
            common = os.path.commonprefix([option.lower() for option in options])
            self.text = f"{head}{common}"

    def draw(self, target: pygame.Surface, rect: pygame.Rect, prompt: str, hint: str = "") -> None:
        pygame.draw.rect(target, self.theme.input_bg, rect)
        pygame.draw.rect(target, self.theme.panel_border, rect, width=1)
        prompt_surface = self.fonts.input.render(prompt, True, self.theme.prompt)
        target.blit(
            prompt_surface, (rect.x + 10, rect.y + (rect.height - prompt_surface.get_height()) // 2)
        )
        text_x = rect.x + 10 + prompt_surface.get_width() + 4
        text_surface = self.fonts.input.render(self.text, True, self.theme.input_fg)
        target.blit(text_surface, (text_x, rect.y + (rect.height - text_surface.get_height()) // 2))
        if pygame.time.get_ticks() % 1000 < 500:
            caret_x = text_x + text_surface.get_width() + 2
            caret = pygame.Rect(caret_x, rect.y + 8, 2, rect.height - 16)
            pygame.draw.rect(target, self.theme.input_fg, caret)
        if hint:
            hint_surface = self.fonts.small.render(hint, True, self.theme.panel_border)
            target.blit(
                hint_surface,
                (
                    rect.right - hint_surface.get_width() - 10,
                    rect.y + (rect.height - hint_surface.get_height()) // 2,
                ),
            )
