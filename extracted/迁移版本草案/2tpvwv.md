<!-- source: 迁移版本草案.md | id: 2tpvwv -->
BEGIN;

-- 1) 建新表
CREATE TABLE object_states_new (
    id                TEXT PRIMARY KEY,
    object_name       TEXT NOT NULL,
    camera_id         TEXT,
    zone_id           TEXT,
    state_value       TEXT NOT NULL
                      CHECK (state_value IN ('present', 'absent', 'unknown')),
    state_confidence  REAL NOT NULL DEFAULT 0.0,
    observed_at       TEXT,
    last_confirmed_at TEXT,
    last_changed_at   TEXT,
    fresh_until       TEXT,
    is_stale          INTEGER NOT NULL DEFAULT 0 CHECK (is_stale IN (0, 1)),
    evidence_count    INTEGER NOT NULL DEFAULT 0,
    source_layer      TEXT DEFAULT 'state',
    reason_code       TEXT,
    summary           TEXT,
    updated_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- 2) 迁数据
INSERT INTO object_states_new (
    id,
    object_name,
    camera_id,
    zone_id,
    state_value,
    state_confidence,
    observed_at,
    last_confirmed_at,
    last_changed_at,
    fresh_until,
    is_stale,
    evidence_count,
    source_layer,
    summary,
    updated_at
)
SELECT
    id,
    object_name,
    camera_id,
    zone_id,
    state_value,
    state_confidence,
    observed_at,
    last_confirmed_at,
    last_changed_at,
    fresh_until,
    is_stale,
    evidence_count,
    source_layer,
    summary,
    updated_at
FROM object_states;

-- 3) 删除旧索引
DROP INDEX IF EXISTS idx_object_states_unique_key;
DROP INDEX IF EXISTS idx_object_states_stale;

-- 4) 删旧表
DROP TABLE object_states;

-- 5) 重命名
ALTER TABLE object_states_new RENAME TO object_states;

-- 6) 重建索引
CREATE UNIQUE INDEX idx_object_states_unique_key
ON object_states(object_name, camera_id, zone_id);

CREATE INDEX idx_object_states_stale
ON object_states(is_stale, updated_at DESC);

COMMIT;
