from __future__ import annotations

import logging
import re
from os import path
from pathlib import Path

from quantis.models.track import Track
from quantis.utils import app_paths

_INVALID_PATH_CHARS = re.compile(r'[<>:"/\\|?*]')
logger = logging.getLogger(__name__)


class PathProvider:
    """Пути к файлам трека. Каталоги берутся из ``app_paths``.

    Классовые атрибуты ниже — точка переопределения (тесты, плагины). Если они
    заданы, используются вместо каталогов пользователя.
    """

    MUSIC_FOLDER: str | None = None
    COVERS_FOLDER: str | None = None
    PLAYLISTS_FOLDER: str | None = None
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    @classmethod
    def music_folder(cls) -> str:
        return cls.MUSIC_FOLDER or str(app_paths.music_dir())

    @classmethod
    def covers_folder(cls) -> str:
        return cls.COVERS_FOLDER or str(app_paths.covers_dir())

    @classmethod
    def playlists_folder(cls) -> str:
        return cls.PLAYLISTS_FOLDER or str(app_paths.playlists_dir())

    @classmethod
    def ensure_storage_dirs(cls) -> None:
        for folder in (cls.music_folder(), cls.covers_folder(), cls.playlists_folder()):
            Path(folder).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sanitize_filename_part(value: str) -> str:
        cleaned = _INVALID_PATH_CHARS.sub("_", value.strip())
        return cleaned or "unknown"

    def get_track_path(self, track: Track, extension: str = "mp3") -> str:
        title = self._sanitize_filename_part(track.title)
        author = self._sanitize_filename_part(track.author)
        return path.join(
            self.music_folder(),
            f"{track.track_id}_{title}_{author}.{extension}",
        )

    def get_cover_path(self, track: Track, extension: str = "jpg") -> str:
        return path.join(self.covers_folder(), f"{track.track_id}.{extension}")

    def get_video_cache_path(self, track: Track, extension: str = "mp4") -> str:
        """Кэш видео для динамических обоев (не путать с аудио в music/)."""
        video_dir = path.join(self.music_folder(), ".video")
        Path(video_dir).mkdir(parents=True, exist_ok=True)
        return path.join(video_dir, f"{track.track_id}.{extension}")
