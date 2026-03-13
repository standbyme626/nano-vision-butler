"""OCR result data access repository."""

from __future__ import annotations

import sqlite3

from src.db.session import require_non_empty, require_positive_limit, utc_now_iso8601
from src.schemas.memory import OcrResult


class OcrRepo:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def save_ocr_result(self, ocr_result: OcrResult) -> OcrResult:
        require_non_empty(ocr_result.id, "ocr_result.id")
        require_non_empty(ocr_result.source_media_id, "ocr_result.source_media_id")
        require_non_empty(ocr_result.ocr_mode, "ocr_result.ocr_mode")

        created_at = ocr_result.created_at or utc_now_iso8601()

        self.conn.execute(
            """
            INSERT INTO ocr_results (
                id, source_media_id, source_observation_id, ocr_mode,
                raw_text, fields_json, boxes_json, language, confidence, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ocr_result.id,
                ocr_result.source_media_id,
                ocr_result.source_observation_id,
                ocr_result.ocr_mode,
                ocr_result.raw_text,
                ocr_result.fields_json,
                ocr_result.boxes_json,
                ocr_result.language,
                ocr_result.confidence,
                created_at,
            ),
        )
        row = self.conn.execute("SELECT * FROM ocr_results WHERE id = ?", (ocr_result.id,)).fetchone()
        assert row is not None
        return OcrResult.from_row(row)

    def get_ocr_result(self, ocr_result_id: str) -> OcrResult | None:
        require_non_empty(ocr_result_id, "ocr_result_id")
        row = self.conn.execute("SELECT * FROM ocr_results WHERE id = ?", (ocr_result_id,)).fetchone()
        return OcrResult.from_row(row) if row else None

    def list_by_media_id(self, source_media_id: str, limit: int = 20) -> list[OcrResult]:
        require_non_empty(source_media_id, "source_media_id")
        require_positive_limit(limit)
        rows = self.conn.execute(
            """
            SELECT *
            FROM ocr_results
            WHERE source_media_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (source_media_id, limit),
        ).fetchall()
        return [OcrResult.from_row(row) for row in rows]
