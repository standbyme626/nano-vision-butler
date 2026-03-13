<!-- source: 迁移版本草案.md | id: orm4f2 -->
"""fts tables

Revision ID: 004_20260313_fts
Revises: 003_20260313_indexes
Create Date: 2026-03-13 10:30:00
"""

from alembic import op

revision = "004_20260313_fts"
down_revision = "003_20260313_indexes"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts
    USING fts5(
        object_name,
        object_class,
        ocr_text,
        raw_payload_json,
        content='observations',
        content_rowid='rowid'
    );
    """)
    op.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS events_fts
    USING fts5(
        event_type,
        summary,
        payload_json,
        content='events',
        content_rowid='rowid'
    );
    """)
    op.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS ocr_results_fts
    USING fts5(
        raw_text,
        fields_json,
        content='ocr_results',
        content_rowid='rowid'
    );
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS ocr_results_fts;")
    op.execute("DROP TABLE IF EXISTS events_fts;")
    op.execute("DROP TABLE IF EXISTS observations_fts;")
