"""Notification rule repository for active rule lookup and throttle bookkeeping."""

from __future__ import annotations

import sqlite3
from typing import Any

from src.db.session import normalize_iso8601, require_non_empty, require_positive_limit, utc_now_iso8601
from src.schemas.policy import NotificationRule


class NotificationRuleRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save_rule(self, rule: NotificationRule) -> NotificationRule:
        require_non_empty(rule.id, "rule.id")
        require_non_empty(rule.user_id, "rule.user_id")
        require_non_empty(rule.rule_name, "rule.rule_name")
        require_non_empty(rule.trigger_type, "rule.trigger_type")
        require_non_empty(rule.condition_json, "rule.condition_json")

        created_at = normalize_iso8601(rule.created_at, "rule.created_at") if rule.created_at else utc_now_iso8601()
        updated_at = normalize_iso8601(rule.updated_at, "rule.updated_at") if rule.updated_at else utc_now_iso8601()
        last_triggered_at = (
            normalize_iso8601(rule.last_triggered_at, "rule.last_triggered_at")
            if rule.last_triggered_at
            else None
        )

        self.conn.execute(
            """
            INSERT INTO notification_rules (
                id, user_id, rule_name, trigger_type, target_scope, condition_json,
                is_enabled, cooldown_sec, last_triggered_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                user_id = excluded.user_id,
                rule_name = excluded.rule_name,
                trigger_type = excluded.trigger_type,
                target_scope = excluded.target_scope,
                condition_json = excluded.condition_json,
                is_enabled = excluded.is_enabled,
                cooldown_sec = excluded.cooldown_sec,
                last_triggered_at = excluded.last_triggered_at,
                updated_at = excluded.updated_at
            """,
            (
                rule.id,
                rule.user_id,
                rule.rule_name,
                rule.trigger_type,
                rule.target_scope,
                rule.condition_json,
                int(rule.is_enabled),
                int(rule.cooldown_sec),
                last_triggered_at,
                created_at,
                updated_at,
            ),
        )
        current = self.get_rule(rule.id)
        assert current is not None
        return current

    def get_rule(self, rule_id: str) -> NotificationRule | None:
        require_non_empty(rule_id, "rule_id")
        row = self.conn.execute(
            "SELECT * FROM notification_rules WHERE id = ? LIMIT 1",
            (rule_id,),
        ).fetchone()
        return NotificationRule.from_row(row) if row else None

    def list_active_rules(self, *, trigger_type: str, limit: int = 200) -> list[dict[str, Any]]:
        require_non_empty(trigger_type, "trigger_type")
        require_positive_limit(limit)
        rows = self.conn.execute(
            """
            SELECT
                id,
                user_id,
                telegram_chat_id,
                rule_name,
                trigger_type,
                target_scope,
                condition_json,
                cooldown_sec,
                last_triggered_at
            FROM active_notification_rules_view
            WHERE trigger_type = ?
            ORDER BY id
            LIMIT ?
            """,
            (trigger_type, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def update_last_triggered_at(self, *, rule_id: str, triggered_at: str | None = None) -> None:
        require_non_empty(rule_id, "rule_id")
        value = normalize_iso8601(triggered_at, "triggered_at") if triggered_at else utc_now_iso8601()
        self.conn.execute(
            """
            UPDATE notification_rules
            SET last_triggered_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (value, utc_now_iso8601(), rule_id),
        )

    def count_user_triggers_since(self, *, user_id: str, since: str) -> int:
        require_non_empty(user_id, "user_id")
        since_ts = normalize_iso8601(since, "since")
        row = self.conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM audit_logs
            WHERE action = 'notification_dispatch'
              AND decision = 'allow'
              AND user_id = ?
              AND julianday(created_at) >= julianday(?)
            """,
            (user_id, since_ts),
        ).fetchone()
        return int(row["total"] if row else 0)
