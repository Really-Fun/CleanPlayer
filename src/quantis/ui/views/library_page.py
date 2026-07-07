from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from quantis.core.async_bridge import AsyncBridge
from quantis.ui.async_ui import schedule
from quantis.ui.viewmodels.home_vm import HomeViewModel
from quantis.ui.views.widgets.glass_panel import GlassPanel
from quantis.ui.views.widgets.track_card import TrackCardDelegate


class LibraryPage(QWidget):
    def __init__(
        self,
        view_model: HomeViewModel,
        bridge: AsyncBridge | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._vm = view_model
        self._bridge = bridge
        self.setObjectName("libraryPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 12)

        panel = GlassPanel()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 18, 20, 16)
        panel_layout.setSpacing(10)

        panel_layout.addWidget(QLabel("Скачанные", objectName="sectionTitle"))

        self._list = QTableView()
        self._list.setObjectName("trackList")
        self._list.setModel(self._vm.downloaded_model)
        self._list.verticalHeader().hide()
        self._list.horizontalHeader().hide()
        self._list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._list.setShowGrid(False)
        self._list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._list.setItemDelegate(TrackCardDelegate(self._list))
        self._list.setMouseTracking(True)
        self._list.viewport().setMouseTracking(True)
        self._list.doubleClicked.connect(self._on_play)
        panel_layout.addWidget(self._list, stretch=1)

        layout.addWidget(panel, stretch=1)

    def _on_play(self, index) -> None:
        if self._bridge is not None:
            schedule(self._vm.play_downloaded_at(index.row()), self._bridge)

    def set_playing_track(self, track) -> None:
        self._vm.downloaded_model.set_playing_track(track)
