"""Путь к ресурсам (assets)"""
import sys
from pathlib import Path


def get_asset_path(relative_path: str) -> str:
    """
    Превращает внутренний путь (например, 'assets/icons/play.svg')
    в абсолютный системный путь.
    """
    base_path = Path(__file__).parent.parent

    if hasattr(sys, '_MEIPASS'):
        base_path = Path(sys._MEIPASS)

    absolute_path = base_path / relative_path

    return str(absolute_path)