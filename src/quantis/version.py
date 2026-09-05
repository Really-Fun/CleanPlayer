"""Версия Quantis.

Единственный источник — ``[project].version`` в ``pyproject.toml``.
Менять её: ``poetry version 0.2.1`` / ``poetry version patch``.
"""

from __future__ import annotations

import sys
from pathlib import Path


def project_version(root: Path | None = None) -> str:
    """Читает версию из ``pyproject.toml`` (запуск из исходников / тесты)."""
    try:
        import tomllib
    except ImportError:  # pragma: no cover
        return ""
    pyproject = (root or _repo_root()) / "pyproject.toml"
    if not pyproject.is_file():
        return ""
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return ""
    value = data.get("project", {}).get("version")
    return str(value).strip() if value else ""


def _repo_root() -> Path:
    # src/quantis/version.py → корень репозитория
    return Path(__file__).resolve().parents[2]


def _version_from_stamp() -> str:
    """Файл, который PyInstaller кладёт рядом с модулем при сборке exe."""
    path = Path(__file__).with_name("version.txt")
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return ""


def _version_from_metadata() -> str:
    try:
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:  # pragma: no cover
        return ""
    try:
        return version("quantis")
    except PackageNotFoundError:
        return ""


def get_version() -> str:
    """Runtime-версия: из исходников — pyproject, в exe — штамп сборки."""
    frozen = bool(getattr(sys, "frozen", False))
    if frozen:
        return (
            _version_from_stamp()
            or _version_from_metadata()
            or project_version()
            or "0.0.0"
        )
    return project_version() or _version_from_metadata() or "0.0.0"


__version__ = get_version()
