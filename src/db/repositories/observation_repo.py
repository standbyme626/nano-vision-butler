"""Observation data access repository."""

from __future__ import annotations

import sqlite3
from typing import Optional

from src.db.session import normalize_iso8601, require_non_empty, require_positive_limit, utc_now_iso8601
from src.schemas.memory import Observation


class ObservationRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save_observation(self, observation: Observation) -> Observation:
        require_non_empty(observation.id, "observation.id")
        require_non_empty(observation.device_id, "observation.device_id")
        require_non_empty(observation.camera_id, "observation.camera_id")

        observed_at = normalize_iso8601(observation.observed_at, "observation.observed_at")
        fresh_until = (
            normalize_iso8601(observation.fresh_until, "observation.fresh_until")
            if observation.fresh_until
            else None
        )
        created_at = (
            normalize_iso8601(observation.created_at, "observation.created_at")
            if observation.created_at
            else utc_now_iso8601()
        )

        self.conn.execute(
            """
            INSERT INTO observations (
                id, device_id, camera_id, zone_id, object_name, object_class, track_id,
                confidence, state_hint, observed_at, fresh_until, source_event_id,
                snapshot_uri, clip_uri, ocr_text, visibility_scope, raw_payload_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                observation.id,
                observation.device_id,
                observation.camera_id,
                observation.zone_id,
                observation.object_name,
                observation.object_class,
                observation.track_id,
                observation.confidence,
                observation.state_hint,
                observed_at,
                fresh_until,
                observation.source_event_id,
                observation.snapshot_uri,
                observation.clip_uri,
                observation.ocr_text,
                observation.visibility_scope,
                observation.raw_payload_json,
                created_at,
            ),
        )
        row = self.conn.execute(
            "SELECT * FROM observations WHERE id = ?", (observation.id,)
        ).fetchone()
        assert row is not None
        return Observation.from_row(row)

    def get_last_seen(
        self,
        object_name: str,
        camera_id: str | None = None,
        zone_id: str | None = None,
    ) -> Optional[Observation]:
        require_non_empty(object_name, "object_name")

        row = self.conn.execute(
            """
            SELECT *
            FROM observations
            WHERE object_name = ?
              AND (? IS NULL OR camera_id = ?)
              AND (? IS NULL OR zone_id = ?)
            ORDER BY observed_at DESC
            LIMIT 1
            """,
            (object_name, camera_id, camera_id, zone_id, zone_id),
        ).fetchone()
        return Observation.from_row(row) if row else None

    def last_seen(
        self,
        object_name: str,
        camera_id: str | None = None,
        zone_id: str | None = None,
    ) -> Optional[Observation]:
        return self.get_last_seen(object_name=object_name, camera_id=camera_id, zone_id=zone_id)

    def list_recent_by_zone(
        self,
        *,
        camera_id: str,
        zone_id: str,
        limit: int = 20,
    ) -> list[Observation]:
        require_non_empty(camera_id, "camera_id")
        require_non_empty(zone_id, "zone_id")
        require_positive_limit(limit)

        rows = self.conn.execute(
            """
            SELECT *
            FROM observations
            WHERE camera_id = ? AND zone_id = ?
            ORDER BY observed_at DESC
            LIMIT ?
            """,
            (camera_id, zone_id, limit),
        ).fetchall()
        return [Observation.from_row(row) for row in rows]

    def query_recent_observations(
        self,
        *,
        camera_id: str | None = None,
        zone_id: str | None = None,
        object_name: str | None = None,
        limit: int = 20,
    ) -> list[Observation]:
        require_positive_limit(limit)
        rows = self.conn.execute(
            """
            SELECT *
            FROM observations
            WHERE (? IS NULL OR camera_id = ?)
              AND (? IS NULL OR zone_id = ?)
              AND (? IS NULL OR object_name = ?)
            ORDER BY observed_at DESC
            LIMIT ?
            """,
            (
                camera_id,
                camera_id,
                zone_id,
                zone_id,
                object_name,
                object_name,
                limit,
            ),
        ).fetchall()
        return [Observation.from_row(row) for row in rows]

    def get_observation(self, observation_id: str) -> Observation | None:
        require_non_empty(observation_id, "observation_id")
        row = self.conn.execute(
            "SELECT * FROM observations WHERE id = ?",
            (observation_id,),
        ).fetchone()
        return Observation.from_row(row) if row else None

    def update_observation_ocr_text(self, observation_id: str, ocr_text: str) -> Observation:
        require_non_empty(observation_id, "observation_id")
        require_non_empty(ocr_text, "ocr_text")
        current = self.get_observation(observation_id)
        if current is None:
            raise ValueError(f"Observation not found: {observation_id}")

        merged_text = ocr_text
        if current.ocr_text and current.ocr_text.strip():
            merged_text = f"{current.ocr_text}\n{ocr_text}".strip()

        self.conn.execute(
            "UPDATE observations SET ocr_text = ? WHERE id = ?",
            (merged_text, observation_id),
        )
        updated = self.get_observation(observation_id)
        assert updated is not None
        return updated
