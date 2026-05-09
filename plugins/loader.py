"""Загрузчик плагинов из файловой системы.

Каждый плагин — папка в директории плагинов с обязательным файлом ``plugin.py``,
содержащим класс-наследник BasePlugin.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Динамически определяем корневую папку проекта (где лежит main.py)
# и ищем папку plugins_dir рядом с ней
BASE_DIR = Path(__file__).parent.parent
DEFAULT_PLUGIN_DIR = BASE_DIR / "plugins_dir"
PLUGIN_DIR = DEFAULT_PLUGIN_DIR


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
        # Позволяем передать путь снаружи, иначе используем дефолтный
        self._dir = plugin_dir or DEFAULT_PLUGIN_DIR

    # ── Публичный API ─────────────────────────────────────────────────────────

    def discover(self) -> list[PluginMeta]:
        """Сканирует папку плагинов и возвращает список метаданных."""
        # Создаем папку, если её вдруг нет, чтобы не было ошибок
        if not self._dir.exists():
            self._dir.mkdir(parents=True, exist_ok=True)
            logger.info("Создана директория для плагинов: %s", self._dir)
            return []

        if not self._dir.is_dir():
            logger.warning("Путь плагинов не является директорией: %s", self._dir)
            return []

        metas: list[PluginMeta] = []
        for entry in sorted(self._dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith("_"):
                continue
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
    def _import_module(meta: PluginMeta):
        module_name = f"quantis_plugins.{meta.plugin_id}"

        spec = importlib.util.spec_from_file_location(module_name, meta.entry)
        if spec is None or spec.loader is None:
            raise ImportError(f"Не удалось загрузить спецификацию для {meta.entry}")

        module = importlib.util.module_from_spec(spec)

        sys.modules[module_name] = module

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            # Очищаем sys.modules при ошибке загрузки, чтобы не оставлять мусор
            sys.modules.pop(module_name, None)
            raise ImportError(
                f"Ошибка выполнения кода плагина {meta.plugin_id}: {e}"
            ) from e

        return module

    @staticmethod
    def _find_plugin_class(module, plugin_id: str):
        """Ищет класс-наследник BasePlugin в модуле."""
        from plugins.base import BasePlugin

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
