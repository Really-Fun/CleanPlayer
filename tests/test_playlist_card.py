from __future__ import annotations

from quantis.ui.views.widgets.playlist_card import playlist_tracks_label


def test_playlist_tracks_label_plural() -> None:
    assert playlist_tracks_label(1) == "1 трек"
    assert playlist_tracks_label(2) == "2 трека"
    assert playlist_tracks_label(5) == "5 треков"
    assert playlist_tracks_label(21) == "21 трек"
    assert playlist_tracks_label(12) == "12 треков"
