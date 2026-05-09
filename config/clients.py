"""Инициализация клиентов:
- Яндекс Музыка
- YouTube Music
- Last.fm
- Spotify (TODO) - приоритет
- SoundCloud (TODO)
- Vk Music (TODO)
"""

from __future__ import annotations

from yandex_music import ClientAsync
from yandex_music.exceptions import TimedOutError, NetworkError as NetworkErrorYandex
from pylast import WSError, NetworkError as NetworkErrorLastFm, LastFMNetwork
from ytmusicapi import YTMusic
from keyring import get_password

from config.constants import (
    SERVICE_NAME_YANDEX,
    SERVICE_NAME_LASTFM_API,
    SERVICE_NAME_LASTFM_SECRET,
    USER,
)


class Clients:
    """Singleton-фабрика клиентов внешних сервисов.

    Клиенты инициализируются **один раз** при первом создании экземпляра.
    Все последующие ``Clients()`` возвращают тот же объект без повторной инициализации.
    """

    _instance: Clients | None = None
    _initialized: bool = False

    def __new__(cls) -> Clients:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._yandex = self._init_yandex()
        self._youtube = self._init_youtube()
        self._lastfm  = self._init_lastfm()
        self._initialized = True

    def get_yandex_client(self) -> ClientAsync | None:
        return self._yandex

    def get_youtube_client(self) -> YTMusic:
        return self._youtube

    def get_lastfm_client(self) -> LastFMNetwork | None:
        return self._lastfm

    @staticmethod
    def _init_yandex() -> ClientAsync | None:
        try:
            return ClientAsync(get_password(SERVICE_NAME_YANDEX, USER))
        except (TimedOutError, NetworkErrorYandex):
            return None

    @staticmethod
    def _init_youtube() -> YTMusic:
        return YTMusic(language="ru", location="")

    @staticmethod
    def _init_lastfm() -> LastFMNetwork | None:
        api_key    = get_password(SERVICE_NAME_LASTFM_API, USER)
        api_secret = get_password(SERVICE_NAME_LASTFM_SECRET, USER)
        if api_key is None or api_secret is None:
            return None
        try:
            return LastFMNetwork(api_key, api_secret)
        except (WSError, NetworkErrorLastFm):
            return None