"""Event data access repository."""

from __future__ import annotations

import sqlite3
from typing import Optional

from src.db.session import (
    normalize_iso8601,
    require_non_empty,
    require_positive_limit,
    utc_now_iso8601,
)
from src.schemas.memory import Event


class EventRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save_event(self, event: Event) -> Event:
        require_non_empty(event.id, "event.id")
        require_non_empty(event.event_type, "event.event_type")
        require_non_empty(event.summary, "event.summary")

        event_at = normalize_iso8601(event.event_at, "event.event_at")
        created_at = (
            normalize_iso8601(event.created_at, "event.created_at")
            if event.created_at
            else utc_now_iso8601()
        )

        self.conn.execute(
            """
            INSERT INTO events (
                id, observation_id, event_type, category, importance,
                camera_id, zone_id, object_name, summary, payload_json, event_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.observation_id,
                event.event_type,
                event.category,
                event.importance,
                event.camera_id,
                event.zone_id,
                event.object_name,
                event.summary,
                event.payload_json,
                event_at,
                created_at,
            ),
        )
        row = self.conn.execute("SELECT * FROM events WHERE id = ?", (event.id,)).fetchone()
        assert row is not None
        return Event.from_row(row)

    def query_recent_events(
        self,
        *,
        zone_id: str | None = None,
        object_name: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 20,
    ) -> list[Event]:
        require_positive_limit(limit)
        if start_time:
            start_time = normalize_iso8601(start_time, "start_time")
        if end_time:
            end_time = normalize_iso8601(end_time, "end_time")

        rows = self.conn.execute(
            """
            SELECT *
            FROM events
            WHERE (? IS NULL OR zone_id = ?)
              AND (? IS NULL OR object_name = ?)
              AND (? IS NULL OR event_at >= ?)
              AND (? IS NULL OR event_at < ?)
            ORDER BY event_at DESC
            LIMIT ?
            """,
            (
                zone_id,
                zone_id,
                object_name,
                object_name,
                start_time,
                start_time,
                end_time,
                end_time,
                limit,
            ),
        ).fetchall()
        return [Event.from_row(row) for row in rows]

    def get_event(self, event_id: str) -> Optional[Event]:
        require_non_empty(event_id, "event_id")
        row = self.conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        return Event.from_row(row) if row else None
