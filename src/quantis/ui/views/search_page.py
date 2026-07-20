from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableView,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from quantis.core.async_bridge import AsyncBridge
from quantis.ui.async_ui import schedule
from quantis.ui.viewmodels.search_vm import SearchViewModel
from quantis.ui.views.widgets.glass_panel import GlassPanel
from quantis.ui.views.widgets.track_card import TrackCardDelegate


class SearchPage(QWidget):
    def __init__(
        self,
        view_model: SearchViewModel,
        bridge: AsyncBridge | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._vm = view_model
        self._bridge = bridge
        self.setObjectName("searchPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 12)
        layout.setSpacing(0)

        panel = GlassPanel()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 18, 20, 16)
        panel_layout.setSpacing(10)

        self._query = QLineEdit()
        self._query.setObjectName("searchInput")
        self._query.setPlaceholderText("Трек, артист или альбом…")
        self._query.setClearButtonEnabled(True)
        self._query.textChanged.connect(self._vm.search)
        self._query.returnPressed.connect(self._vm.search_now)
        panel_layout.addWidget(self._query)

        filters = QHBoxLayout()
        filters.setSpacing(8)
        self._filter_group = QButtonGroup(self)
        self._filter_group.setExclusive(True)
        for key, label in (
            ("all", "Все"),
            ("yandex", "Яндекс"),
            ("youtube", "YouTube"),
        ):
            chip = QToolButton()
            chip.setObjectName("sourceFilterChip")
            chip.setText(label)
            chip.setCheckable(True)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setProperty("filterKey", key)
            if key == "all":
                chip.setChecked(True)
            self._filter_group.addButton(chip)
            filters.addWidget(chip)
            chip.clicked.connect(lambda checked=False, k=key: self._vm.set_source_filter(k))
        filters.addStretch()
        panel_layout.addLayout(filters)

        self._status = QLabel("")
        self._status.setObjectName("searchStatus")
        panel_layout.addWidget(self._status)

        self._list = QTableView()
        self._list.setObjectName("trackList")
        self._list.setModel(self._vm.model)
        self._list.verticalHeader().hide()
        self._list.horizontalHeader().hide()
        self._list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._list.verticalHeader().setDefaultSectionSize(TrackCardDelegate.CARD_HEIGHT)
        self._list.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self._list.setShowGrid(False)
        self._list.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._list.setItemDelegate(
            TrackCardDelegate(self._list, on_download=self._on_download)
        )
        self._list.setMouseTracking(True)
        self._list.viewport().setMouseTracking(True)
        self._list.doubleClicked.connect(self._on_play_index)
        panel_layout.addWidget(self._list, stretch=1)

        layout.addWidget(panel, stretch=1)

        self._vm.loading_changed.connect(self._on_loading)
        self._vm.error_occurred.connect(self._on_error)
        self._vm.results_changed.connect(self._on_results)
        self._vm.status_message.connect(self._status.setText)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._query.setFocus(Qt.FocusReason.OtherFocusReason)
        if self._query.text().strip():
            self._vm.search_now()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._list.doItemsLayout()

    def _on_loading(self, loading: bool) -> None:
        if loading and not self._status.text():
            self._status.setText("Ищем…")

    def _on_error(self, message: str) -> None:
        self._status.setText(message)

    def _on_results(self) -> None:
        self._list.scheduleDelayedItemsLayout()
        self._list.viewport().update()

    def _on_play_index(self, index) -> None:
        if self._bridge is not None:
            schedule(self._vm.play_track_at(index.row()), self._bridge)

    def _on_download(self, row: int) -> None:
        if self._bridge is not None:
            schedule(self._vm.download_track_at(row), self._bridge)
