"""Media data access repository."""

from __future__ import annotations

import sqlite3

from src.db.session import require_non_empty, require_positive_limit, utc_now_iso8601
from src.schemas.memory import MediaItem


class MediaRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save_media_item(self, media: MediaItem) -> MediaItem:
        require_non_empty(media.id, "media.id")
        require_non_empty(media.owner_type, "media.owner_type")
        require_non_empty(media.owner_id, "media.owner_id")
        require_non_empty(media.media_type, "media.media_type")
        require_non_empty(media.uri, "media.uri")
        require_non_empty(media.local_path, "media.local_path")

        created_at = media.created_at or utc_now_iso8601()

        self.conn.execute(
            """
            INSERT INTO media_items (
                id, owner_type, owner_id, media_type, uri, local_path,
                mime_type, duration_sec, width, height, visibility_scope, sha256, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                media.id,
                media.owner_type,
                media.owner_id,
                media.media_type,
                media.uri,
                media.local_path,
                media.mime_type,
                media.duration_sec,
                media.width,
                media.height,
                media.visibility_scope,
                media.sha256,
                created_at,
            ),
        )

        row = self.conn.execute(
            "SELECT * FROM media_items WHERE id = ?", (media.id,)
        ).fetchone()
        assert row is not None
        return MediaItem.from_row(row)

    def list_media_for_owner(self, owner_type: str, owner_id: str, limit: int = 10) -> list[MediaItem]:
        require_non_empty(owner_type, "owner_type")
        require_non_empty(owner_id, "owner_id")
        require_positive_limit(limit)

        rows = self.conn.execute(
            """
            SELECT *
            FROM media_items
            WHERE owner_type = ? AND owner_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (owner_type, owner_id, limit),
        ).fetchall()
        return [MediaItem.from_row(row) for row in rows]

    def get_media_item(self, media_id: str) -> MediaItem | None:
        require_non_empty(media_id, "media_id")
        row = self.conn.execute("SELECT * FROM media_items WHERE id = ?", (media_id,)).fetchone()
        return MediaItem.from_row(row) if row else None

    def get_media_item_by_uri(self, uri: str) -> MediaItem | None:
        require_non_empty(uri, "uri")
        row = self.conn.execute(
            "SELECT * FROM media_items WHERE uri = ? ORDER BY created_at DESC LIMIT 1",
            (uri,),
        ).fetchone()
        return MediaItem.from_row(row) if row else None
