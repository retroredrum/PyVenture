"""Rendu ANSI des lignes du moteur."""

from __future__ import annotations

import sys
from typing import TextIO

from ...core.events import OutputLine, Style, TurnResult

RESET = "\033[0m"

STYLES: dict[Style, str] = {
    Style.NORMAL: "",
    Style.ROOM_TITLE: "\033[1;33m",
    Style.DESCRIPTION: "",
    Style.EXIT: "\033[36m",
    Style.ITEM: "\033[32m",
    Style.ERROR: "\033[31m",
    Style.SUCCESS: "\033[32m",
    Style.SYSTEM: "\033[35m",
    Style.DIALOGUE: "\033[34m",
}


def render_line(line: OutputLine, *, color: bool = True) -> str:
    if not color:
        return line.text
    prefix = STYLES.get(line.style, "")
    return f"{prefix}{line.text}{RESET}" if prefix else line.text


def print_result(result: TurnResult, out: TextIO | None = None, *, color: bool = True) -> None:
    stream = out or sys.stdout
    for line in result.lines:
        print(render_line(line, color=color), file=stream)
