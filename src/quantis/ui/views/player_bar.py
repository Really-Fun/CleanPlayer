from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from quantis.providers.path_provider import PathProvider
from quantis.ui import resources
from quantis.ui.viewmodels.player_vm import PlayerViewModel


class PlayerBar(QFrame):
    """Нижняя панель плеера — карточка с отступами от краёв окна."""

    def __init__(
        self,
        view_model: PlayerViewModel,
        path_provider: PathProvider,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._vm = view_model
        self._path_provider = path_provider
        self._seeking = False
        self.setObjectName("playerDock")

        dock = QVBoxLayout(self)
        dock.setContentsMargins(14, 0, 14, 12)
        dock.setSpacing(0)

        card = QFrame()
        card.setObjectName("PlayMenu")
        card.setFixedHeight(84)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 10, 16, 10)
        card_layout.setSpacing(8)

        seek_row = QHBoxLayout()
        seek_row.setSpacing(10)
        self._elapsed = QLabel("0:00")
        self._elapsed.setObjectName("timeLabel")
        self._position = QSlider(Qt.Orientation.Horizontal)
        self._position.setObjectName("seekSlider")
        self._position.setRange(0, 0)
        self._position.sliderPressed.connect(self._on_seek_start)
        self._position.sliderReleased.connect(self._on_seek_end)
        self._duration_label = QLabel("0:00")
        self._duration_label.setObjectName("timeLabel")
        seek_row.addWidget(self._elapsed)
        seek_row.addWidget(self._position, stretch=1)
        seek_row.addWidget(self._duration_label)

        main_row = QHBoxLayout()
        main_row.setSpacing(16)

        meta_block = QHBoxLayout()
        meta_block.setSpacing(12)
        self._cover = QLabel()
        self._cover.setObjectName("coverLabel")
        self._cover.setFixedSize(48, 48)
        self._cover.setScaledContents(True)

        meta = QVBoxLayout()
        meta.setSpacing(1)
        meta.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._title = QLabel("Выберите трек")
        self._author = QLabel("")
        self._title.setObjectName("trackTitle")
        self._author.setObjectName("trackArtist")
        self._title.setMinimumWidth(120)
        meta.addWidget(self._title)
        meta.addWidget(self._author)
        meta_block.addWidget(self._cover)
        meta_block.addLayout(meta, stretch=1)

        transport = QHBoxLayout()
        transport.setSpacing(6)
        transport.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._prev_btn = self._make_button("prev.svg", "Назад", size=36)
        self._play_btn = self._make_button("play.svg", "Play", accent=True, size=46)
        self._next_btn = self._make_button("next.svg", "Далее", size=36)
        self._prev_btn.clicked.connect(self._vm.play_previous)
        self._play_btn.clicked.connect(self._vm.toggle_pause)
        self._next_btn.clicked.connect(self._vm.play_next)
        transport.addWidget(self._prev_btn)
        transport.addWidget(self._play_btn)
        transport.addWidget(self._next_btn)

        volume_row = QHBoxLayout()
        volume_row.setSpacing(8)
        volume_row.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._vol_label = QLabel("VOL")
        self._vol_label.setObjectName("volIcon")
        self._volume = QSlider(Qt.Orientation.Horizontal)
        self._volume.setObjectName("volSlider")
        self._volume.setFixedWidth(76)
        self._volume.setRange(0, 100)
        self._volume.valueChanged.connect(self._vm.set_volume)
        volume_row.addWidget(self._vol_label)
        volume_row.addWidget(self._volume)

        main_row.addLayout(meta_block, stretch=5)
        main_row.addLayout(transport, stretch=3)
        main_row.addLayout(volume_row, stretch=2)

        card_layout.addLayout(seek_row)
        card_layout.addLayout(main_row)
        dock.addWidget(card)

        self._vm.track_changed.connect(self._on_track_changed)
        self._vm.is_playing_changed.connect(self._on_playing_changed)
        self._vm.position_changed.connect(self._on_position_changed)
        self._vm.duration_changed.connect(self._on_duration_changed)

        self._volume.blockSignals(True)
        self._volume.setValue(80)
        self._volume.blockSignals(False)
        self._vm.set_volume(80)
        self._vm.sync_from_player()

    def _make_button(
        self,
        icon_name: str,
        tooltip: str,
        *,
        accent: bool = False,
        size: int = 36,
    ) -> QToolButton:
        button = QToolButton()
        button.setObjectName("controlButton")
        button.setProperty("accent", accent)
        icon_size = 22 if accent else 17
        button.setIcon(resources.load_icon(icon_name))
        button.setIconSize(QSize(icon_size, icon_size))
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedSize(size, size)
        self._repolish(button)
        return button

    @staticmethod
    def _repolish(widget: QWidget) -> None:
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()

    def _on_track_changed(self, track) -> None:
        self._title.setText(track.title)
        self._author.setText(track.author)
        cover_path = Path(self._path_provider.get_cover_path(track))
        if cover_path.is_file():
            pixmap = QPixmap(str(cover_path))
            self._cover.setPixmap(
                pixmap.scaled(
                    self._cover.size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self._cover.setPixmap(QPixmap())

    def _on_playing_changed(self, playing: bool) -> None:
        icon = "pause.svg" if playing else "play.svg"
        self._play_btn.setIcon(resources.load_icon(icon))

    def _on_position_changed(self, position_ms: int) -> None:
        self._elapsed.setText(resources.format_ms(position_ms))
        if not self._seeking:
            self._position.setValue(position_ms)

    def _on_duration_changed(self, duration_ms: int) -> None:
        self._duration_label.setText(resources.format_ms(duration_ms))
        self._position.setRange(0, max(0, duration_ms))

    def _on_seek_start(self) -> None:
        self._seeking = True

    def _on_seek_end(self) -> None:
        self._seeking = False
        self._vm.seek(self._position.value())

    def refresh_theme(self) -> None:
        """Переприменить QSS к кнопкам с динамическими свойствами."""
        for button in (self._prev_btn, self._play_btn, self._next_btn):
            self._repolish(button)
        card = self.findChild(QFrame, "PlayMenu")
        if card is not None:
            style = self.style()
            style.unpolish(card)
            style.polish(card)
            card.update()
        self.update()
