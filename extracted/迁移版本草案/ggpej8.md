<!-- source: 迁移版本草案.md | id: ggpej8 -->
"""fts sync triggers

Revision ID: 005_20260313_fts_triggers
Revises: 004_20260313_fts
Create Date: 2026-03-13 10:40:00
"""

from alembic import op

revision = "005_20260313_fts_triggers"
down_revision = "004_20260313_fts"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TRIGGER IF NOT EXISTS observations_ai
    AFTER INSERT ON observations
    BEGIN
        INSERT INTO observations_fts(rowid, object_name, object_class, ocr_text, raw_payload_json)
        VALUES (new.rowid, new.object_name, new.object_class, new.ocr_text, new.raw_payload_json);
    END;
    """)

    op.execute("""
    CREATE TRIGGER IF NOT EXISTS observations_ad
    AFTER DELETE ON observations
    BEGIN
        INSERT INTO observations_fts(observations_fts, rowid, object_name, object_class, ocr_text, raw_payload_json)
        VALUES ('delete', old.rowid, old.object_name, old.object_class, old.ocr_text, old.raw_payload_json);
    END;
    """)

    op.execute("""
    CREATE TRIGGER IF NOT EXISTS observations_au
    AFTER UPDATE ON observations
    BEGIN
        INSERT INTO observations_fts(observations_fts, rowid, object_name, object_class, ocr_text, raw_payload_json)
        VALUES ('delete', old.rowid, old.object_name, old.object_class, old.ocr_text, old.raw_payload_json);

        INSERT INTO observations_fts(rowid, object_name, object_class, ocr_text, raw_payload_json)
        VALUES (new.rowid, new.object_name, new.object_class, new.ocr_text, new.raw_payload_json);
    END;
    """)
    # 你可以按同样模式继续补 events / ocr_results 的 FTS 触发器


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS observations_au;")
    op.execute("DROP TRIGGER IF EXISTS observations_ad;")
    op.execute("DROP TRIGGER IF EXISTS observations_ai;")
