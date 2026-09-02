"""Общие хелперы для Yandex finder/wave."""

from __future__ import annotations

from typing import Any

from quantis.models import Track, YandexTrack


def yandex_tracks_from_search(search_result: Any, value: int) -> list[Track]:
    if not search_result or not search_result.tracks:
        return []
    results = search_result.tracks.results[:value]
    return [yandex_track_from_api(track) for track in results]


def yandex_track_from_api(track: Any) -> YandexTrack:
    return YandexTrack(
        track_id=str(track.id),
        title=track.title,
        author=" & ".join(artist.name for artist in track.artists if artist.name),
        downloaded=False,
    )
