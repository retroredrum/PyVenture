"""Inventaire des illustrations d'un projet : statut, placeholders, inutilisés."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_OBJECT_SIZE = (32, 32)
DEFAULT_ENDING_SIZE = (320, 180)


@dataclass(frozen=True)
class AssetRef:
    """Une illustration référencée par le contenu."""

    path: str
    kind: str
    owner: str
    detail: str = ""

    def label(self) -> str:
        return f"{self.kind} {self.owner}" + (f" / {self.detail}" if self.detail else "")


@dataclass(frozen=True)
class AssetStatus:
    ref: AssetRef
    exists: bool
    size: tuple[int, int] | None
    expected: tuple[int, int] = (0, 0)

    @property
    def state(self) -> str:
        if not self.exists:
            return "manquant"
        if self.size is not None and self.expected != (0, 0) and self.size != self.expected:
            return "dimensions"
        return "ok"


def collect_assets(data: dict[str, Any]) -> list[AssetRef]:
    """Liste toutes les illustrations référencées dans le contenu."""
    refs: list[AssetRef] = []

    rooms = data.get("rooms") or {}
    if isinstance(rooms, dict):
        for room_id, room in rooms.items():
            if not isinstance(room, dict):
                continue
            if room.get("art"):
                refs.append(AssetRef(str(room["art"]), "room", str(room_id)))
            variants = room.get("variants") or {}
            if isinstance(variants, dict):
                for name, variant in variants.items():
                    if isinstance(variant, dict) and variant.get("art"):
                        refs.append(
                            AssetRef(str(variant["art"]), "variant", str(room_id), str(name))
                        )

    objects = data.get("objects") or {}
    if isinstance(objects, dict):
        for object_id, game_object in objects.items():
            if not isinstance(game_object, dict):
                continue
            if game_object.get("art"):
                refs.append(AssetRef(str(game_object["art"]), "object", str(object_id)))
            states = game_object.get("states") or {}
            if isinstance(states, dict):
                for name, state in states.items():
                    if isinstance(state, dict) and state.get("art"):
                        refs.append(AssetRef(str(state["art"]), "state", str(object_id), str(name)))

    endings = data.get("endings") or {}
    if isinstance(endings, dict):
        for ending_id, ending in endings.items():
            if isinstance(ending, dict) and ending.get("art"):
                refs.append(AssetRef(str(ending["art"]), "ending", str(ending_id)))

    return refs


def meta_size(data: dict[str, Any]) -> tuple[int, int]:
    art = (data.get("meta") or {}).get("art") or {}
    return int(art.get("width", 320)), int(art.get("height", 180))


def expected_size(data: dict[str, Any], ref: AssetRef) -> tuple[int, int]:
    if ref.kind in {"room", "variant"}:
        return meta_size(data)
    if ref.kind in {"object", "state"}:
        return DEFAULT_OBJECT_SIZE
    return DEFAULT_ENDING_SIZE


def resolve(root: Path, ref: AssetRef) -> Path:
    return Path(root) / ref.path


def image_size(path: Path) -> tuple[int, int] | None:
    """Dimensions d'une image, ou ``None`` si illisible (sans dépendre de Pillow)."""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except OSError:
        return None


def statuses(root: Path, data: dict[str, Any]) -> list[AssetStatus]:
    result: list[AssetStatus] = []
    for ref in collect_assets(data):
        path = resolve(root, ref)
        expected = expected_size(data, ref)
        if path.is_file():
            result.append(AssetStatus(ref, True, image_size(path), expected))
        else:
            result.append(AssetStatus(ref, False, None, expected))
    return result


def missing(root: Path, data: dict[str, Any]) -> list[AssetRef]:
    return [status.ref for status in statuses(root, data) if not status.exists]


def unused_files(root: Path, data: dict[str, Any]) -> list[Path]:
    """Fichiers image du dossier ``art/`` qui ne sont référencés nulle part."""
    art_root = Path(root) / "art"
    if not art_root.is_dir():
        return []
    referenced = {(Path(root) / ref.path).resolve() for ref in collect_assets(data)}
    unused: list[Path] = []
    for path in sorted(art_root.rglob("*")):
        if (
            path.is_file()
            and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}
            and path.resolve() not in referenced
        ):
            unused.append(path)
    return unused


def placeholder_color(label: str) -> tuple[int, int, int]:
    seed = sum(ord(char) for char in label) % 360
    import colorsys

    red, green, blue = colorsys.hsv_to_rgb(seed / 360.0, 0.35, 0.5)
    return int(red * 255), int(green * 255), int(blue * 255)


def make_placeholder(path: Path, size: tuple[int, int], label: str) -> Path:
    """Génère une image placeholder et l'écrit dans ``path``."""
    from PIL import Image, ImageDraw

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = max(1, size[0]), max(1, size[1])
    image = Image.new("RGB", (width, height), placeholder_color(label))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, width - 1, height - 1], outline=(20, 20, 28), width=max(1, width // 40))
    text = label
    try:
        text_width = draw.textlength(text)
    except AttributeError:  # pragma: no cover - très vieilles versions
        text_width = len(text) * 6
    draw.text(((width - text_width) / 2, height / 2 - 6), text, fill=(240, 240, 240))
    image.save(path)
    return path


def import_asset(source: Path, root: Path, relative: str) -> Path:
    """Copie un fichier image vers ``root/relative``."""
    source = Path(source)
    target = Path(root) / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    return target
