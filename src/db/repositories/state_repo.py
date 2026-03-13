"""Object/zone state data access repository."""

from __future__ import annotations

import sqlite3
from typing import Optional

from src.db.session import normalize_iso8601, require_non_empty, require_positive_limit, utc_now_iso8601
from src.schemas.state import ObjectState, ZoneState


class StateRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save_object_state(self, state: ObjectState) -> ObjectState:
        require_non_empty(state.id, "object_state.id")
        require_non_empty(state.object_name, "object_state.object_name")
        require_non_empty(state.state_value, "object_state.state_value")

        observed_at = (
            normalize_iso8601(state.observed_at, "object_state.observed_at")
            if state.observed_at
            else None
        )
        last_confirmed_at = (
            normalize_iso8601(state.last_confirmed_at, "object_state.last_confirmed_at")
            if state.last_confirmed_at
            else None
        )
        last_changed_at = (
            normalize_iso8601(state.last_changed_at, "object_state.last_changed_at")
            if state.last_changed_at
            else None
        )
        fresh_until = (
            normalize_iso8601(state.fresh_until, "object_state.fresh_until")
            if state.fresh_until
            else None
        )
        updated_at = (
            normalize_iso8601(state.updated_at, "object_state.updated_at")
            if state.updated_at
            else utc_now_iso8601()
        )

        self.conn.execute(
            """
            INSERT INTO object_states (
                id, object_name, camera_id, zone_id, state_value, state_confidence,
                observed_at, last_confirmed_at, last_changed_at, fresh_until,
                is_stale, evidence_count, source_layer, summary, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_name, camera_id, zone_id) DO UPDATE SET
                id = excluded.id,
                state_value = excluded.state_value,
                state_confidence = excluded.state_confidence,
                observed_at = excluded.observed_at,
                last_confirmed_at = excluded.last_confirmed_at,
                last_changed_at = excluded.last_changed_at,
                fresh_until = excluded.fresh_until,
                is_stale = excluded.is_stale,
                evidence_count = excluded.evidence_count,
                source_layer = excluded.source_layer,
                summary = excluded.summary,
                updated_at = excluded.updated_at
            """,
            (
                state.id,
                state.object_name,
                state.camera_id,
                state.zone_id,
                state.state_value,
                state.state_confidence,
                observed_at,
                last_confirmed_at,
                last_changed_at,
                fresh_until,
                state.is_stale,
                state.evidence_count,
                state.source_layer,
                state.summary,
                updated_at,
            ),
        )
        refreshed = self.get_object_state(state.object_name, state.camera_id, state.zone_id)
        assert refreshed is not None
        return refreshed

    def get_object_state(
        self,
        object_name: str,
        camera_id: str | None = None,
        zone_id: str | None = None,
    ) -> Optional[ObjectState]:
        require_non_empty(object_name, "object_name")

        row = self.conn.execute(
            """
            SELECT *
            FROM object_states
            WHERE object_name = ?
              AND (? IS NULL OR camera_id = ?)
              AND (? IS NULL OR zone_id = ?)
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (object_name, camera_id, camera_id, zone_id, zone_id),
        ).fetchone()
        return ObjectState.from_row(row) if row else None

    def save_zone_state(self, state: ZoneState) -> ZoneState:
        require_non_empty(state.id, "zone_state.id")
        require_non_empty(state.camera_id, "zone_state.camera_id")
        require_non_empty(state.zone_id, "zone_state.zone_id")
        require_non_empty(state.state_value, "zone_state.state_value")

        observed_at = (
            normalize_iso8601(state.observed_at, "zone_state.observed_at")
            if state.observed_at
            else None
        )
        fresh_until = (
            normalize_iso8601(state.fresh_until, "zone_state.fresh_until")
            if state.fresh_until
            else None
        )
        updated_at = (
            normalize_iso8601(state.updated_at, "zone_state.updated_at")
            if state.updated_at
            else utc_now_iso8601()
        )

        self.conn.execute(
            """
            INSERT INTO zone_states (
                id, camera_id, zone_id, state_value, state_confidence,
                observed_at, fresh_until, is_stale, evidence_count,
                source_layer, summary, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(camera_id, zone_id) DO UPDATE SET
                id = excluded.id,
                state_value = excluded.state_value,
                state_confidence = excluded.state_confidence,
                observed_at = excluded.observed_at,
                fresh_until = excluded.fresh_until,
                is_stale = excluded.is_stale,
                evidence_count = excluded.evidence_count,
                source_layer = excluded.source_layer,
                summary = excluded.summary,
                updated_at = excluded.updated_at
            """,
            (
                state.id,
                state.camera_id,
                state.zone_id,
                state.state_value,
                state.state_confidence,
                observed_at,
                fresh_until,
                state.is_stale,
                state.evidence_count,
                state.source_layer,
                state.summary,
                updated_at,
            ),
        )
        refreshed = self.get_zone_state(state.camera_id, state.zone_id)
        assert refreshed is not None
        return refreshed

    def get_zone_state(self, camera_id: str, zone_id: str) -> Optional[ZoneState]:
        require_non_empty(camera_id, "camera_id")
        require_non_empty(zone_id, "zone_id")

        row = self.conn.execute(
            """
            SELECT *
            FROM zone_states
            WHERE camera_id = ? AND zone_id = ?
            LIMIT 1
            """,
            (camera_id, zone_id),
        ).fetchone()
        return ZoneState.from_row(row) if row else None

    def list_object_states(
        self,
        *,
        camera_id: str | None = None,
        zone_id: str | None = None,
        limit: int = 50,
    ) -> list[ObjectState]:
        require_positive_limit(limit)
        rows = self.conn.execute(
            """
            SELECT *
            FROM object_states
            WHERE (? IS NULL OR camera_id = ?)
              AND (? IS NULL OR zone_id = ?)
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (
                camera_id,
                camera_id,
                zone_id,
                zone_id,
                limit,
            ),
        ).fetchall()
        return [ObjectState.from_row(row) for row in rows]

    def list_zone_states(self, *, camera_id: str | None = None, limit: int = 50) -> list[ZoneState]:
        require_positive_limit(limit)
        rows = self.conn.execute(
            """
            SELECT *
            FROM zone_states
            WHERE (? IS NULL OR camera_id = ?)
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (
                camera_id,
                camera_id,
                limit,
            ),
        ).fetchall()
        return [ZoneState.from_row(row) for row in rows]
