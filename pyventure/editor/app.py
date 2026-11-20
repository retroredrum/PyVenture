"""Éditeur graphique PyVenture (Phase 3)."""

from __future__ import annotations

import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Point d'entrée de l'éditeur.

    L'éditeur graphique est spécifié dans ``docs/04-editeur.md`` et sera
    implémenté en Phase 3. En attendant, la commande explique la situation.
    """
    project = " ".join(argv) if argv else "(aucun projet)"
    print(
        "L'éditeur graphique est prévu en Phase 3.\n"
        f"Projet demandé : {project}\n"
        "Voir docs/03-roadmap.md et docs/04-editeur.md.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
