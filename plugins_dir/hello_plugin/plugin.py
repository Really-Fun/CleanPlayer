from __future__ import annotations

import logging

from quantis.models.track import 
from quantis.plugins.base import BasePlugiTrackn

logger = logging.getLogger(__name__)


class HelloPlugin(BasePlugin):
    """Пример плагина: пишет в лог при смене и окончании трека."""

    name = "Hello Plugin"
    version = "0.1.0"
    author = "Quantis"
    description = "Логирует воспроизведение в консоль"

    async def on_load(self) -> None:
        self.subscribe("track_changed", self._on_track_changed)
        self.subscribe("track_finished", self._on_track_finished)
        logger.info("Hello Plugin загружен")

    async def on_unload(self) -> None:
        self.unsubscribe("track_changed", self._on_track_changed)
        self.unsubscribe("track_finished", self._on_track_finished)
        logger.info("Hello Plugin выгружен")

    def _on_track_changed(self, track: Track) -> None:
        logger.info("▶ %s — %s", track.author, track.title)

    def _on_track_finished(self) -> None:
        logger.info("✓ Трек доигран до конца")
