"""Загрузчик плагинов из файловой системы.

Каждый плагин — папка в директории плагинов с обязательным файлом ``plugin.py``,
содержащим класс-наследник BasePlugin.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

def resolve_plugins_dir() -> Path:
    """Записываемый каталог плагинов в данных пользователя."""
    from quantis.utils import app_paths

    return app_paths.user_plugins_dir()


def plugin_search_dirs() -> list[Path]:
    """Все каталоги, где ищем плагины: пользовательский + из комплекта."""
    from quantis.utils import app_paths

    dirs = [resolve_plugins_dir()]
    bundled = app_paths.bundled_plugins_dir()
    try:
        same = bundled.resolve() == dirs[0].resolve()
    except OSError:
        same = False
    if not same and bundled.is_dir():
        dirs.append(bundled)
    return dirs


_cached_plugin_dir: Path | None = None


def get_plugins_dir() -> Path:
    global _cached_plugin_dir
    if _cached_plugin_dir is None:
        _cached_plugin_dir = resolve_plugins_dir()
    return _cached_plugin_dir


# Обратная совместимость: вычисляется при первом обращении через __getattr__ модуля
def __getattr__(name: str):
    if name in ("DEFAULT_PLUGIN_DIR", "PLUGIN_DIR"):
        return get_plugins_dir()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


_PLUGIN_PACKAGE = "quantis_plugins"


@dataclass
class PluginMeta:
    """Метаданные обнаруженного плагина (до загрузки)."""

    plugin_id: str
    name: str
    version: str
    author: str
    description: str
    path: Path
    entry: Path
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


class PluginLoader:
    """Обнаруживает и загружает плагины."""

    def __init__(self, plugin_dir: Path | None = None) -> None:
        # Явный путь снаружи — только он, иначе пользовательский + из комплекта
        self._dirs = [plugin_dir] if plugin_dir is not None else plugin_search_dirs()

    @property
    def _dir(self) -> Path:
        """Основной (записываемый) каталог плагинов."""
        return self._dirs[0]

    # ── Публичный API ─────────────────────────────────────────────────────────

    def discover(self) -> list[PluginMeta]:
        """Сканирует каталоги плагинов и возвращает список метаданных.

        Одноимённые плагины из комплекта перекрываются пользовательскими:
        побеждает тот, что найден раньше.
        """
        metas: list[PluginMeta] = []
        seen: set[str] = set()

        for folder in self._dirs:
            if not folder.exists():
                try:
                    folder.mkdir(parents=True, exist_ok=True)
                    logger.info("Создана директория для плагинов: %s", folder)
                except OSError:
                    logger.warning("Нет доступа к каталогу плагинов: %s", folder)
                continue

            if not folder.is_dir():
                logger.warning("Путь плагинов не является директорией: %s", folder)
                continue

            for entry in sorted(folder.iterdir()):
                if not entry.is_dir() or entry.name.startswith("_"):
                    continue
                if entry.name in seen:
                    continue
                seen.add(entry.name)
                meta = self._read_meta(entry)
                metas.append(meta)
                if not meta.is_valid:
                    logger.warning("Плагин '%s' пропущен: %s", entry.name, meta.errors)

        return metas

    def load_class(self, meta: PluginMeta):
        """Импортирует модуль плагина и возвращает класс BasePlugin."""
        module = self._import_module(meta)
        plugin_class = self._find_plugin_class(module, meta.plugin_id)
        return plugin_class

    # ── Внутренние методы ─────────────────────────────────────────────────────

    def _read_meta(self, plugin_dir: Path) -> PluginMeta:
        plugin_id = plugin_dir.name
        entry = plugin_dir / "plugin.py"
        errors: list[str] = []

        if not entry.exists():
            errors.append("отсутствует plugin.py")

        manifest_path = plugin_dir / "manifest.json"
        data = {}
        if manifest_path.exists():
            try:
                with manifest_path.open(encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Ошибка чтения manifest.json для '%s': %s", plugin_id, e)

        return PluginMeta(
            plugin_id=data.get("id", plugin_id),
            name=data.get("name", plugin_id),
            version=data.get("version", "0.0.0"),
            author=data.get("author", "Unknown"),
            description=data.get("description", ""),
            path=plugin_dir,
            entry=entry,
            errors=errors,
        )

    @staticmethod
    def _ensure_plugin_package(plugin_dir: Path) -> None:
        """Регистрирует namespace-пакет quantis_plugins для относительных импортов."""
        resolved = str(plugin_dir.resolve())
        if _PLUGIN_PACKAGE not in sys.modules:
            pkg = types.ModuleType(_PLUGIN_PACKAGE)
            pkg.__path__ = []
            sys.modules[_PLUGIN_PACKAGE] = pkg
        pkg_path = sys.modules[_PLUGIN_PACKAGE].__path__
        if resolved not in pkg_path:
            pkg_path.append(resolved)

    @staticmethod
    def _import_module(meta: PluginMeta):
        plugin_dir = meta.path.resolve()
        PluginLoader._ensure_plugin_package(plugin_dir)

        module_name = f"{_PLUGIN_PACKAGE}.{meta.plugin_id}"
        plugin_dir_str = str(plugin_dir)

        spec = importlib.util.spec_from_file_location(
            module_name,
            meta.entry,
            submodule_search_locations=[plugin_dir_str],
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Не удалось загрузить спецификацию для {meta.entry}")

        module = importlib.util.module_from_spec(spec)
        module.__package__ = _PLUGIN_PACKAGE

        sys.modules[module_name] = module

        if plugin_dir_str not in sys.path:
            sys.path.insert(0, plugin_dir_str)

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            sys.modules.pop(module_name, None)
            raise ImportError(
                f"Ошибка выполнения кода плагина {meta.plugin_id}: {e}"
            ) from e

        return module

    @staticmethod
    def _find_plugin_class(module, plugin_id: str):
        """Ищет класс-наследник BasePlugin в модуле."""
        from quantis.plugins.base import BasePlugin

        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if (
                isinstance(obj, type)
                and issubclass(obj, BasePlugin)
                and obj is not BasePlugin
            ):
                return obj

        raise ImportError(
            f"В плагине '{plugin_id}' не найден класс-наследник BasePlugin"
        )
