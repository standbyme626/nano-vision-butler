-- =========================================================
-- Vision Butler v5
-- SQLite schema bootstrap (T1)
-- =========================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
PRAGMA busy_timeout = 5000;

-- 001_init_core.sql
CREATE TABLE IF NOT EXISTS users (
    id                TEXT PRIMARY KEY,
    telegram_user_id  TEXT NOT NULL UNIQUE,
    telegram_chat_id  TEXT,
    display_name      TEXT,
    username          TEXT,
    role              TEXT NOT NULL DEFAULT 'viewer',
    is_allowed        INTEGER NOT NULL DEFAULT 1 CHECK (is_allowed IN (0, 1)),
    media_scope       TEXT DEFAULT 'all',
    note              TEXT,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS devices (
    id                TEXT PRIMARY KEY,
    device_id         TEXT NOT NULL UNIQUE,
    camera_id         TEXT NOT NULL UNIQUE,
    device_name       TEXT,
    api_key_hash      TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'offline'
                      CHECK (status IN ('online', 'offline', 'degraded')),
    ip_addr           TEXT,
    firmware_version  TEXT,
    model_version     TEXT,
    temperature       REAL,
    cpu_load          REAL,
    npu_load          REAL,
    free_mem_mb       INTEGER,
    camera_fps        INTEGER,
    last_seen         TEXT,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS observations (
    id                TEXT PRIMARY KEY,
    device_id         TEXT NOT NULL,
    camera_id         TEXT NOT NULL,
    zone_id           TEXT,
    object_name       TEXT,
    object_class      TEXT,
    track_id          TEXT,
    confidence        REAL,
    state_hint        TEXT,
    observed_at       TEXT NOT NULL,
    fresh_until       TEXT,
    source_event_id   TEXT,
    snapshot_uri      TEXT,
    clip_uri          TEXT,
    ocr_text          TEXT,
    visibility_scope  TEXT DEFAULT 'private',
    raw_payload_json  TEXT,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS events (
    id                TEXT PRIMARY KEY,
    observation_id    TEXT,
    event_type        TEXT NOT NULL,
    category          TEXT NOT NULL DEFAULT 'event'
                      CHECK (category IN ('event', 'episode')),
    importance        INTEGER NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
    camera_id         TEXT,
    zone_id           TEXT,
    object_name       TEXT,
    summary           TEXT NOT NULL,
    payload_json      TEXT,
    event_at          TEXT NOT NULL,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (observation_id) REFERENCES observations(id) ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS object_states (
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
    summary           TEXT,
    updated_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS zone_states (
    id                TEXT PRIMARY KEY,
    camera_id         TEXT NOT NULL,
    zone_id           TEXT NOT NULL,
    state_value       TEXT NOT NULL
                      CHECK (state_value IN ('occupied', 'empty', 'likely_occupied', 'unknown')),
    state_confidence  REAL NOT NULL DEFAULT 0.0,
    observed_at       TEXT,
    fresh_until       TEXT,
    is_stale          INTEGER NOT NULL DEFAULT 0 CHECK (is_stale IN (0, 1)),
    evidence_count    INTEGER NOT NULL DEFAULT 0,
    source_layer      TEXT DEFAULT 'state',
    summary           TEXT,
    updated_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS media_items (
    id                TEXT PRIMARY KEY,
    owner_type        TEXT NOT NULL
                      CHECK (owner_type IN ('observation', 'event', 'ocr', 'manual')),
    owner_id          TEXT NOT NULL,
    media_type        TEXT NOT NULL
                      CHECK (media_type IN ('image', 'video', 'crop')),
    uri               TEXT NOT NULL,
    local_path        TEXT NOT NULL,
    mime_type         TEXT,
    duration_sec      INTEGER,
    width             INTEGER,
    height            INTEGER,
    visibility_scope  TEXT DEFAULT 'private',
    sha256            TEXT,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id                TEXT PRIMARY KEY,
    user_id           TEXT,
    device_id         TEXT,
    action            TEXT NOT NULL,
    target_type       TEXT,
    target_id         TEXT,
    decision          TEXT NOT NULL CHECK (decision IN ('allow', 'deny')),
    reason            TEXT,
    trace_id          TEXT,
    meta_json         TEXT,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON UPDATE CASCADE ON DELETE SET NULL,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON UPDATE CASCADE ON DELETE SET NULL
);

-- 002_aux_tables.sql
CREATE TABLE IF NOT EXISTS telegram_updates (
    id                TEXT PRIMARY KEY,
    update_id         TEXT NOT NULL UNIQUE,
    chat_id           TEXT,
    from_user_id      TEXT,
    message_type      TEXT,
    message_text      TEXT,
    received_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    processed_at      TEXT,
    status            TEXT NOT NULL DEFAULT 'received'
                      CHECK (status IN ('received', 'processed', 'failed')),
    error_message     TEXT,
    trace_id          TEXT
);

CREATE TABLE IF NOT EXISTS notification_rules (
    id                TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL,
    rule_name         TEXT NOT NULL,
    trigger_type      TEXT NOT NULL
                      CHECK (trigger_type IN ('event', 'state_change', 'device_status')),
    target_scope      TEXT,
    condition_json    TEXT NOT NULL,
    is_enabled        INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
    cooldown_sec      INTEGER NOT NULL DEFAULT 0,
    last_triggered_at TEXT,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS facts (
    id                TEXT PRIMARY KEY,
    fact_key          TEXT NOT NULL UNIQUE,
    fact_value        TEXT NOT NULL,
    fact_type         TEXT NOT NULL DEFAULT 'string',
    scope             TEXT DEFAULT 'global',
    source            TEXT,
    confidence        REAL,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS ocr_results (
    id                    TEXT PRIMARY KEY,
    source_media_id       TEXT NOT NULL,
    source_observation_id TEXT,
    ocr_mode              TEXT NOT NULL
                          CHECK (ocr_mode IN ('model_direct', 'tool_structured')),
    raw_text              TEXT,
    fields_json           TEXT,
    boxes_json            TEXT,
    language              TEXT,
    confidence            REAL,
    created_at            TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (source_media_id) REFERENCES media_items(id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (source_observation_id) REFERENCES observations(id) ON UPDATE CASCADE ON DELETE SET NULL
);

-- 003_indexes.sql
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_allowed ON users(is_allowed);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_observations_camera_time ON observations(camera_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_observations_zone_time ON observations(zone_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_observations_object_time ON observations(object_name, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_observations_track_id ON observations(track_id);
CREATE INDEX IF NOT EXISTS idx_observations_source_event ON observations(source_event_id);
CREATE INDEX IF NOT EXISTS idx_events_time ON events(event_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_type_time ON events(event_type, event_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_zone_time ON events(zone_id, event_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_object_time ON events(object_name, event_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_object_states_unique_key ON object_states(object_name, camera_id, zone_id);
CREATE INDEX IF NOT EXISTS idx_object_states_stale ON object_states(is_stale, updated_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_zone_states_unique_key ON zone_states(camera_id, zone_id);
CREATE INDEX IF NOT EXISTS idx_zone_states_stale ON zone_states(is_stale, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_media_owner ON media_items(owner_type, owner_id);
CREATE INDEX IF NOT EXISTS idx_media_created_at ON media_items(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_media_sha256 ON media_items(sha256);
CREATE INDEX IF NOT EXISTS idx_audit_user_time ON audit_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_device_time ON audit_logs(device_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_trace ON audit_logs(trace_id);
CREATE INDEX IF NOT EXISTS idx_tg_updates_status_time ON telegram_updates(status, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_tg_updates_chat_time ON telegram_updates(chat_id, received_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_rules_user_enabled ON notification_rules(user_id, is_enabled);
CREATE INDEX IF NOT EXISTS idx_facts_scope ON facts(scope);
CREATE INDEX IF NOT EXISTS idx_ocr_results_media ON ocr_results(source_media_id);
CREATE INDEX IF NOT EXISTS idx_ocr_results_observation ON ocr_results(source_observation_id);

-- 004_fts.sql
CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts
USING fts5(
    object_name,
    object_class,
    ocr_text,
    raw_payload_json,
    content='observations',
    content_rowid='rowid'
);

CREATE VIRTUAL TABLE IF NOT EXISTS events_fts
USING fts5(
    event_type,
    summary,
    payload_json,
    content='events',
    content_rowid='rowid'
);

CREATE VIRTUAL TABLE IF NOT EXISTS ocr_results_fts
USING fts5(
    raw_text,
    fields_json,
    content='ocr_results',
    content_rowid='rowid'
);

-- 005_fts_triggers.sql
CREATE TRIGGER IF NOT EXISTS observations_ai
AFTER INSERT ON observations
BEGIN
    INSERT INTO observations_fts(rowid, object_name, object_class, ocr_text, raw_payload_json)
    VALUES (new.rowid, new.object_name, new.object_class, new.ocr_text, new.raw_payload_json);
END;

CREATE TRIGGER IF NOT EXISTS observations_ad
AFTER DELETE ON observations
BEGIN
    INSERT INTO observations_fts(observations_fts, rowid, object_name, object_class, ocr_text, raw_payload_json)
    VALUES ('delete', old.rowid, old.object_name, old.object_class, old.ocr_text, old.raw_payload_json);
END;

CREATE TRIGGER IF NOT EXISTS observations_au
AFTER UPDATE ON observations
BEGIN
    INSERT INTO observations_fts(observations_fts, rowid, object_name, object_class, ocr_text, raw_payload_json)
    VALUES ('delete', old.rowid, old.object_name, old.object_class, old.ocr_text, old.raw_payload_json);

    INSERT INTO observations_fts(rowid, object_name, object_class, ocr_text, raw_payload_json)
    VALUES (new.rowid, new.object_name, new.object_class, new.ocr_text, new.raw_payload_json);
END;

CREATE TRIGGER IF NOT EXISTS events_ai
AFTER INSERT ON events
BEGIN
    INSERT INTO events_fts(rowid, event_type, summary, payload_json)
    VALUES (new.rowid, new.event_type, new.summary, new.payload_json);
END;

CREATE TRIGGER IF NOT EXISTS events_ad
AFTER DELETE ON events
BEGIN
    INSERT INTO events_fts(events_fts, rowid, event_type, summary, payload_json)
    VALUES ('delete', old.rowid, old.event_type, old.summary, old.payload_json);
END;

CREATE TRIGGER IF NOT EXISTS events_au
AFTER UPDATE ON events
BEGIN
    INSERT INTO events_fts(events_fts, rowid, event_type, summary, payload_json)
    VALUES ('delete', old.rowid, old.event_type, old.summary, old.payload_json);

    INSERT INTO events_fts(rowid, event_type, summary, payload_json)
    VALUES (new.rowid, new.event_type, new.summary, new.payload_json);
END;

CREATE TRIGGER IF NOT EXISTS ocr_results_ai
AFTER INSERT ON ocr_results
BEGIN
    INSERT INTO ocr_results_fts(rowid, raw_text, fields_json)
    VALUES (new.rowid, new.raw_text, new.fields_json);
END;

CREATE TRIGGER IF NOT EXISTS ocr_results_ad
AFTER DELETE ON ocr_results
BEGIN
    INSERT INTO ocr_results_fts(ocr_results_fts, rowid, raw_text, fields_json)
    VALUES ('delete', old.rowid, old.raw_text, old.fields_json);
END;

CREATE TRIGGER IF NOT EXISTS ocr_results_au
AFTER UPDATE ON ocr_results
BEGIN
    INSERT INTO ocr_results_fts(ocr_results_fts, rowid, raw_text, fields_json)
    VALUES ('delete', old.rowid, old.raw_text, old.fields_json);

    INSERT INTO ocr_results_fts(rowid, raw_text, fields_json)
    VALUES (new.rowid, new.raw_text, new.fields_json);
END;

-- 006_views.sql
CREATE VIEW IF NOT EXISTS world_state_view AS
SELECT
    d.camera_id,
    d.status AS device_status,
    d.last_seen,
    z.zone_id,
    z.state_value AS zone_state_value,
    z.state_confidence AS zone_state_confidence,
    z.fresh_until AS zone_fresh_until,
    z.is_stale AS zone_is_stale
FROM devices d
LEFT JOIN zone_states z
ON d.camera_id = z.camera_id;

CREATE VIEW IF NOT EXISTS active_notification_rules_view AS
SELECT
    nr.id,
    nr.user_id,
    u.telegram_chat_id,
    nr.rule_name,
    nr.trigger_type,
    nr.target_scope,
    nr.condition_json,
    nr.cooldown_sec,
    nr.last_triggered_at
FROM notification_rules nr
JOIN users u
ON nr.user_id = u.id
WHERE nr.is_enabled = 1
  AND u.is_allowed = 1;

CREATE VIEW IF NOT EXISTS recent_device_health_view AS
SELECT
    device_id,
    camera_id,
    status,
    temperature,
    cpu_load,
    npu_load,
    free_mem_mb,
    camera_fps,
    last_seen
FROM devices;

-- 007_backfill_fts.sql
INSERT INTO observations_fts(rowid, object_name, object_class, ocr_text, raw_payload_json)
SELECT rowid, object_name, object_class, ocr_text, raw_payload_json
FROM observations
WHERE rowid NOT IN (SELECT rowid FROM observations_fts);

INSERT INTO events_fts(rowid, event_type, summary, payload_json)
SELECT rowid, event_type, summary, payload_json
FROM events
WHERE rowid NOT IN (SELECT rowid FROM events_fts);

INSERT INTO ocr_results_fts(rowid, raw_text, fields_json)
SELECT rowid, raw_text, fields_json
FROM ocr_results
WHERE rowid NOT IN (SELECT rowid FROM ocr_results_fts);
