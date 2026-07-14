"""Инициализация клиентов:
- Яндекс Музыка
- YouTube Music
- Spotify (TODO) - приоритет
- SoundCloud (TODO)
- Vk Music (TODO)
"""

from __future__ import annotations

from keyring import get_password
from yandex_music import ClientAsync
from yandex_music.exceptions import NetworkError as NetworkErrorYandex
from yandex_music.exceptions import TimedOutError
from ytmusicapi import YTMusic
from ytmusicapi.exceptions import YTMusicError

from quantis.config.constants import (
    SERVICE_NAME_YANDEX,
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
        self._initialized = True

    def get_yandex_client(self) -> ClientAsync | None:
        return self._yandex

    def get_youtube_client(self) -> YTMusic:
        return self._youtube

    def reload_yandex_client(self) -> None:
        """Перечитать токен из keyring (после сохранения в настройках)."""
        self._yandex = self._init_yandex()

    def reload_youtube_client(self) -> None:
        """Перечитать cookie из keyring (после сохранения в настройках)."""
        self._youtube = self._init_youtube()

    @staticmethod
    def _init_yandex() -> ClientAsync | None:
        try:
            return ClientAsync(get_password(SERVICE_NAME_YANDEX, USER))
        except (TimedOutError, NetworkErrorYandex):
            return None

    @staticmethod
    def _init_youtube() -> YTMusic:
        from quantis.config.credentials import yotube_cookie

        cookie = yotube_cookie()
        if cookie:
            try:
                return YTMusic(auth=cookie, language="ru", location="")
            except (YTMusicError, ValueError, TypeError, OSError) as e:
                print(f"Ошибка инициализации YTMusic с auth: {e}")
            except Exception as e:
                # Битый JSON в credentials/youtube_cookies.txt не должен валить старт
                print(f"Ошибка инициализации YTMusic с auth: {e}")
        try:
            return YTMusic(language="ru", location="")
        except YTMusicError as e:
            print(f"Ошибка инициализации YTMusic: {e}")
            return YTMusic(language="ru", location="")
