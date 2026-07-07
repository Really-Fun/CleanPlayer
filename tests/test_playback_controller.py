"""Unit-тесты PlaybackController (без сети)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from quantis.controllers.playback_controller import PlaybackController
from quantis.models import YandexTrack
from quantis.plugins.event_bus import EventBus
from quantis.providers import PlaylistManager


@pytest.mark.asyncio
async def test_play_track_sets_current_and_emits_event() -> None:
    player = MagicMock()
    music = MagicMock()
    music.streamer.get_stream_url = AsyncMock(return_value="http://stream")
    music.provider.get_track_path = MagicMock(return_value="/path")
    event_bus = EventBus()
    bridge = MagicMock()

    emitted: list[object] = []
    event_bus.track_changed.connect(emitted.append)

    playback = PlaybackController(
        player=player,
        playlist_manager=PlaylistManager(),
        music_service=music,
        event_bus=event_bus,
        history=None,
        async_bridge=bridge,
    )

    track = YandexTrack(track_id="1", title="Song", author="Artist")
    await playback.play_track(track)

    bridge.invoke_main.assert_called_once()
    bridge.invoke_main.call_args[0][0]()

    assert playback.current_track is track
    assert player.current_track is track
    player.play.assert_called_once_with("http://stream")
    assert emitted == [track]
