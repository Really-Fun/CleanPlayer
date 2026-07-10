from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from quantis.core.async_bridge import AsyncBridge
from quantis.models.playlist import Playlist
from quantis.ui.async_ui import schedule
from quantis.ui.models import TrackListModel
from quantis.ui.preferences import UiPreferences
from quantis.ui.resources import THEME_EDITORIAL
from quantis.ui.viewmodels.home_vm import HomeViewModel
from quantis.ui.views.widgets.featured_track import FeaturedTrackPanel
from quantis.ui.views.widgets.home_section import HomeSection
from quantis.ui.views.widgets.playlist_card import PlaylistCard, QuickPickTile
from quantis.ui.views.widgets.track_card import TrackCardDelegate

_QUICK_COLS = 3
_LIBRARY_COLS = 4


class HomePage(QWidget):
    playlist_open_requested = Signal(object)

    def __init__(
        self,
        view_model: HomeViewModel,
        bridge: AsyncBridge | None = None,
        preferences: UiPreferences | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._vm = view_model
        self._bridge = bridge
        self._prefs = preferences or UiPreferences()
        self.setObjectName("homePage")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("homeScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("homeScrollContent")
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(16, 8, 16, 20)
        self._layout.setSpacing(20)

        self._greeting = QLabel()
        self._greeting.setObjectName("homeGreeting")
        self._layout.addWidget(self._greeting)

        self._greeting_sub = QLabel("Плейлисты, рекомендации и недавнее")
        self._greeting_sub.setObjectName("homeGreetingSub")
        self._layout.addWidget(self._greeting_sub)

        self._featured = FeaturedTrackPanel()
        self._featured.play_requested.connect(self._on_featured_play)
        self._layout.addWidget(self._featured)

        self._quick_section = HomeSection(
            "Быстрый доступ",
            "Нажми на плейлист, чтобы открыть",
        )
        self._quick_host = QWidget()
        self._quick_grid = QGridLayout(self._quick_host)
        self._quick_grid.setContentsMargins(0, 0, 0, 0)
        self._quick_grid.setHorizontalSpacing(12)
        self._quick_grid.setVerticalSpacing(12)
        self._quick_section.add_widget_block(self._quick_host)
        self._layout.addWidget(self._quick_section)

        self._library_section = HomeSection(
            "Ваша медиатека",
            "Недавние, скачанные и ваши плейлисты",
        )
        self._library_host = QWidget()
        self._library_grid = QGridLayout(self._library_host)
        self._library_grid.setContentsMargins(0, 0, 0, 0)
        self._library_grid.setHorizontalSpacing(12)
        self._library_grid.setVerticalSpacing(12)
        self._library_section.add_widget_block(self._library_host)
        self._layout.addWidget(self._library_section)

        self._recommend_section = HomeSection(
            "Рекомендуем послушать",
            "Подборка на основе недавних прослушиваний",
        )
        self._recommend_list = self._make_track_table(self._vm.recommendation_model)
        self._recommend_section.add_widget_block(self._recommend_list)
        self._layout.addWidget(self._recommend_section)

        self._recent_section = HomeSection("Недавно прослушанные")
        self._recent_list = self._make_track_table(
            self._vm.recent_model,
            on_download=self._on_download_recent,
        )
        self._recent_section.add_widget_block(self._recent_list)
        self._layout.addWidget(self._recent_section)

        self._layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

        self._vm.home_changed.connect(self._rebuild)
        self._vm.recent_changed.connect(self._on_recent_changed)
        self._prefs.changed.connect(self._apply_featured_visibility)
        self._apply_featured_visibility()

    def _make_track_table(
        self,
        model: TrackListModel,
        *,
        on_download=None,
    ) -> QTableView:
        table = QTableView()
        table.setObjectName("homeTrackList")
        table.setModel(model)
        table.verticalHeader().hide()
        table.horizontalHeader().hide()
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        table.verticalHeader().setDefaultSectionSize(TrackCardDelegate.CARD_HEIGHT)
        table.setShowGrid(False)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setItemDelegate(
            TrackCardDelegate(table, on_download=on_download),
        )
        table.setMouseTracking(True)
        table.viewport().setMouseTracking(True)
        table.doubleClicked.connect(
            lambda index, m=model: self._on_play_model(m, index.row()),
        )
        model.modelReset.connect(lambda: self._sync_table_height(table, model))
        model.rowsInserted.connect(lambda *_: self._sync_table_height(table, model))
        model.rowsRemoved.connect(lambda *_: self._sync_table_height(table, model))
        self._sync_table_height(table, model)
        return table

    @staticmethod
    def _sync_table_height(table: QTableView, model: TrackListModel) -> None:
        rows = model.rowCount()
        if rows <= 0:
            table.setFixedHeight(72)
            return
        height = min(rows * TrackCardDelegate.CARD_HEIGHT + 6, 420)
        table.setFixedHeight(max(height, TrackCardDelegate.CARD_HEIGHT + 6))

    def _clear_grid(self, grid: QGridLayout) -> None:
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _rebuild(self) -> None:
        snap = self._vm.snapshot
        self._greeting.setText(snap.greeting)

        self._clear_grid(self._quick_grid)
        for index, playlist in enumerate(snap.quick_playlists):
            tile = QuickPickTile(playlist)
            tile.activated.connect(self._on_playlist)
            row, col = divmod(index, _QUICK_COLS)
            self._quick_grid.addWidget(tile, row, col)

        self._clear_grid(self._library_grid)
        if not snap.library_playlists:
            empty = QLabel("Добавьте плейлисты в папку playlists/ или послушайте музыку")
            empty.setObjectName("homeEmptyHint")
            self._library_grid.addWidget(empty, 0, 0, 1, _LIBRARY_COLS)
        else:
            for index, playlist in enumerate(snap.library_playlists):
                card = PlaylistCard(playlist)
                card.activated.connect(self._on_playlist)
                row, col = divmod(index, _LIBRARY_COLS)
                self._library_grid.addWidget(card, row, col)

        rec_count = len(snap.recommendation_tracks)
        self._recommend_section.set_subtitle(
            f"{rec_count} треков" if rec_count else "Пока пусто — включи любой трек",
        )
        self._recent_section.set_subtitle(f"{len(snap.recent_tracks)} треков")
        self._sync_table_height(self._recommend_list, self._vm.recommendation_model)
        self._sync_table_height(self._recent_list, self._vm.recent_model)
        self._sync_featured()

    def _on_recent_changed(self) -> None:
        self._sync_table_height(self._recent_list, self._vm.recent_model)
        self._sync_featured()

    def _apply_featured_visibility(self) -> None:
        visible = (
            self._prefs.ui_theme == THEME_EDITORIAL
            or self._prefs.show_home_featured_panel
        )
        self._featured.setVisible(visible)
        if visible:
            self._sync_featured()

    def _sync_featured(self) -> None:
        if not self._featured.isVisible():
            return
        model = self._vm.recent_model
        if model.rowCount() == 0:
            self._featured.set_track(None)
            return
        track = model.data(model.index(0, 0), TrackListModel.TrackRole)
        playing = bool(model.data(model.index(0, 0), TrackListModel.IsPlayingRole))
        self._featured.set_track(track, 0, playing=playing)

    def _on_playlist(self, playlist: Playlist) -> None:
        self.playlist_open_requested.emit(playlist)

    def _on_play_model(self, model: TrackListModel, row: int) -> None:
        if self._bridge is None:
            return
        if model is self._vm.recent_model:
            schedule(self._vm.play_recent_at(row), self._bridge)
        else:
            schedule(self._vm.play_recommendation_at(row), self._bridge)

    def _on_featured_play(self, index: int) -> None:
        if self._bridge is not None:
            schedule(self._vm.play_recent_at(index), self._bridge)

    def _on_download_recent(self, row: int) -> None:
        if self._bridge is not None:
            schedule(self._vm.download_recent_at(row), self._bridge)

    def refresh_featured(self) -> None:
        self._sync_featured()
