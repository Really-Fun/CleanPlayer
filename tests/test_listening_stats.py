"""Тесты агрегатов статистики прослушивания."""

from __future__ import annotations

from pathlib import Path

from quantis.database.sync_history import (
    fetch_listening_summary,
    fetch_ranked_entries,
    upsert_progress,
)


def _play(
    db: Path,
    *,
    key: str,
    title: str,
    author: str,
    listens: int,
    duration_ms: int = 180_000,
) -> None:
    upsert_progress(
        track_key=key,
        title=title,
        author=author,
        source="yandex",
        position_ms=duration_ms,
        duration_ms=duration_ms,
        listen_increment=listens,
        db_path=db,
    )


def test_listening_summary_and_rankings(tmp_path: Path) -> None:
    db = tmp_path / "player_history.db"
    _play(db, key="yandex:1", title="Hit", author="Star", listens=5)
    _play(db, key="yandex:2", title="Rare", author="Star", listens=1)
    _play(db, key="yandex:3", title="Skip", author="Other", listens=0, duration_ms=60_000)
    _play(db, key="youtube:ab", title="Mix", author="DJ", listens=3, duration_ms=3_600_000)

    summary = fetch_listening_summary(db)
    assert summary.unique_tracks == 4
    assert summary.total_listens == 9
    assert summary.top_artist == "Star"
    assert summary.top_artist_listens == 6
    assert summary.listened_ms == 5 * 180_000 + 1 * 180_000 + 3 * 3_600_000

    most = fetch_ranked_entries(2, descending=True, db_path=db)
    assert [row["title"] for row in most] == ["Hit", "Mix"]
    assert most[0]["listen_count"] == 5

    least = fetch_ranked_entries(2, descending=False, db_path=db)
    assert [row["title"] for row in least] == ["Rare", "Mix"]


def test_empty_history_summary(tmp_path: Path) -> None:
    db = tmp_path / "empty.db"
    summary = fetch_listening_summary(db)
    assert summary.unique_tracks == 0
    assert summary.total_listens == 0
    assert summary.top_artist == ""
    assert fetch_ranked_entries(5, db_path=db) == []
