"""Стек страниц приложения.

Переключение между страницами происходит через строковые ID (`page_id`).
Встроенные страницы зарегистрированы в `__init__` через `register_page()`.
Плагины могут добавлять свои страницы, вызывая тот же метод.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

# Импортируем наш единый контекст
from quantis.core import AppContext

from quantis.ui.HomePage import HomePage
from quantis.ui.PlaylistPage import PlaylistPage
from quantis.ui.SearchPage import SearchPage
from quantis.ui.SettingsPage import SettingsPage
from quantis.ui.UserPage import UserPage
from quantis.ui.PluginsManagerPage import PluginsManagerPage

if TYPE_CHECKING:
    pass


class Stack(QWidget):
    """Виджет со стеком страниц."""

    PAGE_HOME = "home"
    PAGE_SEARCH = "search"
    PAGE_PLAYLIST = "playlist"
    PAGE_SETTINGS = "settings"
    PAGE_USER = "user"
    PAGE_PLUGINS = "plugins"

    # 1. ПРИНИМАЕМ КОНТЕКСТ В __init__
    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(parent)
        self.context = context

        self._stack = QStackedWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

        self._page_factories: dict[str, tuple[type[QWidget], str | None]] = {}
        self._page_ids: list[str] = []
        self._pages_cache: dict[str, QWidget] = {}

        # Регистрация встроенных страниц
        self.register_page(self.PAGE_HOME, HomePage)
        self.register_page(self.PAGE_SEARCH, SearchPage)
        self.register_page(self.PAGE_PLAYLIST, PlaylistPage, go_back=self.PAGE_HOME)
        self.register_page(self.PAGE_SETTINGS, SettingsPage, go_back=self.PAGE_HOME)
        self.register_page(self.PAGE_USER, UserPage, go_back=self.PAGE_HOME)
        self.register_page(self.PAGE_PLUGINS, PluginsManagerPage)

        self.switch_to(self.PAGE_HOME)

    # ── Публичный API (остается без изменений) ────────────────────────────────

    def register_page(
        self,
        page_id: str,
        factory: type[QWidget],
        *,
        go_back: str | None = None,
    ) -> None:
        if page_id in self._page_factories:
            raise ValueError(f"Страница '{page_id}' уже зарегистрирована")
        self._page_factories[page_id] = (factory, go_back)
        self._page_ids.append(page_id)
        self._stack.addWidget(QWidget())

    def switch_to(self, page_id: str) -> None:
        index = self._index_of(page_id)
        self._get_page(page_id)
        self._stack.setCurrentIndex(index)

        if page_id == self.PAGE_HOME:
            self.home_page.reload_system_playlists()
            self.home_page.reload_user_playlists()

    async def open_playlist(self, playlist) -> None:
        self.switch_to(self.PAGE_PLAYLIST)
        await self.playlist_page.load_playlist(playlist)

    # ... (properties остаются без изменений) ...

    @property
    def home_page(self) -> HomePage:
        return self._get_page(self.PAGE_HOME)  # type: ignore[return-value]

    @property
    def search_page(self) -> SearchPage:
        return self._get_page(self.PAGE_SEARCH)  # type: ignore[return-value]

    @property
    def playlist_page(self) -> PlaylistPage:
        return self._get_page(self.PAGE_PLAYLIST)  # type: ignore[return-value]

    @property
    def settings_page(self) -> SettingsPage:
        return self._get_page(self.PAGE_SETTINGS)  # type: ignore[return-value]

    @property
    def user_page(self) -> UserPage:
        return self._get_page(self.PAGE_USER)  # type: ignore[return-value]

    @property
    def plugins_page(self) -> PluginsManagerPage:
        return self._get_page(self.PAGE_PLUGINS)  # type: ignore[return-value]

    # ── Внутренние методы ─────────────────────────────────────────────────────

    def _index_of(self, page_id: str) -> int:
        try:
            return self._page_ids.index(page_id)
        except ValueError:
            raise KeyError(f"Страница '{page_id}' не зарегистрирована") from None

    def _get_page(self, page_id: str) -> QWidget:
        """Возвращает виджет страницы, создавая его при первом обращении."""
        if page_id in self._pages_cache:
            return self._pages_cache[page_id]

        factory, go_back = self._page_factories[page_id]

        page = factory(self.context, self)

        if go_back is not None and hasattr(page, "go_back"):
            page.go_back.connect(lambda: self.switch_to(go_back))

        index = self._index_of(page_id)
        old = self._stack.widget(index)
        self._stack.insertWidget(index, page)
        self._stack.removeWidget(old)
        old.deleteLater()

        self._pages_cache[page_id] = page
        return page
