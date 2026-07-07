"""Движок воспроизведения на Qt Multimedia."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class QtMediaEngine:
    """Владеет QMediaPlayer и QAudioOutput."""

    def __init__(self) -> None:
        self._player = QMediaPlayer()
        self._audio = QAudioOutput()
        self._player.setAudioOutput(self._audio)

    @property
    def media_player(self) -> QMediaPlayer:
        return self._player

    @property
    def audio_output(self) -> QAudioOutput:
        return self._audio

    @staticmethod
    def _to_url(source: str) -> QUrl:
        if source.startswith(("http://", "https://")):
            return QUrl(source)
        return QUrl.fromLocalFile(str(Path(source).resolve()))

    def play_media(self, source: str) -> None:
        self._player.setSource(self._to_url(source))
        self._player.play()

    def pause_media(self) -> None:
        self._player.pause()

    def resume_media(self) -> None:
        self._player.play()

    def stop_media(self) -> None:
        self._player.stop()
