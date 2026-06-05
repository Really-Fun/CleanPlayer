"""Стек страниц приложения на основе инверсии управления."""

from __future__ import annotations

from typing import Callable
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget


class Stack(QWidget):
    """Виджет со стеком страниц с ленивой инициализацией через фабрики."""

    PAGE_HOME = "home"
    PAGE_SEARCH = "search"
    PAGE_PLAYLIST = "playlist"
    PAGE_SETTINGS = "settings"
    PAGE_USER = "user"
    PAGE_PLUGINS = "plugins"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._stack = QStackedWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

        # Фабрика теперь — это любая вызываемая функция/лямбда, возвращающая QWidget
        self._page_factories: dict[str, tuple[Callable[[], QWidget], str | None]] = {}
        self._page_ids: list[str] = []
        self._pages_cache: dict[str, QWidget] = {}

    def register_page(
            self,
            page_id: str,
            factory: Callable[[], QWidget],
            *,
            go_back: str | None = None,
    ) -> None:
        """Регистрирует рецепт (фабрику) для создания страницы."""
        if page_id in self._page_factories:
            raise ValueError(f"Страница '{page_id}' уже зарегистрирована")
        self._page_factories[page_id] = (factory, go_back)
        self._page_ids.append(page_id)
        self._stack.addWidget(QWidget())  # Создаем индексную заглушку

    def switch_to(self, page_id: str) -> None:
        """Переключает стек на нужную страницу, собирая её при необходимости."""
        index = self._index_of(page_id)
        self._get_page(page_id)
        self._stack.setCurrentIndex(index)

        # Триггеры обновления дефолтных страниц (если они уже созданы)
        if page_id == self.PAGE_HOME and self.PAGE_HOME in self._pages_cache:
            self.home_page.reload_system_playlists()
            self.home_page.reload_user_playlists()

    async def open_playlist(self, playlist) -> None:
        """Слот для открытия конкретного плейлиста."""
        self.switch_to(self.PAGE_PLAYLIST)
        await self.playlist_page.load_playlist(playlist)

    # ── Свойства страниц ──────────────────────────────────────────────────────

    @property
    def home_page(self) -> QWidget:
        return self._get_page(self.PAGE_HOME)

    @property
    def search_page(self) -> QWidget:
        return self._get_page(self.PAGE_SEARCH)

    @property
    def playlist_page(self) -> QWidget:
        return self._get_page(self.PAGE_PLAYLIST)

    @property
    def settings_page(self) -> QWidget:
        return self._get_page(self.PAGE_SETTINGS)

    @property
    def user_page(self) -> QWidget:
        return self._get_page(self.PAGE_USER)

    @property
    def plugins_page(self) -> QWidget:
        return self._get_page(self.PAGE_PLUGINS)

    # ── Внутренние методы ─────────────────────────────────────────────────────

    def _index_of(self, page_id: str) -> int:
        try:
            return self._page_ids.index(page_id)
        except ValueError:
            raise KeyError(f"Страница '{page_id}' не зарегистрирована") from None

    def _get_page(self, page_id: str) -> QWidget:
        """Возвращает готовый виджет страницы. Конструирует лениво."""
        if page_id in self._pages_cache:
            return self._pages_cache[page_id]

        factory, go_back = self._page_factories[page_id]

        # Вызов лямбды, переданной при регистрации. Сама фабрика знает свои зависимости!
        page = factory()

        if go_back is not None and hasattr(page, "go_back"):
            page.go_back.connect(lambda: self.switch_to(go_back))

        index = self._index_of(page_id)
        old_stub = self._stack.widget(index)

        self._stack.insertWidget(index, page)
        self._stack.removeWidget(old_stub)
        old_stub.deleteLater()

        self._pages_cache[page_id] = page
        return page