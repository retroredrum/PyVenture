"""Point d'entrée de l'éditeur graphique PyVenture."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path


def main(argv: Sequence[str] | None = None) -> int:
    """Lance l'éditeur Tkinter."""
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print(
            "Tkinter est requis pour l'éditeur.\n"
            "Sur Debian/Ubuntu : sudo apt install python3-tk\n"
            "Le jeu et le mode terminal n'en ont pas besoin.",
            file=sys.stderr,
        )
        return 1

    from .main_window import open_editor

    arguments = list(argv or [])
    path = Path(arguments[0]) if arguments else None
    try:
        open_editor(path)
    except Exception as exc:  # noqa: BLE001 - message utilisateur
        print(f"Erreur de l'éditeur : {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
