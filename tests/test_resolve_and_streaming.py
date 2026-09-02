"""Unit-тесты resolve_tracks и VLC routing."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from quantis.models import YandexTrack, YoutubeTrack
from quantis.services.async_finder import AsyncFinder
from quantis.services.async_streamer import AsyncStreamer


@pytest.mark.asyncio
async def test_resolve_tracks_yandex_url() -> None:
    finder = AsyncFinder()
    track = YandexTrack(track_id="123", title="T", author="A")

    with patch.object(
        finder._yandex_finder, "get_track", new_callable=AsyncMock, return_value=track
    ) as yandex_mock:
        result = await finder.resolve_tracks(
            url="https://music.yandex.ru/album/1/track/123"
        )

    assert result == [track]
    yandex_mock.assert_awaited_once_with("123")
    finder.shutdown()


@pytest.mark.asyncio
async def test_resolve_tracks_youtube_url() -> None:
    finder = AsyncFinder()
    video_id = "dQw4w9WgXcQ"
    track = YoutubeTrack(track_id=video_id, title="T", author="A")

    with patch.object(
        finder._youtube_finder,
        "get_track_from_url",
        new_callable=AsyncMock,
        return_value=track,
    ) as yt_mock:
        result = await finder.resolve_tracks(
            url=f"https://www.youtube.com/watch?v={video_id}"
        )

    assert result == [track]
    yt_mock.assert_awaited_once()
    finder.shutdown()


@pytest.mark.asyncio
async def test_resolve_tracks_by_id_and_source() -> None:
    finder = AsyncFinder()
    track = YoutubeTrack(track_id="abc", title="T", author="A")

    with patch.object(
        finder._youtube_finder, "get_track", new_callable=AsyncMock, return_value=track
    ) as yt_mock:
        result = await finder.resolve_tracks(track_id="abc", source="youtube")

    assert result == [track]
    yt_mock.assert_awaited_once_with("abc")
    finder.shutdown()


@pytest.mark.asyncio
async def test_open_playback_yandex_uses_progressive_buffer() -> None:
    streamer = AsyncStreamer()
    track = YandexTrack(track_id="1", title="T", author="A")

    with (
        patch.object(
            streamer._stream_buffer,
            "open",
            new_callable=AsyncMock,
            return_value="/tmp/quantis_stream/yandex_1.mp3",
        ) as buffer_mock,
        patch.object(streamer._stream_buffer, "cleanup_old_files"),
        patch.object(streamer, "get_stream_url", new_callable=AsyncMock) as url_mock,
    ):
        result = await streamer.open_playback(track)

    assert result == "/tmp/quantis_stream/yandex_1.mp3"
    buffer_mock.assert_awaited_once_with(track)
    url_mock.assert_not_awaited()
    streamer.shutdown()


@pytest.mark.asyncio
async def test_open_playback_youtube_uses_progressive_buffer() -> None:
    streamer = AsyncStreamer()
    track = YoutubeTrack(track_id="abc123", title="T", author="A")

    with (
        patch.object(
            streamer._stream_buffer,
            "open",
            new_callable=AsyncMock,
            return_value="/tmp/quantis_stream/youtube_abc123.m4a",
        ) as buffer_mock,
        patch.object(streamer._stream_buffer, "cleanup_old_files"),
        patch.object(streamer, "get_stream_url", new_callable=AsyncMock) as url_mock,
    ):
        result = await streamer.open_playback(track)

    assert result == "/tmp/quantis_stream/youtube_abc123.m4a"
    buffer_mock.assert_awaited_once_with(track)
    url_mock.assert_not_awaited()
    streamer.shutdown()


@pytest.mark.asyncio
async def test_open_playback_qt_yandex_uses_buffer() -> None:
    streamer = AsyncStreamer()
    track = YandexTrack(track_id="1", title="T", author="A")

    with (
        patch("quantis.config.media_backend.resolve_media_backend", return_value="qt"),
        patch.object(
            streamer._stream_buffer,
            "open",
            new_callable=AsyncMock,
            return_value="/tmp/quantis_stream/yandex_1.mp3",
        ) as buffer_mock,
        patch.object(streamer._stream_buffer, "cleanup_old_files"),
        patch.object(streamer, "get_stream_url", new_callable=AsyncMock) as url_mock,
    ):
        result = await streamer.open_playback(track)

    assert result == "/tmp/quantis_stream/yandex_1.mp3"
    buffer_mock.assert_awaited_once_with(track)
    url_mock.assert_not_awaited()
    streamer.shutdown()
