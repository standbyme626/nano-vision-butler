# 第二部分：迁移版本草案

这里我给你两种组织方式：

1. **纯 SQL 版本**：适合你现在直接落地
2. **Alembic 版本骨架**：适合你以后把它接到 Python 项目迁移体系里

Alembic 官方文档说明，revision 脚本的标准结构就是 `upgrade()` / `downgrade()`；如果你不想直接执行变更，还可以用 `--sql` 输出离线 SQL。([alembic.sqlalchemy.org](https://alembic.sqlalchemy.org/en/latest/tutorial.html?utm_source=chatgpt.com)) ([alembic.sqlalchemy.org](https://alembic.sqlalchemy.org/en/latest/offline.html?utm_source=chatgpt.com))

---

## A. 纯 SQL 迁移版本草案

我建议你按下面顺序切文件。

---

### `001_init_core.sql`

```text id="ztgxgh"
BEGIN;

PRAGMA foreign_keys = ON;

-- users
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

-- devices
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

-- observations
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

-- events
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

-- object_states
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

-- zone_states
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

-- media_items
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

-- audit_logs
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
```

---

### `002_aux_tables.sql`

```text id="qmg8kv"
BEGIN;

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
    id                TEXT PRIMARY KEY,
    source_media_id   TEXT NOT NULL,
    source_observation_id TEXT,
    ocr_mode          TEXT NOT NULL
                      CHECK (ocr_mode IN ('model_direct', 'tool_structured')),
    raw_text          TEXT,
    fields_json       TEXT,
    boxes_json        TEXT,
    language          TEXT,
    confidence        REAL,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (source_media_id) REFERENCES media_items(id) ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (source_observation_id) REFERENCES observations(id) ON UPDATE CASCADE ON DELETE SET NULL
);

COMMIT;
```

---

### `003_indexes.sql`

```text id="rmx7x5"
BEGIN;

CREATE INDEX IF NOT EXISTS idx_users_role
ON users(role);

CREATE INDEX IF NOT EXISTS idx_users_allowed
ON users(is_allowed);

CREATE INDEX IF NOT EXISTS idx_devices_status
ON devices(status);

CREATE INDEX IF NOT EXISTS idx_devices_last_seen
ON devices(last_seen DESC);

CREATE INDEX IF NOT EXISTS idx_observations_camera_time
ON observations(camera_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_observations_zone_time
ON observations(zone_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_observations_object_time
ON observations(object_name, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_observations_track_id
ON observations(track_id);

CREATE INDEX IF NOT EXISTS idx_observations_source_event
ON observations(source_event_id);

CREATE INDEX IF NOT EXISTS idx_events_time
ON events(event_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_type_time
ON events(event_type, event_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_zone_time
ON events(zone_id, event_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_object_time
ON events(object_name, event_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_object_states_unique_key
ON object_states(object_name, camera_id, zone_id);

CREATE INDEX IF NOT EXISTS idx_object_states_stale
ON object_states(is_stale, updated_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_zone_states_unique_key
ON zone_states(camera_id, zone_id);

CREATE INDEX IF NOT EXISTS idx_zone_states_stale
ON zone_states(is_stale, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_media_owner
ON media_items(owner_type, owner_id);

CREATE INDEX IF NOT EXISTS idx_media_created_at
ON media_items(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_media_sha256
ON media_items(sha256);

CREATE INDEX IF NOT EXISTS idx_audit_user_time
ON audit_logs(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_device_time
ON audit_logs(device_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_trace
ON audit_logs(trace_id);

CREATE INDEX IF NOT EXISTS idx_tg_updates_status_time
ON telegram_updates(status, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_tg_updates_chat_time
ON telegram_updates(chat_id, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_notification_rules_user_enabled
ON notification_rules(user_id, is_enabled);

CREATE INDEX IF NOT EXISTS idx_facts_scope
ON facts(scope);

CREATE INDEX IF NOT EXISTS idx_ocr_results_media
ON ocr_results(source_media_id);

CREATE INDEX IF NOT EXISTS idx_ocr_results_observation
ON ocr_results(source_observation_id);

COMMIT;
```

---

### `004_fts.sql`

```text id="94xvgw"
BEGIN;

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

COMMIT;
```

---

### `005_fts_triggers.sql`

```text id="xjlwm9"
BEGIN;

-- observations_fts triggers
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

-- events_fts triggers
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

-- ocr_results_fts triggers
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

COMMIT;
```

---

### `006_views_and_touch_triggers.sql`

```text id="27ucay"
BEGIN;

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

COMMIT;
```

---

### `007_backfill_fts.sql`

```text id="h4b5yz"
BEGIN;

INSERT INTO observations_fts(rowid, object_name, object_class, ocr_text, raw_payload_json)
SELECT rowid, object_name, object_class, ocr_text, raw_payload_json
FROM observations;

INSERT INTO events_fts(rowid, event_type, summary, payload_json)
SELECT rowid, event_type, summary, payload_json
FROM events;

INSERT INTO ocr_results_fts(rowid, raw_text, fields_json)
SELECT rowid, raw_text, fields_json
FROM ocr_results;

COMMIT;
```

---

## B. 示例“重建表”迁移草案

SQLite 的复杂 schema 变更，官方推荐的安全路线就是“新表 → 拷贝 → 删除旧表 → 重命名 → 重建索引/视图/触发器”。([sqlite.org](https://sqlite.org/lang_altertable.html?utm_source=chatgpt.com))

下面给你一个**给 `object_states` 增加 `reason_code` 字段**的示例迁移：

### `008_add_reason_code_to_object_states.sql`

```text id="2tpvwv"
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
```

---

# 第三部分：Alembic 版本草案

Alembic 是轻量迁移工具，revision 文件里写 `upgrade()` / `downgrade()`；也支持 autogenerate 和离线 SQL 输出。([alembic.sqlalchemy.org](https://alembic.sqlalchemy.org/en/latest/?utm_source=chatgpt.com)) ([alembic.sqlalchemy.org](https://alembic.sqlalchemy.org/en/latest/autogenerate.html?utm_source=chatgpt.com))

如果你要兼顾“现在是 SQLite + 手写 SQL，未来可接 SQLAlchemy/Alembic”，我建议迁移目录这么组织：

```text id="d8484b"
migrations/
├─ env.py
├─ script.py.mako
└─ versions/
   ├─ 001_20260313_init_core.py
   ├─ 002_20260313_aux_tables.py
   ├─ 003_20260313_indexes.py
   ├─ 004_20260313_fts.py
   ├─ 005_20260313_fts_triggers.py
   ├─ 006_20260313_views.py
   └─ 007_20260320_add_reason_code_object_states.py
```

---

## 1）`001_20260313_init_core.py`

```text id="ezqk0t"
"""init core tables

Revision ID: 001_20260313_init_core
Revises: 
Create Date: 2026-03-13 10:00:00
"""

from alembic import op

revision = "001_20260313_init_core"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        telegram_user_id TEXT NOT NULL UNIQUE,
        telegram_chat_id TEXT,
        display_name TEXT,
        username TEXT,
        role TEXT NOT NULL DEFAULT 'viewer',
        is_allowed INTEGER NOT NULL DEFAULT 1 CHECK (is_allowed IN (0, 1)),
        media_scope TEXT DEFAULT 'all',
        note TEXT,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS devices (
        id TEXT PRIMARY KEY,
        device_id TEXT NOT NULL UNIQUE,
        camera_id TEXT NOT NULL UNIQUE,
        device_name TEXT,
        api_key_hash TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'offline'
            CHECK (status IN ('online', 'offline', 'degraded')),
        ip_addr TEXT,
        firmware_version TEXT,
        model_version TEXT,
        temperature REAL,
        cpu_load REAL,
        npu_load REAL,
        free_mem_mb INTEGER,
        camera_fps INTEGER,
        last_seen TEXT,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS observations (
        id TEXT PRIMARY KEY,
        device_id TEXT NOT NULL,
        camera_id TEXT NOT NULL,
        zone_id TEXT,
        object_name TEXT,
        object_class TEXT,
        track_id TEXT,
        confidence REAL,
        state_hint TEXT,
        observed_at TEXT NOT NULL,
        fresh_until TEXT,
        source_event_id TEXT,
        snapshot_uri TEXT,
        clip_uri TEXT,
        ocr_text TEXT,
        visibility_scope TEXT DEFAULT 'private',
        raw_payload_json TEXT,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        FOREIGN KEY (device_id) REFERENCES devices(device_id) ON UPDATE CASCADE ON DELETE RESTRICT
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY,
        observation_id TEXT,
        event_type TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'event'
            CHECK (category IN ('event', 'episode')),
        importance INTEGER NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
        camera_id TEXT,
        zone_id TEXT,
        object_name TEXT,
        summary TEXT NOT NULL,
        payload_json TEXT,
        event_at TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        FOREIGN KEY (observation_id) REFERENCES observations(id) ON UPDATE CASCADE ON DELETE SET NULL
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS object_states (
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
    CREATE TABLE IF NOT EXISTS zone_states (
        id TEXT PRIMARY KEY,
        camera_id TEXT NOT NULL,
        zone_id TEXT NOT NULL,
        state_value TEXT NOT NULL
            CHECK (state_value IN ('occupied', 'empty', 'likely_occupied', 'unknown')),
        state_confidence REAL NOT NULL DEFAULT 0.0,
        observed_at TEXT,
        fresh_until TEXT,
        is_stale INTEGER NOT NULL DEFAULT 0 CHECK (is_stale IN (0, 1)),
        evidence_count INTEGER NOT NULL DEFAULT 0,
        source_layer TEXT DEFAULT 'state',
        summary TEXT,
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS media_items (
        id TEXT PRIMARY KEY,
        owner_type TEXT NOT NULL
            CHECK (owner_type IN ('observation', 'event', 'ocr', 'manual')),
        owner_id TEXT NOT NULL,
        media_type TEXT NOT NULL
            CHECK (media_type IN ('image', 'video', 'crop')),
        uri TEXT NOT NULL,
        local_path TEXT NOT NULL,
        mime_type TEXT,
        duration_sec INTEGER,
        width INTEGER,
        height INTEGER,
        visibility_scope TEXT DEFAULT 'private',
        sha256 TEXT,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        device_id TEXT,
        action TEXT NOT NULL,
        target_type TEXT,
        target_id TEXT,
        decision TEXT NOT NULL CHECK (decision IN ('allow', 'deny')),
        reason TEXT,
        trace_id TEXT,
        meta_json TEXT,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        FOREIGN KEY (user_id) REFERENCES users(id) ON UPDATE CASCADE ON DELETE SET NULL,
        FOREIGN KEY (device_id) REFERENCES devices(device_id) ON UPDATE CASCADE ON DELETE SET NULL
    );
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS audit_logs;")
    op.execute("DROP TABLE IF EXISTS media_items;")
    op.execute("DROP TABLE IF EXISTS zone_states;")
    op.execute("DROP TABLE IF EXISTS object_states;")
    op.execute("DROP TABLE IF EXISTS events;")
    op.execute("DROP TABLE IF EXISTS observations;")
    op.execute("DROP TABLE IF EXISTS devices;")
    op.execute("DROP TABLE IF EXISTS users;")
```

---

## 2）`002_20260313_aux_tables.py`

```text id="9f7n7y"
"""aux tables

Revision ID: 002_20260313_aux_tables
Revises: 001_20260313_init_core
Create Date: 2026-03-13 10:10:00
"""

from alembic import op

revision = "002_20260313_aux_tables"
down_revision = "001_20260313_init_core"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS telegram_updates (
        id TEXT PRIMARY KEY,
        update_id TEXT NOT NULL UNIQUE,
        chat_id TEXT,
        from_user_id TEXT,
        message_type TEXT,
        message_text TEXT,
        received_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        processed_at TEXT,
        status TEXT NOT NULL DEFAULT 'received'
            CHECK (status IN ('received', 'processed', 'failed')),
        error_message TEXT,
        trace_id TEXT
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS notification_rules (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        rule_name TEXT NOT NULL,
        trigger_type TEXT NOT NULL
            CHECK (trigger_type IN ('event', 'state_change', 'device_status')),
        target_scope TEXT,
        condition_json TEXT NOT NULL,
        is_enabled INTEGER NOT NULL DEFAULT 1 CHECK (is_enabled IN (0, 1)),
        cooldown_sec INTEGER NOT NULL DEFAULT 0,
        last_triggered_at TEXT,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        FOREIGN KEY (user_id) REFERENCES users(id) ON UPDATE CASCADE ON DELETE CASCADE
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS facts (
        id TEXT PRIMARY KEY,
        fact_key TEXT NOT NULL UNIQUE,
        fact_value TEXT NOT NULL,
        fact_type TEXT NOT NULL DEFAULT 'string',
        scope TEXT DEFAULT 'global',
        source TEXT,
        confidence REAL,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
    );
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS ocr_results (
        id TEXT PRIMARY KEY,
        source_media_id TEXT NOT NULL,
        source_observation_id TEXT,
        ocr_mode TEXT NOT NULL
            CHECK (ocr_mode IN ('model_direct', 'tool_structured')),
        raw_text TEXT,
        fields_json TEXT,
        boxes_json TEXT,
        language TEXT,
        confidence REAL,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
        FOREIGN KEY (source_media_id) REFERENCES media_items(id) ON UPDATE CASCADE ON DELETE CASCADE,
        FOREIGN KEY (source_observation_id) REFERENCES observations(id) ON UPDATE CASCADE ON DELETE SET NULL
    );
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS ocr_results;")
    op.execute("DROP TABLE IF EXISTS facts;")
    op.execute("DROP TABLE IF EXISTS notification_rules;")
    op.execute("DROP TABLE IF EXISTS telegram_updates;")
```

---

## 3）`003_20260313_indexes.py`

```text id="ouw0b1"
"""indexes

Revision ID: 003_20260313_indexes
Revises: 002_20260313_aux_tables
Create Date: 2026-03-13 10:20:00
"""

from alembic import op

revision = "003_20260313_indexes"
down_revision = "002_20260313_aux_tables"
branch_labels = None
depends_on = None


def upgrade():
    statements = [
        "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);",
        "CREATE INDEX IF NOT EXISTS idx_users_allowed ON users(is_allowed);",
        "CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);",
        "CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen DESC);",
        "CREATE INDEX IF NOT EXISTS idx_observations_camera_time ON observations(camera_id, observed_at DESC);",
        "CREATE INDEX IF NOT EXISTS idx_observations_zone_time ON observations(zone_id, observed_at DESC);",
        "CREATE INDEX IF NOT EXISTS idx_observations_object_time ON observations(object_name, observed_at DESC);",
        "CREATE INDEX IF NOT EXISTS idx_observations_track_id ON observations(track_id);",
        "CREATE INDEX IF NOT EXISTS idx_observations_source_event ON observations(source_event_id);",
        "CREATE INDEX IF NOT EXISTS idx_events_time ON events(event_at DESC);",
        "CREATE INDEX IF NOT EXISTS idx_events_type_time ON events(event_type, event_at DESC);",
        "CREATE INDEX IF NOT EXISTS idx_events_zone_time ON events(zone_id, event_at DESC);",
        "CREATE INDEX IF NOT EXISTS idx_events_object_time ON events(object_name, event_at DESC);",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_object_states_unique_key ON object_states(object_name, camera_id, zone_id);",
        "CREATE INDEX IF NOT EXISTS idx_object_states_stale ON object_states(is_stale, updated_at DESC);",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_zone_states_unique_key ON zone_states(camera_id, zone_id);",
        "CREATE INDEX IF NOT EXISTS idx_zone_states_stale ON zone_states(is_stale, updated_at DESC);",
        "CREATE INDEX IF NOT EXISTS idx_media_owner ON media_items(owner_type, owner_id);",
        "CREATE INDEX IF NOT EXISTS idx_media_created_at ON media_items(created_at DESC);",
        "CREATE INDEX IF NOT EXISTS idx_media_sha256 ON media_items(sha256);",
        "CREATE INDEX IF NOT EXISTS idx_audit_user_time ON audit_logs(user_id, created_at DESC);",
        "CREATE INDEX IF NOT EXISTS idx_audit_device_time ON audit_logs(device_id, created_at DESC);",
        "CREATE INDEX IF NOT EXISTS idx_audit_trace ON audit_logs(trace_id);",
        "CREATE INDEX IF NOT EXISTS idx_tg_updates_status_time ON telegram_updates(status, received_at DESC);",
        "CREATE INDEX IF NOT EXISTS idx_tg_updates_chat_time ON telegram_updates(chat_id, received_at DESC);",
        "CREATE INDEX IF NOT EXISTS idx_notification_rules_user_enabled ON notification_rules(user_id, is_enabled);",
        "CREATE INDEX IF NOT EXISTS idx_facts_scope ON facts(scope);",
        "CREATE INDEX IF NOT EXISTS idx_ocr_results_media ON ocr_results(source_media_id);",
        "CREATE INDEX IF NOT EXISTS idx_ocr_results_observation ON ocr_results(source_observation_id);",
    ]
    for stmt in statements:
        op.execute(stmt)


def downgrade():
    statements = [
        "DROP INDEX IF EXISTS idx_ocr_results_observation;",
        "DROP INDEX IF EXISTS idx_ocr_results_media;",
        "DROP INDEX IF EXISTS idx_facts_scope;",
        "DROP INDEX IF EXISTS idx_notification_rules_user_enabled;",
        "DROP INDEX IF EXISTS idx_tg_updates_chat_time;",
        "DROP INDEX IF EXISTS idx_tg_updates_status_time;",
        "DROP INDEX IF EXISTS idx_audit_trace;",
        "DROP INDEX IF EXISTS idx_audit_device_time;",
        "DROP INDEX IF EXISTS idx_audit_user_time;",
        "DROP INDEX IF EXISTS idx_media_sha256;",
        "DROP INDEX IF EXISTS idx_media_created_at;",
        "DROP INDEX IF EXISTS idx_media_owner;",
        "DROP INDEX IF EXISTS idx_zone_states_stale;",
        "DROP INDEX IF EXISTS idx_zone_states_unique_key;",
        "DROP INDEX IF EXISTS idx_object_states_stale;",
        "DROP INDEX IF EXISTS idx_object_states_unique_key;",
        "DROP INDEX IF EXISTS idx_events_object_time;",
        "DROP INDEX IF EXISTS idx_events_zone_time;",
        "DROP INDEX IF EXISTS idx_events_type_time;",
        "DROP INDEX IF EXISTS idx_events_time;",
        "DROP INDEX IF EXISTS idx_observations_source_event;",
        "DROP INDEX IF EXISTS idx_observations_track_id;",
        "DROP INDEX IF EXISTS idx_observations_object_time;",
        "DROP INDEX IF EXISTS idx_observations_zone_time;",
        "DROP INDEX IF EXISTS idx_observations_camera_time;",
        "DROP INDEX IF EXISTS idx_devices_last_seen;",
        "DROP INDEX IF EXISTS idx_devices_status;",
        "DROP INDEX IF EXISTS idx_users_allowed;",
        "DROP INDEX IF EXISTS idx_users_role;",
    ]
    for stmt in statements:
        op.execute(stmt)
```

---

## 4）`004_20260313_fts.py`

```text id="orm4f2"
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
```

---

## 5）`005_20260313_fts_triggers.py`

```text id="ggpej8"
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
```

---

## 6）`006_20260313_views.py`

```text id="s0okkv"
"""views

Revision ID: 006_20260313_views
Revises: 005_20260313_fts_triggers
Create Date: 2026-03-13 10:50:00
"""

from alembic import op

revision = "006_20260313_views"
down_revision = "005_20260313_fts_triggers"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
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
    """)

    op.execute("""
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
    """)


def downgrade():
    op.execute("DROP VIEW IF EXISTS active_notification_rules_view;")
    op.execute("DROP VIEW IF EXISTS world_state_view;")
```

---

## 7）`007_20260320_add_reason_code_object_states.py`

这个 revision 演示 SQLite 复杂变更的“重建表”方式。

```text id="utv06t"
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
```

---

# 第四部分：推荐的项目书说明文字

你可以把下面这段直接放进项目书的“数据库迁移策略”小节：

> 本项目采用“SQLite 正式单机落库 + FTS5 全文检索 + 版本化迁移”的数据库策略。对于建库初期，推荐使用按编号递增的 SQL 迁移文件完成主表、索引、FTS、触发器与视图初始化；对于后续 Python 服务化阶段，推荐引入 Alembic，以 revision 文件形式维护 `upgrade()` 与 `downgrade()`。对于 SQLite 中较复杂的 schema 变更，不依赖直接 `ALTER TABLE`，而采用“新表 → 数据迁移 → 删除旧表 → 重命名 → 重建索引/视图/触发器”的保守迁移策略。([sqlite.org](https://sqlite.org/lang_altertable.html?utm_source=chatgpt.com)) ([alembic.sqlalchemy.org](https://alembic.sqlalchemy.org/en/latest/tutorial.html?utm_source=chatgpt.com))

如果你愿意，我下一步可以继续把这些内容收成一个**完整的 `schema.sql` 与 `migrations/README.md` 成品版文本**，让你直接复制进仓库。


可以，下面我把你要的两份**成品版文本**一次性发全：

1. `schema.sql`
2. `migrations/README.md`

这两份内容是按 **SQLite 正式单机落库 + FTS5 全文检索 + 版本化迁移** 的思路整理的。SQLite 官方文档明确要求外键约束需要显式开启，FTS5 通过虚拟表实现全文检索，而复杂表结构变更通常需要采用“建新表、迁数据、删旧表、重命名、重建索引/触发器”的保守方式；Alembic 官方文档则明确支持 revision 脚本、`--autogenerate` 和离线 SQL 输出。([sqlite.org](https://sqlite.org/foreignkeys.html?utm_source=chatgpt.com)) ([sqlite.org](https://sqlite.org/fts5.html?utm_source=chatgpt.com)) ([sqlite.org](https://sqlite.org/lang_altertable.html?utm_source=chatgpt.com)) ([alembic.sqlalchemy.org](https://alembic.sqlalchemy.org/en/latest/tutorial.html?utm_source=chatgpt.com)) ([alembic.sqlalchemy.org](https://alembic.sqlalchemy.org/en/latest/offline.html?utm_source=chatgpt.com))

---

## `schema.sql`

```text id="kp4m8i"
-- =========================================================
-- Vision Butler v5
-- Final SQLite Schema
-- =========================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
PRAGMA busy_timeout = 5000;

-- =========================================================
-- Core tables
-- =========================================================

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
    reason_code       TEXT,
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
    reason_code       TEXT,
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

-- =========================================================
-- Auxiliary tables
-- =========================================================

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

-- =========================================================
-- Indexes
-- =========================================================

CREATE INDEX IF NOT EXISTS idx_users_role
ON users(role);

CREATE INDEX IF NOT EXISTS idx_users_allowed
ON users(is_allowed);

CREATE INDEX IF NOT EXISTS idx_devices_status
ON devices(status);

CREATE INDEX IF NOT EXISTS idx_devices_last_seen
ON devices(last_seen DESC);

CREATE INDEX IF NOT EXISTS idx_observations_camera_time
ON observations(camera_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_observations_zone_time
ON observations(zone_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_observations_object_time
ON observations(object_name, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_observations_track_id
ON observations(track_id);

CREATE INDEX IF NOT EXISTS idx_observations_source_event
ON observations(source_event_id);

CREATE INDEX IF NOT EXISTS idx_events_time
ON events(event_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_type_time
ON events(event_type, event_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_zone_time
ON events(zone_id, event_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_object_time
ON events(object_name, event_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_object_states_unique_key
ON object_states(object_name, camera_id, zone_id);

CREATE INDEX IF NOT EXISTS idx_object_states_stale
ON object_states(is_stale, updated_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_zone_states_unique_key
ON zone_states(camera_id, zone_id);

CREATE INDEX IF NOT EXISTS idx_zone_states_stale
ON zone_states(is_stale, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_media_owner
ON media_items(owner_type, owner_id);

CREATE INDEX IF NOT EXISTS idx_media_created_at
ON media_items(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_media_sha256
ON media_items(sha256);

CREATE INDEX IF NOT EXISTS idx_audit_user_time
ON audit_logs(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_device_time
ON audit_logs(device_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_trace
ON audit_logs(trace_id);

CREATE INDEX IF NOT EXISTS idx_tg_updates_status_time
ON telegram_updates(status, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_tg_updates_chat_time
ON telegram_updates(chat_id, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_notification_rules_user_enabled
ON notification_rules(user_id, is_enabled);

CREATE INDEX IF NOT EXISTS idx_facts_scope
ON facts(scope);

CREATE INDEX IF NOT EXISTS idx_ocr_results_media
ON ocr_results(source_media_id);

CREATE INDEX IF NOT EXISTS idx_ocr_results_observation
ON ocr_results(source_observation_id);

-- =========================================================
-- FTS5 virtual tables
-- =========================================================

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

-- =========================================================
-- FTS sync triggers
-- =========================================================

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

-- =========================================================
-- updated_at touch triggers
-- =========================================================

CREATE TRIGGER IF NOT EXISTS users_set_updated_at
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
    UPDATE users
    SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER IF NOT EXISTS devices_set_updated_at
AFTER UPDATE ON devices
FOR EACH ROW
BEGIN
    UPDATE devices
    SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER IF NOT EXISTS object_states_set_updated_at
AFTER UPDATE ON object_states
FOR EACH ROW
BEGIN
    UPDATE object_states
    SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER IF NOT EXISTS zone_states_set_updated_at
AFTER UPDATE ON zone_states
FOR EACH ROW
BEGIN
    UPDATE zone_states
    SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER IF NOT EXISTS notification_rules_set_updated_at
AFTER UPDATE ON notification_rules
FOR EACH ROW
BEGIN
    UPDATE notification_rules
    SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    WHERE rowid = NEW.rowid;
END;

CREATE TRIGGER IF NOT EXISTS facts_set_updated_at
AFTER UPDATE ON facts
FOR EACH ROW
BEGIN
    UPDATE facts
    SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    WHERE rowid = NEW.rowid;
END;

-- =========================================================
-- Views
-- =========================================================

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
```

---

## `migrations/README.md`

```text id="87e4jg"
# Vision Butler v5 数据库迁移说明

本目录用于维护 Vision Butler v5 的数据库版本演进。

当前正式数据库策略为：

- SQLite 作为正式单机数据层
- FTS5 作为 observation / event / OCR 文本的全文检索层
- SQL 文件可直接执行
- 可选接入 Alembic 作为 Python 项目中的迁移调度器

---

## 1. 目录建议

推荐结构如下：

migrations/
├─ README.md
├─ sql/
│  ├─ 001_init_core.sql
│  ├─ 002_aux_tables.sql
│  ├─ 003_indexes.sql
│  ├─ 004_fts.sql
│  ├─ 005_fts_triggers.sql
│  ├─ 006_views.sql
│  └─ 007_backfill_fts.sql
├─ alembic.ini
├─ env.py
└─ versions/
   ├─ 001_20260313_init_core.py
   ├─ 002_20260313_aux_tables.py
   ├─ 003_20260313_indexes.py
   ├─ 004_20260313_fts.py
   ├─ 005_20260313_fts_triggers.py
   ├─ 006_20260313_views.py
   └─ 007_20260320_add_reason_code_object_states.py

---

## 2. 版本命名规则

### SQL 文件命名
建议使用：

- `001_init_core.sql`
- `002_aux_tables.sql`
- `003_indexes.sql`

规则：
- 前缀为三位顺序号
- 名称简洁描述本次变更目标
- 文件按顺序执行

### Alembic revision 命名
建议使用：

- `001_20260313_init_core`
- `007_20260320_add_reason_code_object_states`

规则：
- 保留顺序感
- 带日期便于排查
- revision 文件名与内部 revision 标识保持一致

---

## 3. 首次初始化方式

### 方案 A：直接执行 schema.sql
适用于：
- 本地开发初始化
- 测试环境快速建库
- 单机部署

示例：

sqlite3 vision_butler.db < schema.sql

### 方案 B：按 SQL 迁移顺序执行
适用于：
- 更可控的初始化
- 要保留明确升级过程

示例：

sqlite3 vision_butler.db < migrations/sql/001_init_core.sql
sqlite3 vision_butler.db < migrations/sql/002_aux_tables.sql
sqlite3 vision_butler.db < migrations/sql/003_indexes.sql
sqlite3 vision_butler.db < migrations/sql/004_fts.sql
sqlite3 vision_butler.db < migrations/sql/005_fts_triggers.sql
sqlite3 vision_butler.db < migrations/sql/006_views.sql
sqlite3 vision_butler.db < migrations/sql/007_backfill_fts.sql

---

## 4. Alembic 使用方式

Alembic 适用于：
- Python 服务项目
- 需要标准化 revision 管理
- 需要 `upgrade` / `downgrade`
- 需要 CI 中验证迁移脚本

### 初始化
在项目中执行：

alembic init migrations

然后将本 README 中建议的 `versions/` 文件放入对应目录。

### 查看当前版本
alembic current

### 升级到最新
alembic upgrade head

### 回退一个版本
alembic downgrade -1

### 回退到指定 revision
alembic downgrade 003_20260313_indexes

### 生成新 revision
alembic revision -m "add xyz table"

### 自动生成候选迁移
alembic revision --autogenerate -m "sync models"

注意：
- `--autogenerate` 只生成候选迁移
- 必须人工审核
- SQLite 下复杂表结构变更不要盲信 autogenerate 输出

### 生成离线 SQL
alembic upgrade head --sql > migrations/out/upgrade.sql

---

## 5. SQLite 迁移原则

SQLite 是正式数据库，但它不是 PostgreSQL。

对于以下情况，不要优先尝试“直接 ALTER”：

- 删除列
- 重命名列后伴随约束变化
- 修改 CHECK 约束
- 变更联合唯一约束
- 变更列类型语义
- 调整外键关系

推荐方式是：

1. 创建新表
2. 把旧表数据复制到新表
3. 删除旧表
4. 重命名新表
5. 重建索引
6. 重建视图
7. 重建触发器
8. 如涉及 FTS，重建或回填 FTS 数据

这一原则适用于：
- `object_states`
- `zone_states`
- `observations`
- `events`
- `ocr_results`

---

## 6. FTS5 维护原则

项目使用 FTS5 建立三类全文索引：

- `observations_fts`
- `events_fts`
- `ocr_results_fts`

### 原则 1：FTS 表不是普通业务表
不要直接对 FTS 表执行业务写入，统一通过内容表与同步触发器维护。

### 原则 2：先建内容表，再建 FTS 表，再建同步触发器
推荐顺序：

1. 建 observations / events / ocr_results
2. 建 observations_fts / events_fts / ocr_results_fts
3. 建 insert / update / delete 触发器
4. 执行回填脚本

### 原则 3：已有历史数据时必须执行回填
如果 FTS 表晚于内容表创建，必须手工补一遍：

INSERT INTO observations_fts(...) SELECT ... FROM observations;
INSERT INTO events_fts(...) SELECT ... FROM events;
INSERT INTO ocr_results_fts(...) SELECT ... FROM ocr_results;

---

## 7. 推荐迁移顺序

首版推荐顺序固定如下：

1. `001_init_core.sql`
2. `002_aux_tables.sql`
3. `003_indexes.sql`
4. `004_fts.sql`
5. `005_fts_triggers.sql`
6. `006_views.sql`
7. `007_backfill_fts.sql`

后续新增版本按照递增顺序继续添加，例如：

- `008_add_reason_code_to_object_states.sql`
- `009_add_notification_delivery_log.sql`
- `010_add_media_retention_policy.sql`

---

## 8. 回滚策略

### 简单对象
以下对象可直接 DROP 后重建：
- 视图
- 普通索引
- 触发器
- FTS 表（前提是可由内容表重建）

### 核心业务表
以下表不建议直接 DROP：
- observations
- events
- object_states
- zone_states
- devices
- users

对核心业务表做回滚时，推荐：
- 先备份数据库文件
- 在事务中执行迁移
- 对关键表使用“新表替换”回滚方式
- 如有 FTS 依赖，回滚后重新回填

---

## 9. 上线前检查清单

执行迁移前必须确认：

- `PRAGMA foreign_keys = ON`
- 当前数据库已备份
- 当前 revision 已记录
- FTS 表是否需要回填
- 视图和触发器是否受影响
- 是否存在依赖该表的 repository / service / MCP tool / skill

上线完成后必须验证：

- `alembic current` 或 schema 版本记录正确
- 主表存在
- 索引存在
- FTS 搜索可用
- 关键查询可跑通
- Telegram update 去重正常
- state / policy / OCR 查询不报错

---

## 10. 推荐版本记录方式

项目可增加一张轻量版本表：

CREATE TABLE IF NOT EXISTS schema_versions (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    note TEXT
);

每次执行 SQL 迁移后写入：

INSERT INTO schema_versions(version, note)
VALUES ('001_init_core', 'core tables created');

如果使用 Alembic，也可以只以 Alembic 的 revision 为准，不重复造轮子。

---

## 11. 迁移开发规范

### 必须做到
- 一个版本只做一类主要变更
- 每个版本都可独立阅读
- 每个版本都能解释 upgrade 和 downgrade
- SQLite 复杂变更优先重建表
- 所有索引、视图、触发器都要在迁移里显式管理

### 不建议做
- 在一版迁移里同时改很多表和很多行为
- 把业务逻辑写进 migration
- 依赖数据库自动推断
- 对 SQLite 复杂变更强行套 PostgreSQL 思路

---

## 12. 建议的 CI 检查

在 CI 中建议至少跑以下步骤：

1. 新建空数据库
2. 执行全部 SQL 迁移
3. 检查主表、索引、FTS、视图是否存在
4. 执行 smoke queries
5. 若使用 Alembic，再执行：
   - `alembic upgrade head`
   - `alembic downgrade base`
   - 再次 `alembic upgrade head`

---

## 13. 推荐 smoke queries

### 检查主表
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;

### 检查索引
SELECT name FROM sqlite_master WHERE type='index' ORDER BY name;

### 检查视图
SELECT name FROM sqlite_master WHERE type='view' ORDER BY name;

### 检查 FTS
SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_fts';

### 检查 devices
SELECT COUNT(*) FROM devices;

### 检查 observations
SELECT COUNT(*) FROM observations;

### 检查 object_states
SELECT COUNT(*) FROM object_states;

---

## 14. 最终建议

推荐采用“双轨制”：

- 仓库中保留 `schema.sql` 作为一键初始化方案
- 同时保留 `migrations/sql/` 作为可读的 SQL 迁移历史
- Python 服务侧可接入 Alembic，作为版本化升级工具
- 生产变更以“先生成 SQL，再审核，再执行”为原则

这套做法最适合当前项目：
- 单机 SQLite
- 后端 Python 服务
- 未来仍可能演进表结构
- 同时需要可读性和可维护性
```

你现在已经有了能直接放进仓库的两份成品。下一步最顺的是把前面我给你的**图注、表字段说明、SQL 草案、迁移说明**收成一份真正可交付的 Markdown 文档。
