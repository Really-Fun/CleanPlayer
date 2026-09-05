"""Тесты восстановления потока при зависании."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from quantis.controllers.playback_controller import PlaybackController
from quantis.models import YandexTrack
from quantis.plugins.event_bus import EventBus
from quantis.providers import PlaylistManager


@pytest.mark.asyncio
async def test_recover_playback_refreshes_source_and_seeks() -> None:
    player = MagicMock()
    player.time = 42_000
    player.current_source = "https://cdn.example/old"

    music = MagicMock()
    music.streamer.invalidate = MagicMock()
    music.streamer.open_playback = AsyncMock(
        return_value="/tmp/quantis_stream/yandex_1.mp3"
    )

    bridge = MagicMock()
    playback = PlaybackController(
        player=player,
        playlist_manager=PlaylistManager(),
        music_service=music,
        event_bus=EventBus(),
        async_bridge=bridge,
    )
    track = YandexTrack(track_id="1", title="Song", author="Artist")
    playback._current_track = track

    await playback.recover_playback(42_000, reason="stall")

    music.streamer.invalidate.assert_called_once_with(track)
    music.streamer.open_playback.assert_awaited_once_with(track)
    bridge.invoke_main.assert_called_once()
    bridge.invoke_main.call_args[0][0]()
    player.play.assert_called_once_with(
        "/tmp/quantis_stream/yandex_1.mp3",
        start_ms=42_000,
    )


@pytest.mark.asyncio
async def test_handle_stream_error_uses_paused_position() -> None:
    player = MagicMock()
    player.time = 0
    player.paused_at_ms = 42_000
    player.current_source = "https://cdn.example/old"

    playback = PlaybackController(
        player=player,
        playlist_manager=PlaylistManager(),
        music_service=MagicMock(),
        event_bus=EventBus(),
        async_bridge=MagicMock(),
    )
    playback.request_playback_recovery = MagicMock()  # type: ignore[method-assign]

    playback.handle_stream_error("resume-after-pause")

    playback.request_playback_recovery.assert_called_once_with(
        42_000,
        reason="resume-after-pause",
    )
