from asyncio import AbstractEventLoop

from qasync import QEventLoop

from quantis.player import Player
from quantis.services import (
    AsyncDownloader,
    AsyncFinder,
    AsyncRecomendation,
    AsyncStreamer,
    TrackHistoryService,
)
from quantis.providers import PathProvider
from quantis.plugins import EventBus, PluginRegistry


class AppContext:

    def __init__(
        self,
        loop: AbstractEventLoop | QEventLoop,
        player: Player = None,
        async_finder: AsyncFinder = None,
        async_downloader: AsyncDownloader = None,
        async_recomendation: AsyncRecomendation = None,
        async_streamer: AsyncStreamer = None,
        path_provider: PathProvider = None,
        event_bus: EventBus = None,
        plugin_register: PluginRegistry = None,
        history_service: TrackHistoryService = None,
    ) -> None:
        self._player = player
        self._async_finder = async_finder
        self._async_downloader = async_downloader
        self._async_recomendation = async_recomendation
        self._async_streamer = async_streamer
        self._path_provider = path_provider
        self._loop = loop
        self._event_bus = event_bus
        self._plugin_registry = plugin_register
        self._history_service = history_service

    @property
    def player(self) -> Player:
        if self._player is None:
            self._player = Player(
                self.event_bus,
                self.path_provider,
                self.async_streamer,
                self.history_service,
                self.loop,
            )
        return self._player

    @property
    def async_finder(self) -> AsyncFinder:
        if self._async_finder is None:
            self._async_finder = AsyncFinder()
        return self._async_finder

    @property
    def async_downloader(self) -> AsyncDownloader:
        if self._async_downloader is None:
            self._async_downloader = AsyncDownloader()
        return self._async_downloader

    @property
    def async_recomendation(self) -> AsyncRecomendation:
        if self._async_recomendation is None:
            self._async_recomendation = AsyncRecomendation()
        return self._async_recomendation

    @property
    def async_streamer(self) -> AsyncStreamer:
        if self._async_streamer is None:
            self._async_streamer = AsyncStreamer()
        return self._async_streamer

    @property
    def path_provider(self) -> PathProvider:
        if self._path_provider is None:
            self._path_provider = PathProvider()
        return self._path_provider

    @property
    def event_bus(self) -> EventBus:
        if self._event_bus is None:
            self._event_bus = EventBus()
        return self._event_bus

    @property
    def plugin_registry(self) -> PluginRegistry:
        if self._plugin_registry is None:
            self._plugin_registry = PluginRegistry()
        return self._plugin_registry

    @property
    def loop(self) -> AbstractEventLoop | QEventLoop:
        return self._loop

    @property
    def history_service(self) -> TrackHistoryService:
        if self._history_service is None:
            self._history_service = TrackHistoryService()
        return self._history_service


def init_app_context(loop: AbstractEventLoop | QEventLoop) -> AppContext:
    """Инициализация контекста приложения

    Returns:
        AppContext:
    """
    return AppContext(
        loop=loop,
    )
