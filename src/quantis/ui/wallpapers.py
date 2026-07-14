"""Каталог статичных обоев (background/user и assets/background)."""

from __future__ import annotations

from pathlib import Path

from quantis.utils import get_asset_path

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def project_root() -> Path:
    from quantis.utils.resource_path import app_dir

    return app_dir()


def user_backgrounds_dir() -> Path:
    """Папка пользовательских обоев: background/user/ в корне проекта."""
    path = project_root() / "background" / "user"
    path.mkdir(parents=True, exist_ok=True)
    return path


def bundled_backgrounds_dir() -> Path:
    return Path(get_asset_path("assets/background"))


def is_wallpaper_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in _IMAGE_EXTENSIONS


def wallpaper_dirs() -> list[Path]:
    return [
        bundled_backgrounds_dir(),
        project_root() / "assets" / "background",
        user_backgrounds_dir(),
    ]


def scan_wallpapers() -> list[Path]:
    """Все доступные изображения из встроенных и пользовательских папок."""
    found: list[Path] = []
    seen: set[str] = set()
    for folder in wallpaper_dirs():
        if not folder.is_dir():
            continue
        for entry in sorted(folder.iterdir()):
            if not is_wallpaper_file(entry):
                continue
            key = str(entry.resolve())
            if key in seen:
                continue
            seen.add(key)
            found.append(entry)
    return found


def wallpaper_display_name(path: Path) -> str:
    try:
        if path.resolve().parent == user_backgrounds_dir().resolve():
            return f"Мои — {path.stem}"
    except OSError:
        pass
    return path.stem


def default_wallpaper_path() -> str:
    for folder in wallpaper_dirs():
        for name in (
            "majestic-mountain-peak-tranquil-winter-landscape-generated-by-ai.jpg",
            "wallpaper.jpg",
        ):
            path = folder / name
            if path.is_file():
                return str(path.resolve())
    for path in scan_wallpapers():
        return str(path.resolve())
    return ""


def resolve_wallpaper_path(stored: str | None = None) -> str:
    if stored:
        chosen = Path(stored)
        if chosen.is_file() and is_wallpaper_file(chosen):
            return str(chosen.resolve())
    return default_wallpaper_path()
