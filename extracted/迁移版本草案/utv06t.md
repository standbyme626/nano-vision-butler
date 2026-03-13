<!-- source: 迁移版本草案.md | id: utv06t -->
"""add reason_code to object_states

Revision ID: 007_20260320_add_reason_code_object_states
Revises: 006_20260313_views
Create Date: 2026-03-20 10:00:00
"""

from alembic import op

revision = "007_20260320_add_reason_code_object_states"
down_revision = "006_20260313_views"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE object_states_new (
        id TEXT PRIMARY KEY,
        object_name TEXT NOT NULL,
        camera_id TEXT,
        zone_id TEXT,
        state_value TEXT NOT NULL
            CHECK (state_value IN ('present', 'absent', 'unknown')),
        state_confidence REAL NOT NULL DEFAULT 0.0,
        observed_at TEXT,
        last_confirmed_at TEXT,
        last_changed_at TEXT,
        fresh_until TEXT,
        is_stale INTEGER NOT NULL DEFAULT 0 CHECK (is_stale IN (0, 1)),
        evidence_count INTEGER NOT NULL DEFAULT 0,
        source_layer TEXT DEFAULT 'state',
        reason_code TEXT,
        summary TEXT,
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    );
    """)

    op.execute("""
    INSERT INTO object_states_new (
        id, object_name, camera_id, zone_id, state_value,
        state_confidence, observed_at, last_confirmed_at, last_changed_at,
        fresh_until, is_stale, evidence_count, source_layer, summary, updated_at
    )
    SELECT
        id, object_name, camera_id, zone_id, state_value,
        state_confidence, observed_at, last_confirmed_at, last_changed_at,
        fresh_until, is_stale, evidence_count, source_layer, summary, updated_at
    FROM object_states;
    """)

    op.execute("DROP INDEX IF EXISTS idx_object_states_unique_key;")
    op.execute("DROP INDEX IF EXISTS idx_object_states_stale;")
    op.execute("DROP TABLE object_states;")
    op.execute("ALTER TABLE object_states_new RENAME TO object_states;")
    op.execute("""
    CREATE UNIQUE INDEX idx_object_states_unique_key
    ON object_states(object_name, camera_id, zone_id);
    """)
    op.execute("""
    CREATE INDEX idx_object_states_stale
    ON object_states(is_stale, updated_at DESC);
    """)


def downgrade():
    op.execute("""
    CREATE TABLE object_states_old (
        id TEXT PRIMARY KEY,
        object_name TEXT NOT NULL,
        camera_id TEXT,
        zone_id TEXT,
        state_value TEXT NOT NULL
            CHECK (state_value IN ('present', 'absent', 'unknown')),
        state_confidence REAL NOT NULL DEFAULT 0.0,
        observed_at TEXT,
        last_confirmed_at TEXT,
        last_changed_at TEXT,
        fresh_until TEXT,
        is_stale INTEGER NOT NULL DEFAULT 0 CHECK (is_stale IN (0, 1)),
        evidence_count INTEGER NOT NULL DEFAULT 0,
        source_layer TEXT DEFAULT 'state',
        summary TEXT,
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    );
    """)

    op.execute("""
    INSERT INTO object_states_old (
        id, object_name, camera_id, zone_id, state_value,
        state_confidence, observed_at, last_confirmed_at, last_changed_at,
        fresh_until, is_stale, evidence_count, source_layer, summary, updated_at
    )
    SELECT
        id, object_name, camera_id, zone_id, state_value,
        state_confidence, observed_at, last_confirmed_at, last_changed_at,
        fresh_until, is_stale, evidence_count, source_layer, summary, updated_at
    FROM object_states;
    """)

    op.execute("DROP INDEX IF EXISTS idx_object_states_unique_key;")
    op.execute("DROP INDEX IF EXISTS idx_object_states_stale;")
    op.execute("DROP TABLE object_states;")
    op.execute("ALTER TABLE object_states_old RENAME TO object_states;")
    op.execute("""
    CREATE UNIQUE INDEX idx_object_states_unique_key
    ON object_states(object_name, camera_id, zone_id);
    """)
    op.execute("""
    CREATE INDEX idx_object_states_stale
    ON object_states(is_stale, updated_at DESC);
    """)
