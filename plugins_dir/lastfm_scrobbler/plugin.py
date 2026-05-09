"""Discord NetRunner — демонстрационный плагин Quantis.

Подписывается на ``track_changed`` и отправляет данные в Discord о смене трека:
- «Now Playing» при смене трека

Требования:
- Установленный и запущенный клиент Discord
"""

from __future__ import annotations

import asyncio
import logging
import time
from pypresence import Presence
from pypresence.exceptions import DiscordNotFound

from plugins.base import BasePlugin
from core import AppContext

logger = logging.getLogger(__name__)

CLIENT_ID = "1501512315500232724"


class DiscordNetRunner(BasePlugin):
    """Дискорд RPC"""

    name = "Discord NetRunner - информация о треках в Дискорд"
    version = "0.0.1"
    author = "Really-Fun"
    description = "Отправляет Now Playing при смене треков"
    icon = ""

    def __init__(self, app_context: AppContext, settings) -> None:
        super().__init__(app_context)
        self._track_start_time: float | None = None
        self._current_track = None

        self._rpc = Presence(CLIENT_ID)
        self._is_connected = False
        self.context = app_context

    async def on_load(self) -> None:
        self.context.event_bus.track_changed.connect(self._on_track_changed)
        self.context.event_bus.track_finished.connect(self._on_track_finished)
        self.context.event_bus.playback_paused.connect(self._on_paused)

        try:
            await asyncio.to_thread(self._rpc.connect)
            self._is_connected = True
            logger.info("[Discord NetRunner] Успешное подключение к Discord IPC!")
        except DiscordNotFound:
            logger.warning("[Discord NetRunner] Discord не запущен. RPC отключен.")
        except Exception as e:
            logger.error(f"[Discord NetRunner] Ошибка подключения: {e}")

    async def on_unload(self) -> None:
        self.unsubscribe("track_changed", self._on_track_changed)
        self.unsubscribe("track_finished", self._on_track_finished)
        self.unsubscribe("playback_paused", self._on_paused)

        if self._is_connected:
            await asyncio.to_thread(self._rpc.close)
            self._is_connected = False

        logger.info("[Discord NetRunner] Плагин выгружен")

    def _on_track_changed(self, track) -> None:
        """При смене трека — обновляем статус в Discord."""
        self._current_track = track
        self._track_start_time = time.time()

        if not self._is_connected:
            return

        try:
            self._rpc.update(
                state="Quantis",
                details=f"Текущий трек: {track.title.capitalize()} - {track.author.capitalize()}",
                start=int(self._track_start_time),
            )
            logger.info(f"[Discord NetRunner] Статус обновлен: {track}")
        except Exception as e:
            logger.error(f"[Discord NetRunner] Не удалось обновить статус: {e}")

    def _on_track_finished(self) -> None: ...

    def _on_paused(self) -> None:
        self._track_start_time = None

        if not self._is_connected:
            return

        try:
            self._rpc.update(
                state="На паузе",
                details=(
                    f"Трек: {self._current_track}"
                    if self._current_track
                    else "Ничего не играет"
                ),
                small_image="play_icon",
                small_text="Воспроизвести",
            )
        except Exception as e:
            logger.error(f"[Discord NetRunner] Ошибка при паузе: {e}")
