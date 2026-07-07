"""Загрузка QSS-тем и путей к ресурсам."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon

from quantis.utils import get_asset_path

THEME_CLASSIC = "classic"
THEME_NEON = "neon"
THEME_EDITORIAL = "editorial"
THEME_LIGHT = "light"
THEME_YELLOW_DARK = "yellow_dark"
DEFAULT_UI_THEME = THEME_NEON

UI_THEME_LABELS: dict[str, str] = {
    THEME_CLASSIC: "Классическая",
    THEME_NEON: "Неоновая",
    THEME_EDITORIAL: "Редакционная",
    THEME_LIGHT: "Светлая",
    THEME_YELLOW_DARK: "Тёмно-жёлтая",
}

UI_THEME_BASE_QSS: dict[str, str] = {
    THEME_CLASSIC: "dark",
    THEME_NEON: "dark",
    THEME_EDITORIAL: "dark",
    THEME_LIGHT: "light",
    THEME_YELLOW_DARK: "yellow_dark",
}

_SHARED_WIDGET_STYLES = (
    "home.qss",
    "play_menu.qss",
    "playlist_page.qss",
    "playlist_preview.qss",
    "quantis.qss",
    "track_card.qss",
)


def styles_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "styles"


def icon_path(name: str) -> str:
    return get_asset_path(f"assets/icons/{name}")


def load_icon(name: str) -> QIcon:
    return QIcon(icon_path(name))


def load_theme(theme: str = "dark") -> str:
    theme_file = styles_dir() / f"{theme}.qss"
    if not theme_file.is_file():
        theme_file = styles_dir() / "dark.qss"
    return theme_file.read_text(encoding="utf-8")


def normalize_ui_theme(ui_theme: str | None) -> str:
    if ui_theme in UI_THEME_LABELS:
        return ui_theme
    return DEFAULT_UI_THEME


def load_widget_styles(ui_theme: str = DEFAULT_UI_THEME) -> str:
    theme_id = normalize_ui_theme(ui_theme)
    parts: list[str] = []

    widget_dir = styles_dir() / "widget_styles"
    for name in _SHARED_WIDGET_STYLES:
        path = widget_dir / name
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8"))

    theme_dir = styles_dir() / "themes" / theme_id
    if theme_dir.is_dir():
        for path in sorted(theme_dir.glob("*.qss")):
            parts.append(path.read_text(encoding="utf-8"))

    return "\n".join(parts)


def wallpaper_path() -> str:
    candidates = [
        Path(__file__).resolve().parents[3]
        / "assets"
        / "background"
        / "majestic-mountain-peak-tranquil-winter-landscape-generated-by-ai.jpg",
        Path(get_asset_path("assets/background/wallpaper.jpg")),
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return ""


def load_stylesheet(ui_theme: str = DEFAULT_UI_THEME) -> str:
    theme_id = normalize_ui_theme(ui_theme)
    base = UI_THEME_BASE_QSS.get(theme_id, "dark")
    return load_theme(base) + "\n" + load_widget_styles(theme_id)


def format_ms(ms: int) -> str:
    if ms < 0:
        ms = 0
    total_sec = ms // 1000
    minutes, seconds = divmod(total_sec, 60)
    return f"{minutes}:{seconds:02d}"
