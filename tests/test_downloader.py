"""Тесты форматов скачивания YouTube."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from quantis.models import YoutubeTrack
from quantis.services.async_downloader import (
    _AUDIO_FORMAT,
    _VIDEO_FORMAT,
    AsyncYoutubeDownloader,
)


def test_audio_format_prefers_m4a_mp3() -> None:
    assert "m4a" in _AUDIO_FORMAT
    assert "mp3" in _AUDIO_FORMAT
    assert "mp4" not in _AUDIO_FORMAT


def test_video_format_is_mp4() -> None:
    assert "mp4" in _VIDEO_FORMAT


@pytest.mark.asyncio
async def test_download_track_skips_video_when_wallpaper_off() -> None:
    downloader = AsyncYoutubeDownloader()

    with (
        patch.object(downloader, "_download_audio", return_value=True) as audio_mock,
        patch.object(downloader, "_download_video_cache") as video_mock,
        patch.object(downloader, "_video_wallpaper_enabled", return_value=False),
    ):
        track = YoutubeTrack(track_id="vid", title="T", author="A")
        await downloader.download_track(track)

    audio_mock.assert_awaited_once()
    video_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_download_track_fetches_video_cache_when_wallpaper_on() -> None:
    downloader = AsyncYoutubeDownloader()

    with (
        patch.object(downloader, "_download_audio", return_value=True) as audio_mock,
        patch.object(downloader, "_download_video_cache") as video_mock,
        patch.object(downloader, "_video_wallpaper_enabled", return_value=True),
    ):
        track = YoutubeTrack(track_id="vid", title="T", author="A")
        await downloader.download_track(track)

    audio_mock.assert_awaited_once()
    video_mock.assert_awaited_once()
