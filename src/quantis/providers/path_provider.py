from __future__ import annotations

import logging
import re
from os import path
from pathlib import Path

from quantis.models.track import Track

_INVALID_PATH_CHARS = re.compile(r'[<>:"/\\|?*]')
logger = logging.getLogger(__name__)


class PathProvider:
    MUSIC_FOLDER = "music/"
    COVERS_FOLDER = "covers/"
    PLAYLISTS_FOLDER = "playlists/"
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    @classmethod
    def ensure_storage_dirs(cls) -> None:
        Path(cls.MUSIC_FOLDER).mkdir(parents=True, exist_ok=True)
        Path(cls.COVERS_FOLDER).mkdir(parents=True, exist_ok=True)
        Path(cls.PLAYLISTS_FOLDER).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sanitize_filename_part(value: str) -> str:
        cleaned = _INVALID_PATH_CHARS.sub("_", value.strip())
        return cleaned or "unknown"

    def get_track_path(self, track: Track, extension: str = "mp3") -> str:
        title = self._sanitize_filename_part(track.title)
        author = self._sanitize_filename_part(track.author)
        return path.join(
            self.MUSIC_FOLDER,
            f"{track.track_id}_{title}_{author}.{extension}",
        )

    def get_cover_path(self, track: Track, extension: str = "jpg") -> str:
        return path.join(self.COVERS_FOLDER, f"{track.track_id}.{extension}")

    def get_video_cache_path(self, track: Track, extension: str = "mp4") -> str:
        """Кэш видео для динамических обоев (не путать с аудио в music/)."""
        video_dir = path.join(self.MUSIC_FOLDER, ".video")
        Path(video_dir).mkdir(parents=True, exist_ok=True)
        return path.join(video_dir, f"{track.track_id}.{extension}")
