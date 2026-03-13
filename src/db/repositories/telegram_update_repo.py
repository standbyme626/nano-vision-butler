"""Telegram update dedup/process status data access repository."""

from __future__ import annotations

import sqlite3

from src.db.session import require_non_empty, utc_now_iso8601
from src.schemas.telegram import TelegramUpdate


class TelegramUpdateRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save_telegram_update(self, update: TelegramUpdate) -> bool:
        require_non_empty(update.id, "telegram_update.id")
        require_non_empty(update.update_id, "telegram_update.update_id")

        status = update.status or "received"
        if status not in {"received", "processed", "failed"}:
            raise ValueError("telegram_update.status must be one of: received, processed, failed")

        cursor = self.conn.execute(
            """
            INSERT INTO telegram_updates (
                id, update_id, chat_id, from_user_id,
                message_type, message_text, received_at,
                processed_at, status, error_message, trace_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(update_id) DO NOTHING
            """,
            (
                update.id,
                update.update_id,
                update.chat_id,
                update.from_user_id,
                update.message_type,
                update.message_text,
                update.received_at or utc_now_iso8601(),
                update.processed_at,
                status,
                update.error_message,
                update.trace_id,
            ),
        )
        return cursor.rowcount == 1

    def mark_telegram_update_processed(self, update_id: str) -> bool:
        require_non_empty(update_id, "update_id")
        cursor = self.conn.execute(
            """
            UPDATE telegram_updates
            SET status = 'processed',
                processed_at = ?,
                error_message = NULL
            WHERE update_id = ?
            """,
            (utc_now_iso8601(), update_id),
        )
        return cursor.rowcount > 0

    def mark_telegram_update_failed(self, update_id: str, error_message: str) -> bool:
        require_non_empty(update_id, "update_id")
        require_non_empty(error_message, "error_message")
        cursor = self.conn.execute(
            """
            UPDATE telegram_updates
            SET status = 'failed',
                processed_at = ?,
                error_message = ?
            WHERE update_id = ?
            """,
            (utc_now_iso8601(), error_message, update_id),
        )
        return cursor.rowcount > 0

    def get_by_update_id(self, update_id: str) -> TelegramUpdate | None:
        require_non_empty(update_id, "update_id")
        row = self.conn.execute(
            "SELECT * FROM telegram_updates WHERE update_id = ? LIMIT 1", (update_id,)
        ).fetchone()
        return TelegramUpdate.from_row(row) if row else None
