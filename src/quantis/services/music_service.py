from __future__ import annotations

from quantis.providers import PathProvider
from quantis.services.async_downloader import AsyncDownloader
from quantis.services.async_finder import AsyncFinder
from quantis.services.async_recommendation import AsyncRecommendation
from quantis.services.async_streamer import AsyncStreamer


class MusicService:
    def __init__(
        self,
        finder: AsyncFinder | None = None,
        streamer: AsyncStreamer | None = None,
        downloader: AsyncDownloader | None = None,
        provider: PathProvider | None = None,
    ) -> None:
        self._finder = finder or AsyncFinder()
        self._streamer = streamer or AsyncStreamer()
        self._downloader = downloader or AsyncDownloader()
        self._provider = provider or PathProvider()
        self._recommendation = AsyncRecommendation(self._finder.youtube)

    @property
    def downloader(self) -> AsyncDownloader:
        return self._downloader

    @property
    def finder(self) -> AsyncFinder:
        return self._finder

    @property
    def recommendation(self) -> AsyncRecommendation:
        return self._recommendation

    @property
    def streamer(self) -> AsyncStreamer:
        return self._streamer

    @property
    def provider(self) -> PathProvider:
        return self._provider

    def shutdown(self) -> None:
        self._finder.shutdown()
        self._streamer.shutdown()
        self._downloader.shutdown()
