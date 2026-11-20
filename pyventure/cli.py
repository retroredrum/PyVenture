"""Interface en ligne de commande de PyVenture."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROJECT = REPO_ROOT / "examples" / "mini-game" / "game.yaml"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema" / "game.schema.json"


def _parse_size(value: str) -> tuple[int, int]:
    try:
        width, height = value.lower().split("x")
        return max(320, int(width)), max(240, int(height))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("format attendu : LxH, par exemple 960x720") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pyventure",
        description="Moteur d'aventure texte avec illustrations pixel art.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    play = subparsers.add_parser("play", help="Jouer en mode terminal")
    play.add_argument("-p", "--project", type=Path, default=None, help="Fichier game.yaml")
    play.add_argument("--lang", default=None, help="Langue de départ (fr, en, ...)")
    play.add_argument("--save", type=Path, default=None, help="Fichier de sauvegarde")
    play.add_argument("--no-color", action="store_true", help="Désactiver les couleurs")
    play.add_argument("--fresh", action="store_true", help="Ignorer la sauvegarde automatique")
    play.add_argument(
        "--no-autosave", action="store_true", help="Désactiver la sauvegarde automatique"
    )
    play.add_argument("--legacy", action="store_true", help="Lancer le moteur historique")
    play.add_argument("--gui", action="store_true", help="Lancer la fenêtre pygame")
    play.add_argument(
        "--size",
        type=_parse_size,
        default=(960, 720),
        metavar="LxH",
        help="Taille de la fenêtre (défaut 960x720)",
    )

    validate = subparsers.add_parser("validate", help="Valider un projet YAML")
    validate.add_argument("project", type=Path, nargs="?", default=None)
    validate.add_argument("--schema", type=Path, default=None, help="Schéma JSON alternatif")
    validate.add_argument(
        "--strict-i18n", action="store_true", help="Traductions manquantes = erreur"
    )

    editor = subparsers.add_parser("editor", help="Lancer l'éditeur graphique (Phase 3+)")
    editor.add_argument("project", type=Path, nargs="?", default=None)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "play":
        return _play(args)
    if args.command == "validate":
        return _validate_project(args.project, args.schema, args.strict_i18n)
    if args.command == "editor":
        return _run_editor(args.project)

    parser.error(f"commande inconnue : {args.command}")
    return 2


def _resolve_project(path: Path | None) -> Path | None:
    if path is not None:
        return path
    if Path("game.yaml").is_file():
        return Path("game.yaml")
    if DEFAULT_PROJECT.is_file():
        return DEFAULT_PROJECT
    return None


def _play(args: argparse.Namespace) -> int:
    if args.legacy:
        return _run_legacy()

    project = _resolve_project(args.project)
    if project is None:
        print(
            "Aucun projet trouvé. Indiquez-en un avec --project chemin/vers/game.yaml.",
            file=sys.stderr,
        )
        return 1

    if args.gui:
        return _play_gui(args, project)

    try:
        from .ui.terminal.app import run
    except ImportError as exc:
        _report_missing_dependency(exc)
        return 1

    try:
        return run(
            project,
            language=args.lang,
            save_path=args.save,
            color=False if args.no_color else None,
            resume=not args.fresh,
            autosave=not args.no_autosave,
        )
    except Exception as exc:  # noqa: BLE001 - message utilisateur
        from .core.errors import PyVentureError

        if isinstance(exc, PyVentureError):
            print(f"Erreur : {exc}", file=sys.stderr)
            return 1
        raise


def _play_gui(args: argparse.Namespace, project: Path) -> int:
    try:
        from .ui.pygame.app import run as run_gui
    except ImportError as exc:
        _report_missing_dependency(exc, gui=True)
        return 1

    from .core.errors import PyVentureError

    try:
        return run_gui(
            project,
            language=args.lang,
            save_path=args.save,
            size=args.size,
            resume=not args.fresh,
            autosave=not args.no_autosave,
        )
    except PyVentureError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - dépendance SDL manquante
        print(f"Impossible d'ouvrir la fenêtre : {exc}", file=sys.stderr)
        return 1


def _report_missing_dependency(exc: ImportError, *, gui: bool = False) -> None:
    name = exc.name or str(exc)
    gui_line = (
        '\nPour la fenêtre graphique, ajoute l\'extra gui :\n  pip install -e ".[gui]"\n'
        if gui
        else ""
    )
    print(
        f"Dépendance manquante : {name}.\n"
        "PyVenture n'est pas installé dans ce Python.\n\n"
        "Option 1 — installer les dépendances dans cet environnement :\n"
        "  python3 -m pip install -e .\n\n"
        "Option 2 — utiliser un environnement virtuel :\n"
        "  python3 -m venv .venv\n"
        "  source .venv/bin/activate\n"
        '  pip install -e ".[dev,gui]"\n'
        "  python -m pyventure play\n"
        f"{gui_line}",
        file=sys.stderr,
    )


def _run_legacy() -> int:
    """Lance le moteur historique tant que la parité n'est pas prouvée."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    try:
        from engine import mainGame
    except ImportError as exc:
        print(f"Impossible de charger le moteur historique : {exc}", file=sys.stderr)
        return 1
    try:
        mainGame()
    except (EOFError, KeyboardInterrupt):
        print()
    return 0


def _validate_project(project: Path | None, schema_path: Path | None, strict_i18n: bool) -> int:
    try:
        from .core.errors import PyVentureError
        from .core.loader import load_project
    except ImportError as exc:
        _report_missing_dependency(exc)
        return 1

    resolved = _resolve_project(project)
    if resolved is None:
        print("Aucun projet à valider. Indiquez un chemin.", file=sys.stderr)
        return 1

    try:
        load_project(resolved, validate=True, strict_i18n=strict_i18n)
    except PyVentureError as exc:
        print(str(exc), file=sys.stderr)
        print(f"Échec de la validation de {resolved}.", file=sys.stderr)
        return 1

    print(f"OK : {resolved} est valide.")
    return 0


def _run_editor(project: Path | None) -> int:
    try:
        from .editor.app import main as editor_main
    except ImportError as exc:
        _report_missing_dependency(exc)
        return 1

    return editor_main([str(project)] if project else [])


if __name__ == "__main__":
    raise SystemExit(main())
