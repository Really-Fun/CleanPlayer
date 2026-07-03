import asyncio

import pytest

from quantis.models import Track, YandexTrack, YoutubeTrack
from quantis.services import AsyncFinder, AsyncDownloader, AsyncStreamer

pytestmark = pytest.mark.asyncio

@pytest.mark.network
async def test_find_track_from_yandex():
    finder = AsyncFinder()
    
    tracks = await finder.get_tracks("Intro alt-j", value=1)
    assert isinstance(tracks, list)
    assert len(tracks) == 1
    
    track = tracks[0]
    assert isinstance(track, YandexTrack)
    assert track.title == "Intro", f"Неожиданное название трека: {track.title}"
    assert track.author == "alt-J", f"Неожиданный автор трека: {track.author}"
    
@pytest.mark.network
async def test_find_track_from_youtube():
    finder = AsyncFinder()
    
    tracks = await finder.get_tracks("Intro alt-j", value=1)
    assert isinstance(tracks, list)
    assert len(tracks) == 1
    
    track = tracks[0]
    assert isinstance(track, YoutubeTrack)
    assert track.title == "Intro", f"Неожиданное название трека: {track.title}"
    assert track.author == "alt-J", f"Неожиданный автор трека: {track.author}"