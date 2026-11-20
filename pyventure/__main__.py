"""Point d'entrée pour ``python -m pyventure``."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
