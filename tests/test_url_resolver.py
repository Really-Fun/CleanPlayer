"""Unit-тесты парсинга URL для расширенного поиска."""

from __future__ import annotations

from quantis.services.url_resolver import (
    detect_source,
    parse_track_id,
    parse_yandex_track_id,
    parse_youtube_video_id,
)


def test_detect_source_yandex() -> None:
    assert detect_source("https://music.yandex.ru/album/1/track/12345") == "yandex"


def test_detect_source_youtube() -> None:
    assert detect_source("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "youtube"
    assert detect_source("https://youtu.be/dQw4w9WgXcQ") == "youtube"


def test_parse_yandex_track_id() -> None:
    url = "https://music.yandex.ru/album/123/track/987654"
    assert parse_yandex_track_id(url) == "987654"


def test_parse_youtube_video_id_watch() -> None:
    assert parse_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_parse_youtube_video_id_short() -> None:
    assert parse_youtube_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_parse_track_id_yandex() -> None:
    parsed = parse_track_id("https://music.yandex.ru/track/555")
    assert parsed == ("yandex", "555")


def test_parse_track_id_youtube() -> None:
    parsed = parse_track_id("https://music.youtube.com/watch?v=abc12345678")
    assert parsed == ("youtube", "abc12345678")


def test_parse_track_id_invalid() -> None:
    assert parse_track_id("https://example.com/foo") is None
