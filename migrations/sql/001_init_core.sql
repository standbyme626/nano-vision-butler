BEGIN;

PRAGMA foreign_keys = ON;

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

COMMIT;
