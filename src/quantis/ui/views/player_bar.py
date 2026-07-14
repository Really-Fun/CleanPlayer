from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from quantis.core.async_bridge import AsyncBridge
from quantis.models.track import Track
from quantis.providers.path_provider import PathProvider
from quantis.services.liked_tracks import LikedTracksService
from quantis.services.music_service import MusicService
from quantis.ui import resources
from quantis.ui.cover_prefetch import schedule_cover_prefetch
from quantis.ui.viewmodels.player_vm import PlayerViewModel
from quantis.ui.views.widgets.cover_art import load_cover_pixmap


class PlayerBar(QFrame):
    """Нижняя панель плеера — трёхколоночная сетка, seek сверху."""

    def __init__(
        self,
        view_model: PlayerViewModel,
        path_provider: PathProvider,
        *,
        bridge: AsyncBridge | None = None,
        music: MusicService | None = None,
        on_liked_changed: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._vm = view_model
        self._path_provider = path_provider
        self._bridge = bridge
        self._music = music
        self._liked = LikedTracksService()
        self._on_liked_changed = on_liked_changed
        self._current_track: Track | None = None
        self._seeking = False
        self._is_playing = False
        self._track_liked = False
        self.setObjectName("playerDock")

        dock = QVBoxLayout(self)
        dock.setContentsMargins(12, 4, 12, 14)
        dock.setSpacing(0)

        card = QFrame()
        card.setObjectName("PlayMenu")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 12, 18, 12)
        card_layout.setSpacing(10)

        seek_row = QHBoxLayout()
        seek_row.setSpacing(10)
        self._elapsed = QLabel("0:00")
        self._elapsed.setObjectName("timeLabel")
        self._elapsed.setFixedWidth(38)
        self._elapsed.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._position = QSlider(Qt.Orientation.Horizontal)
        self._position.setObjectName("seekSlider")
        self._position.setRange(0, 0)
        self._position.setFixedHeight(14)
        self._position.sliderPressed.connect(self._on_seek_start)
        self._position.sliderReleased.connect(self._on_seek_end)
        self._duration_label = QLabel("0:00")
        self._duration_label.setObjectName("timeLabel")
        self._duration_label.setFixedWidth(38)
        self._duration_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        seek_row.addWidget(self._elapsed)
        seek_row.addWidget(self._position, stretch=1)
        seek_row.addWidget(self._duration_label)

        divider = QFrame()
        divider.setObjectName("playerInnerDivider")
        divider.setFixedHeight(1)

        self._cover = QLabel()
        self._cover.setObjectName("coverLabel")
        self._cover.setFixedSize(52, 52)
        self._cover.setScaledContents(True)

        meta = QVBoxLayout()
        meta.setSpacing(2)
        meta.setContentsMargins(0, 0, 0, 0)
        meta.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self._title = QLabel("Выберите трек")
        self._author = QLabel("")
        self._title.setObjectName("trackTitle")
        self._author.setObjectName("trackArtist")
        self._title.setMaximumWidth(320)
        self._author.setMaximumWidth(320)
        meta.addWidget(self._title)
        meta.addWidget(self._author)

        self._like_btn = self._make_button("heart.svg", "В любимые", size=32)
        self._like_btn.clicked.connect(self._on_like_clicked)

        left = QWidget()
        left.setObjectName("playerLeft")
        left_layout = QHBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        left_layout.addWidget(self._cover)
        left_layout.addLayout(meta, stretch=1)
        left_layout.addWidget(self._like_btn)

        self._prev_btn = self._make_button("prev.svg", "Назад", size=34)
        self._play_btn = self._make_button("play.svg", "Play", accent=True, size=44)
        self._next_btn = self._make_button("next.svg", "Далее", size=34)
        self._prev_btn.clicked.connect(self._vm.play_previous)
        self._play_btn.clicked.connect(self._vm.toggle_pause)
        self._next_btn.clicked.connect(self._vm.play_next)

        center = QWidget()
        center.setObjectName("playerCenter")
        center_layout = QHBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self._prev_btn)
        center_layout.addWidget(self._play_btn)
        center_layout.addWidget(self._next_btn)

        self._volume = QSlider(Qt.Orientation.Horizontal)
        self._volume.setObjectName("volSlider")
        self._volume.setFixedWidth(84)
        self._volume.setRange(0, 100)
        self._volume.valueChanged.connect(self._vm.set_volume)

        right = QWidget()
        right.setObjectName("playerRight")
        right_layout = QHBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        right_layout.addWidget(self._volume)

        body = QGridLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setHorizontalSpacing(12)
        body.setColumnStretch(0, 1)
        body.setColumnStretch(1, 0)
        body.setColumnStretch(2, 1)
        body.addWidget(
            left, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        body.addWidget(center, 0, 1, Qt.AlignmentFlag.AlignCenter)
        body.addWidget(
            right, 0, 2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        card_layout.addLayout(seek_row)
        card_layout.addWidget(divider)
        card_layout.addLayout(body)
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
        self._update_like_button()

    def _make_button(
        self,
        icon_name: str,
        tooltip: str,
        *,
        accent: bool = False,
        size: int = 34,
    ) -> QToolButton:
        button = QToolButton()
        button.setObjectName("controlButton")
        button.setProperty("accent", accent)
        icon_size = 20 if accent else 16
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

    def _set_title_playing(self, playing: bool) -> None:
        self._title.setProperty("playing", playing)
        self._repolish(self._title)

    def _update_like_button(self) -> None:
        self._like_btn.setEnabled(self._current_track is not None)
        self._like_btn.setProperty("liked", self._track_liked)
        self._like_btn.setToolTip(
            "Убрать из любимых" if self._track_liked else "В любимые"
        )
        self._repolish(self._like_btn)

    def _apply_cover(self, track: Track) -> None:
        cover_path = Path(self._path_provider.get_cover_path(track))
        size = max(self._cover.width(), self._cover.height(), 48)
        pixmap = load_cover_pixmap(cover_path, size)
        self._cover.setPixmap(pixmap if pixmap is not None else QPixmap())

    def _on_track_changed(self, track) -> None:
        self._current_track = track
        self._title.setText(track.title)
        self._author.setText(track.author)
        self._author.setVisible(bool(track.author))
        self._apply_cover(track)
        if self._bridge is not None and self._music is not None:
            schedule_cover_prefetch(
                [track],
                self._music.downloader,
                self._bridge,
                on_done=lambda t=track: self._apply_cover(t),
                limit=1,
            )
            self._bridge.schedule(self._sync_liked_state(track))
        else:
            self._track_liked = False
            self._update_like_button()

    async def _sync_liked_state(self, track: Track) -> None:
        liked = await self._liked.is_liked(track)
        if self._bridge is not None:
            self._bridge.invoke_main(lambda: self._set_liked_ui(liked))

    def _set_liked_ui(self, liked: bool) -> None:
        self._track_liked = liked
        self._update_like_button()

    def _on_like_clicked(self) -> None:
        track = self._current_track
        if track is None or self._bridge is None:
            return
        self._bridge.schedule(self._toggle_like(track))

    async def _toggle_like(self, track: Track) -> None:
        liked = await self._liked.toggle(track)
        if self._bridge is not None:
            self._bridge.invoke_main(lambda: self._set_liked_ui(liked))
            if self._on_liked_changed is not None:
                self._bridge.invoke_main(self._on_liked_changed)

    def _on_playing_changed(self, playing: bool) -> None:
        self._is_playing = playing
        icon = "pause.svg" if playing else "play.svg"
        self._play_btn.setIcon(resources.load_icon(icon))
        self._set_title_playing(playing)

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
        for button in (self._prev_btn, self._play_btn, self._next_btn, self._like_btn):
            self._repolish(button)
        self._set_title_playing(self._is_playing)
        self._update_like_button()
        card = self.findChild(QFrame, "PlayMenu")
        if card is not None:
            style = self.style()
            style.unpolish(card)
            style.polish(card)
            card.update()
        self.update()
