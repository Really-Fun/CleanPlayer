"""Синхронный доступ к SQLite для вызова из thread pool (не блокирует Qt/qasync)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from time import time
from typing import Any

DEFAULT_DB_PATH = Path("player_history.db")


def _connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path.as_posix())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA cache_size=-8000;")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS track_history (
            track_key TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            source TEXT NOT NULL,
            position_ms INTEGER NOT NULL DEFAULT 0,
            duration_ms INTEGER NOT NULL DEFAULT 0,
            listen_count INTEGER NOT NULL DEFAULT 0,
            last_played_at INTEGER NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_track_history_last_played
        ON track_history(last_played_at DESC);
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS liked_tracks (
            track_key TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            source TEXT NOT NULL,
            liked_at INTEGER NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_liked_tracks_liked_at
        ON liked_tracks(liked_at DESC);
        """
    )
    conn.commit()


def fetch_liked_entries(db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    with _connect(db_path) as conn:
        ensure_schema(conn)
        cursor = conn.execute(
            """
            SELECT track_key, title, author, source, liked_at
            FROM liked_tracks
            ORDER BY liked_at DESC;
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def is_track_liked(track_key: str, db_path: Path = DEFAULT_DB_PATH) -> bool:
    with _connect(db_path) as conn:
        ensure_schema(conn)
        cursor = conn.execute(
            "SELECT 1 FROM liked_tracks WHERE track_key = ? LIMIT 1;",
            (track_key,),
        )
        return cursor.fetchone() is not None


def set_track_liked(
    *,
    track_key: str,
    title: str,
    author: str,
    source: str,
    liked: bool,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    with _connect(db_path) as conn:
        ensure_schema(conn)
        if liked:
            conn.execute(
                """
                INSERT INTO liked_tracks (track_key, title, author, source, liked_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(track_key) DO UPDATE SET
                    title = excluded.title,
                    author = excluded.author,
                    source = excluded.source,
                    liked_at = excluded.liked_at;
                """,
                (track_key, title, author, source, int(time())),
            )
        else:
            conn.execute(
                "DELETE FROM liked_tracks WHERE track_key = ?;",
                (track_key,),
            )
        conn.commit()


def fetch_recent_entries(
    limit: int,
    db_path: Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    with _connect(db_path) as conn:
        ensure_schema(conn)
        cursor = conn.execute(
            """
            SELECT track_key, title, author, source, position_ms, duration_ms,
                   listen_count, last_played_at
            FROM track_history
            ORDER BY last_played_at DESC
            LIMIT ?;
            """,
            (max(1, limit),),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_saved_position(track_key: str, db_path: Path = DEFAULT_DB_PATH) -> int:
    with _connect(db_path) as conn:
        ensure_schema(conn)
        cursor = conn.execute(
            "SELECT position_ms FROM track_history WHERE track_key = ?;",
            (track_key,),
        )
        row = cursor.fetchone()
        return int(row["position_ms"]) if row is not None else 0


def upsert_progress(
    *,
    track_key: str,
    title: str,
    author: str,
    source: str,
    position_ms: int,
    duration_ms: int,
    listen_increment: int = 0,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    with _connect(db_path) as conn:
        ensure_schema(conn)
        conn.execute(
            """
            INSERT INTO track_history (
                track_key, title, author, source, position_ms, duration_ms,
                listen_count, last_played_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(track_key) DO UPDATE SET
                title = excluded.title,
                author = excluded.author,
                source = excluded.source,
                position_ms = excluded.position_ms,
                duration_ms = excluded.duration_ms,
                listen_count = track_history.listen_count + excluded.listen_count,
                last_played_at = excluded.last_played_at;
            """,
            (
                track_key,
                title,
                author,
                source,
                max(0, position_ms),
                max(0, duration_ms),
                max(0, listen_increment),
                int(time()),
            ),
        )
        conn.commit()
