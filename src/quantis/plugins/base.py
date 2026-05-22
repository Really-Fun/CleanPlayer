"""Базовый класс для всех плагинов Quantis.

Минимальный плагин::

    from quantis.plugins.base import BasePlugin

    class HelloPlugin(BasePlugin):
        name    = "Название плагина"
        version = "1.0.0"
        author  = "You"
        description = "Описание плагина"

        async def on_load(self):
            self.app.event_bus.subscribe("track_changed", self._greet)

        async def on_unload(self):
            self.app.event_bus.unsubscribe("track_changed", self._greet)

        def _greet(self, track):
            print(f"Сейчас играет: {track.title}")
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from PySide6.QtCore import QSettings

if TYPE_CHECKING:
    from quantis.core.app_context import AppContext


class BasePlugin:
    """Базовый класс для всех плагинов Quantis.

    Attributes:
        name:        Отображаемое название плагина.
        version:     Версия в формате ``MAJOR.MINOR.PATCH``.
        author:      Автор / организация.
        description: Краткое описание что делает плагин.
        app:         Контекст приложения. Доступен после ``__init__``.
        icon:        Иконка (Превью) плагина. Относительный путь
    """

    name: str = "Без названия"
    version: str = "0.0.0"
    author: str = "Unknown"
    description: str = ""
    icon: str = ""

    def __init__(self, app_context: AppContext, settings: QSettings = None) -> None:
        self.app = app_context
        self.settings = settings

    async def on_load(self) -> None:
        """Вызывается при включении плагина.

        Здесь подписывайся на события, регистрируй страницы, добавляй кнопки.
        Можно использовать ``await`` для асинхронных операций.
        """
        ...

    async def on_unload(self) -> None:
        """Вызывается при выключении плагина.

        Обязательно отписывайся от всех событий и освобождай ресурсы.
        Для отписки от всех событий сразу используй:
        ``self.app.event_bus.unsubscribe_all(callback)``
        """
        ...

    async def on_minimize(self) -> None:
        """Вызывается при сворачивании окна (для приостановки тяжёлых операций)."""
        ...

    async def on_restore(self) -> None:
        """Вызывается при разворачивании окна."""
        ...

    # ── Подписка ───────────────────────────────────────────────────

    def subscribe(self, event: str, callback) -> None:
        """Краткая форма: ``self.app.event_bus.subscribe(event, callback)``."""
        self.app.event_bus.subscribe(event, callback)

    def unsubscribe(self, event: str, callback) -> None:
        """Краткая форма: ``self.app.event_bus.unsubscribe(event, callback)``."""
        self.app.event_bus.unsubscribe(event, callback)

    def __repr__(self) -> str:
        return f"<Plugin {self.name!r} v{self.version}>"

    __str__ = __repr__
