"""Базовый класс для всех плагинов Quantis."""

from __future__ import annotations

from PySide6.QtCore import QSettings

from quantis.core.plugin_host import PluginHost


class BasePlugin:
    """Базовый класс для всех плагинов Quantis."""

    name: str = "Без названия"
    version: str = "0.0.0"
    author: str = "Unknown"
    description: str = ""
    icon: str = ""

    def __init__(self, host: PluginHost, settings: QSettings | None = None) -> None:
        self.host = host
        self.settings = settings

    @property
    def app(self) -> PluginHost:
        """Алиас для обратной совместимости с примерами в документации."""
        return self.host

    async def on_load(self) -> None:
        ...

    async def on_unload(self) -> None:
        ...

    async def on_minimize(self) -> None:
        ...

    async def on_restore(self) -> None:
        ...

    def subscribe(self, event: str, callback) -> None:
        self.host.event_bus.subscribe(event, callback)

    def unsubscribe(self, event: str, callback) -> None:
        self.host.event_bus.unsubscribe(event, callback)

    def __repr__(self) -> str:
        return f"<Plugin {self.name!r} v{self.version}>"

    __str__ = __repr__
