"""Парсинг ссылок YouTube и Yandex Music для расширенного поиска."""

from __future__ import annotations

import re
from typing import Literal
from urllib.parse import parse_qs, urlparse

SourceId = Literal["yandex", "youtube"]

_YANDEX_TRACK_RE = re.compile(
    r"(?:music\.)?yandex\.(?:ru|com|by|kz|ua)/(?:album/\d+/track/|track/)(\d+)",
    re.IGNORECASE,
)
_YOUTUBE_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|shorts/|embed/)|youtu\.be/|music\.youtube\.com/watch\?v=)"
    r"([A-Za-z0-9_-]{11})",
    re.IGNORECASE,
)


def detect_source(url: str) -> SourceId | None:
    """Определяет платформу по домену ссылки."""
    text = url.strip()
    lowered = text.lower()
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()

    is_yandex_music_host = host.startswith("music.yandex.")
    if is_yandex_music_host and "/track/" in lowered:
        return "yandex"

    is_youtube_host = host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com")
    if is_youtube_host:
        return "youtube"
    return None


def parse_yandex_track_id(url: str) -> str | None:
    match = _YANDEX_TRACK_RE.search(url.strip())
    return match.group(1) if match else None


def parse_youtube_video_id(url: str) -> str | None:
    text = url.strip()
    match = _YOUTUBE_ID_RE.search(text)
    if match:
        return match.group(1)
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    is_youtube_host = host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com")
    if is_youtube_host:
        query_id = parse_qs(parsed.query).get("v", [None])[0]
        if query_id and len(query_id) == 11:
            return query_id
    return None


def parse_track_id(url: str) -> tuple[SourceId, str] | None:
    """Извлекает (source, track_id) из ссылки."""
    source = detect_source(url)
    if source == "yandex":
        track_id = parse_yandex_track_id(url)
        return ("yandex", track_id) if track_id else None
    if source == "youtube":
        video_id = parse_youtube_video_id(url)
        return ("youtube", video_id) if video_id else None
    return None
