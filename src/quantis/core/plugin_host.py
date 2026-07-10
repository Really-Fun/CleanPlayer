"""Узкий контракт для плагинов (без God Object)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quantis.controllers.playback_controller import PlaybackController
    from quantis.core.async_bridge import AsyncBridge
    from quantis.plugins.event_bus import EventBus
    from quantis.services.music_service import MusicService


@dataclass
class PluginHost:
    event_bus: EventBus
    playback: PlaybackController
    music: MusicService
    async_bridge: AsyncBridge | None = None
