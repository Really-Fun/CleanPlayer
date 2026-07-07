from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QHBoxLayout,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from quantis.core.async_bridge import AsyncBridge
from quantis.ui.async_ui import schedule
from quantis.ui.models import TrackListModel
from quantis.ui.preferences import UiPreferences
from quantis.ui.resources import THEME_EDITORIAL
from quantis.ui.viewmodels.home_vm import HomeViewModel
from quantis.ui.views.widgets.featured_track import FeaturedTrackPanel
from quantis.ui.views.widgets.glass_panel import GlassPanel
from quantis.ui.views.widgets.track_card import TrackCardDelegate


class HomePage(QWidget):
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

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 8, 16, 12)
        root.setSpacing(12)

        self._featured = FeaturedTrackPanel()
        self._featured.play_requested.connect(self._on_featured_play)

        panel = GlassPanel()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 18, 20, 16)
        panel_layout.setSpacing(10)

        title = QLabel("Недавно")
        title.setObjectName("sectionTitle")
        panel_layout.addWidget(title)

        self._recent_list = QTableView()
        self._recent_list.setObjectName("trackList")
        self._recent_list.setModel(self._vm.recent_model)
        self._recent_list.verticalHeader().hide()
        self._recent_list.horizontalHeader().hide()
        self._recent_list.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._recent_list.setShowGrid(False)
        self._recent_list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._recent_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._recent_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._recent_list.setItemDelegate(
            TrackCardDelegate(self._recent_list, on_download=self._on_download_recent)
        )
        self._recent_list.setMouseTracking(True)
        self._recent_list.viewport().setMouseTracking(True)
        self._recent_list.doubleClicked.connect(self._on_recent_play)
        self._recent_list.clicked.connect(self._on_row_clicked)
        panel_layout.addWidget(self._recent_list, stretch=1)

        root.addWidget(self._featured, stretch=0)
        root.addWidget(panel, stretch=1)

        self._vm.recent_changed.connect(self._sync_featured)
        self._prefs.changed.connect(self._apply_featured_visibility)
        self._apply_featured_visibility()
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
        if not (
            self._prefs.ui_theme == THEME_EDITORIAL
            or self._prefs.show_home_featured_panel
        ):
            return
        model = self._vm.recent_model
        if model.rowCount() == 0:
            self._featured.set_track(None)
            return
        track = model.data(model.index(0, 0), TrackListModel.TrackRole)
        playing = bool(model.data(model.index(0, 0), TrackListModel.IsPlayingRole))
        self._featured.set_track(track, 0, playing=playing)

    def _on_row_clicked(self, index) -> None:
        if not (
            self._prefs.ui_theme == THEME_EDITORIAL
            or self._prefs.show_home_featured_panel
        ):
            return
        track = self._vm.recent_model.get_track(index.row())
        playing = bool(
            self._vm.recent_model.data(index, TrackListModel.IsPlayingRole)
        )
        self._featured.set_track(track, index.row(), playing=playing)

    def _on_featured_play(self, index: int) -> None:
        if self._bridge is not None:
            schedule(self._vm.play_recent_at(index), self._bridge)

    def _on_recent_play(self, index) -> None:
        if self._bridge is not None:
            schedule(self._vm.play_recent_at(index.row()), self._bridge)

    def _on_download_recent(self, row: int) -> None:
        if self._bridge is not None:
            schedule(self._vm.download_recent_at(row), self._bridge)

    def refresh_featured(self) -> None:
        self._sync_featured()
