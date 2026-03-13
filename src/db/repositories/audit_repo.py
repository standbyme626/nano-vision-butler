"""Audit log data access repository."""

from __future__ import annotations

import sqlite3

from src.db.session import require_non_empty, require_positive_limit, utc_now_iso8601
from src.schemas.security import AuditLog


class AuditRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save_audit_log(self, audit_log: AuditLog) -> AuditLog:
        require_non_empty(audit_log.id, "audit_log.id")
        require_non_empty(audit_log.action, "audit_log.action")
        require_non_empty(audit_log.decision, "audit_log.decision")

        created_at = audit_log.created_at or utc_now_iso8601()

        self.conn.execute(
            """
            INSERT INTO audit_logs (
                id, user_id, device_id, action, target_type, target_id,
                decision, reason, trace_id, meta_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_log.id,
                audit_log.user_id,
                audit_log.device_id,
                audit_log.action,
                audit_log.target_type,
                audit_log.target_id,
                audit_log.decision,
                audit_log.reason,
                audit_log.trace_id,
                audit_log.meta_json,
                created_at,
            ),
        )

        row = self.conn.execute("SELECT * FROM audit_logs WHERE id = ?", (audit_log.id,)).fetchone()
        assert row is not None
        return AuditLog.from_row(row)

    def list_recent(self, limit: int = 20) -> list[AuditLog]:
        require_positive_limit(limit)
        rows = self.conn.execute(
            "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [AuditLog.from_row(row) for row in rows]
