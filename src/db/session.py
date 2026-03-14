"""SQLite session and shared validation helpers for repositories."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator


def utc_now_iso8601() -> str:
    mode = _time_mode()
    if mode == "local":
        return datetime.now().astimezone().isoformat(timespec="milliseconds")
    return datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def normalize_iso8601(value: str, field_name: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty ISO8601 string")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid ISO8601 for {field_name}: {value}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    mode = _time_mode()
    if mode == "local":
        return dt.astimezone().isoformat(timespec="milliseconds")
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _time_mode() -> str:
    raw = (os.getenv("VISION_BUTLER_TIME_MODE", "utc") or "utc").strip().lower()
    if raw in {"local", "asia/shanghai", "cst"}:
        return "local"
    return "utc"


def require_non_empty(value: str | None, field_name: str) -> str:
    if value is None or not str(value).strip():
        raise ValueError(f"{field_name} is required and must be non-empty")
    return str(value).strip()


def require_positive_limit(limit: int) -> int:
    if limit <= 0:
        raise ValueError("limit must be > 0")
    return limit


def create_connection(db_path: str | Path) -> sqlite3.Connection:
    # FastAPI may hand off sync dependency work between worker threads inside one request.
    # Allow thread handoff for request-scoped connections; lifecycle is still per-request.
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


class SQLiteSessionFactory:
    """Connection factory for app/services dependency injection."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = create_connection(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def initialize_database(db_path: str | Path, schema_path: str | Path = "schema.sql") -> None:
    conn = create_connection(db_path)
    try:
        sql = Path(schema_path).read_text(encoding="utf-8")
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()
