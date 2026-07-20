"""Установка плагинов из zip / URL."""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from quantis.plugins.loader import resolve_plugins_dir

logger = logging.getLogger(__name__)

_SAFE_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


class PluginInstallError(Exception):
    pass


def _safe_plugin_id(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip()).strip("_")
    if not cleaned or not _SAFE_ID.match(cleaned):
        raise PluginInstallError(f"Недопустимое имя плагина: {name!r}")
    return cleaned


def _find_plugin_root(extracted: Path) -> Path:
    """Ищет каталог с plugin.py (корень zip или одна вложенная папка)."""
    if (extracted / "plugin.py").is_file():
        return extracted
    children = [p for p in extracted.iterdir() if p.is_dir() and not p.name.startswith("__")]
    if len(children) == 1 and (children[0] / "plugin.py").is_file():
        return children[0]
    for child in extracted.rglob("plugin.py"):
        return child.parent
    raise PluginInstallError("В архиве не найден plugin.py")


def install_plugin_from_zip(zip_path: str | Path, *, overwrite: bool = True) -> str:
    """Распаковывает zip в plugins_dir. Возвращает plugin_id."""
    path = Path(zip_path)
    if not path.is_file():
        raise PluginInstallError(f"Файл не найден: {path}")
    if path.suffix.lower() != ".zip":
        raise PluginInstallError("Нужен архив .zip")

    plugins_dir = resolve_plugins_dir()
    plugins_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="quantis_plugin_") as tmp:
        tmp_path = Path(tmp)
        try:
            with zipfile.ZipFile(path, "r") as zf:
                for member in zf.namelist():
                    dest = (tmp_path / member).resolve()
                    if not str(dest).startswith(str(tmp_path.resolve())):
                        raise PluginInstallError("Небезопасный путь в архиве")
                zf.extractall(tmp_path)
        except zipfile.BadZipFile as exc:
            raise PluginInstallError("Повреждённый zip-архив") from exc

        root = _find_plugin_root(tmp_path)
        if root == tmp_path:
            plugin_id = _safe_plugin_id(path.stem)
        else:
            plugin_id = _safe_plugin_id(root.name)

        target = plugins_dir / plugin_id
        if target.exists():
            if not overwrite:
                raise PluginInstallError(f"Плагин «{plugin_id}» уже установлен")
            shutil.rmtree(target)

        shutil.copytree(root, target)
        if not (target / "plugin.py").is_file():
            shutil.rmtree(target, ignore_errors=True)
            raise PluginInstallError("После установки нет plugin.py")

        logger.info("Плагин установлен: %s → %s", plugin_id, target)
        return plugin_id


def download_plugin_zip(url: str, dest_dir: Path | None = None) -> Path:
    """Скачивает zip по URL во временный/указанный каталог."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise PluginInstallError("URL должен начинаться с http:// или https://")

    dest_dir = dest_dir or Path(tempfile.gettempdir())
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = Path(parsed.path).name or "plugin.zip"
    if not name.lower().endswith(".zip"):
        name = f"{name}.zip"
    dest = dest_dir / name

    req = Request(url, headers={"User-Agent": "Quantis/1.0"})
    try:
        with urlopen(req, timeout=60) as resp, open(dest, "wb") as out:
            shutil.copyfileobj(resp, out)
    except Exception as exc:
        raise PluginInstallError(f"Не удалось скачать: {exc}") from exc

    if dest.stat().st_size < 32:
        dest.unlink(missing_ok=True)
        raise PluginInstallError("Скачанный файл пуст или слишком маленький")
    return dest


def install_plugin_from_url(url: str, *, overwrite: bool = True) -> str:
    zip_path = download_plugin_zip(url)
    try:
        return install_plugin_from_zip(zip_path, overwrite=overwrite)
    finally:
        zip_path.unlink(missing_ok=True)
