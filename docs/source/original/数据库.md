明白，你的要求是整理文档，不对项目内容做任何修改。以下是我根据你提供的最新内容整理出的“高频示例查询 SQL”和“迁移版本草案”部分，格式保持原样，仅作排版优化。

---

## 第一部分：高频示例查询 SQL

### 1）查某对象的 last_seen
```sql
-- 输入参数：
-- :object_name
-- :camera_id 可选
-- :zone_id 可选

SELECT
    o.id,
    o.object_name,
    o.object_class,
    o.camera_id,
    o.zone_id,
    o.confidence,
    o.observed_at,
    o.fresh_until,
    o.snapshot_uri,
    o.clip_uri,
    o.ocr_text
FROM observations o
WHERE o.object_name = :object_name
  AND (:camera_id IS NULL OR o.camera_id = :camera_id)
  AND (:zone_id IS NULL OR o.zone_id = :zone_id)
ORDER BY o.observed_at DESC
LIMIT 1;
```

### 2）优先查 object_state，再回退到 last_seen
```sql
-- 第一步：先查状态层
SELECT
    os.object_name,
    os.camera_id,
    os.zone_id,
    os.state_value,
    os.state_confidence,
    os.observed_at,
    os.fresh_until,
    os.is_stale,
    os.evidence_count,
    os.source_layer,
    os.summary
FROM object_states os
WHERE os.object_name = :object_name
  AND (:camera_id IS NULL OR os.camera_id = :camera_id)
  AND (:zone_id IS NULL OR os.zone_id = :zone_id)
LIMIT 1;
```

```sql
-- 第二步：如果没有 state，再回退 observation
SELECT
    o.object_name,
    o.camera_id,
    o.zone_id,
    'unknown' AS state_value,
    o.confidence AS state_confidence,
    o.observed_at,
    o.fresh_until,
    CASE
        WHEN o.fresh_until IS NOT NULL AND o.fresh_until < strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        THEN 1
        ELSE 0
    END AS is_stale,
    1 AS evidence_count,
    'observation' AS source_layer,
    'fallback from last_seen' AS summary
FROM observations o
WHERE o.object_name = :object_name
  AND (:camera_id IS NULL OR o.camera_id = :camera_id)
  AND (:zone_id IS NULL OR o.zone_id = :zone_id)
ORDER BY o.observed_at DESC
LIMIT 1;
```

### 3）查某区域最近事件
```sql
-- 输入参数：
-- :zone_id
-- :start_time
-- :end_time
-- :limit

SELECT
    e.id,
    e.event_type,
    e.category,
    e.importance,
    e.zone_id,
    e.object_name,
    e.summary,
    e.event_at
FROM events e
WHERE e.zone_id = :zone_id
  AND e.event_at >= :start_time
  AND e.event_at < :end_time
ORDER BY e.event_at DESC
LIMIT :limit;
```

### 4）查某对象最近事件
```sql
SELECT
    e.id,
    e.event_type,
    e.summary,
    e.event_at,
    e.importance,
    e.zone_id
FROM events e
WHERE e.object_name = :object_name
ORDER BY e.event_at DESC
LIMIT :limit;
```

### 5）查当前 zone_state
```sql
SELECT
    zs.camera_id,
    zs.zone_id,
    zs.state_value,
    zs.state_confidence,
    zs.observed_at,
    zs.fresh_until,
    zs.is_stale,
    zs.evidence_count,
    zs.source_layer,
    zs.summary
FROM zone_states zs
WHERE zs.camera_id = :camera_id
  AND zs.zone_id = :zone_id
LIMIT 1;
```

### 6）查 world_state 视图
```sql
SELECT
    camera_id,
    device_status,
    last_seen,
    zone_id,
    zone_state_value,
    zone_state_confidence,
    zone_fresh_until,
    zone_is_stale
FROM world_state_view
ORDER BY camera_id, zone_id;
```

### 7）查所有 stale 的对象状态
```sql
SELECT
    os.object_name,
    os.camera_id,
    os.zone_id,
    os.state_value,
    os.state_confidence,
    os.fresh_until,
    os.updated_at
FROM object_states os
WHERE os.is_stale = 1
ORDER BY os.updated_at DESC;
```

### 8）按 freshness 规则判断“现在是否 stale”（SQL 侧简版）
```sql
SELECT
    os.object_name,
    os.fresh_until,
    CASE
        WHEN os.fresh_until IS NULL THEN 1
        WHEN os.fresh_until < strftime('%Y-%m-%dT%H:%M:%fZ', 'now') THEN 1
        ELSE 0
    END AS is_stale
FROM object_states os
WHERE os.object_name = :object_name
LIMIT 1;
```

### 9）查最近快照或视频
```sql
SELECT
    m.id,
    m.owner_type,
    m.owner_id,
    m.media_type,
    m.uri,
    m.local_path,
    m.duration_sec,
    m.width,
    m.height,
    m.created_at
FROM media_items m
WHERE m.owner_type = :owner_type
  AND m.owner_id = :owner_id
ORDER BY m.created_at DESC
LIMIT :limit;
```

### 10）查 observation 对应的媒体
```sql
SELECT
    o.id AS observation_id,
    o.object_name,
    o.observed_at,
    m.id AS media_id,
    m.media_type,
    m.uri,
    m.local_path
FROM observations o
LEFT JOIN media_items m
  ON m.owner_type = 'observation'
 AND m.owner_id = o.id
WHERE o.id = :observation_id
ORDER BY m.created_at DESC;
```

### 11）查设备最近状态
```sql
SELECT
    d.device_id,
    d.camera_id,
    d.status,
    d.temperature,
    d.cpu_load,
    d.npu_load,
    d.free_mem_mb,
    d.camera_fps,
    d.last_seen
FROM devices d
WHERE d.device_id = :device_id
LIMIT 1;
```

### 12）找疑似离线设备
```sql
-- :offline_before 例如 “当前时间减去 120 秒”的 ISO8601 值

SELECT
    d.device_id,
    d.camera_id,
    d.status,
    d.last_seen
FROM devices d
WHERE d.last_seen IS NULL
   OR d.last_seen < :offline_before
ORDER BY d.last_seen ASC;
```

### 13）查启用中的通知规则
```sql
SELECT
    nr.id,
    nr.rule_name,
    nr.trigger_type,
    nr.target_scope,
    nr.condition_json,
    nr.cooldown_sec,
    nr.last_triggered_at,
    u.telegram_chat_id
FROM notification_rules nr
JOIN users u
  ON u.id = nr.user_id
WHERE nr.is_enabled = 1
  AND u.is_allowed = 1;
```

### 14）查最近审计日志
```sql
SELECT
    a.id,
    a.user_id,
    a.device_id,
    a.action,
    a.target_type,
    a.target_id,
    a.decision,
    a.reason,
    a.trace_id,
    a.created_at
FROM audit_logs a
ORDER BY a.created_at DESC
LIMIT :limit;
```

### 15）按 trace_id 查全链路
```sql
SELECT
    a.id,
    a.action,
    a.target_type,
    a.target_id,
    a.decision,
    a.reason,
    a.created_at
FROM audit_logs a
WHERE a.trace_id = :trace_id
ORDER BY a.created_at ASC;
```

### 16）Telegram update 去重写入
```sql
INSERT INTO telegram_updates (
    id,
    update_id,
    chat_id,
    from_user_id,
    message_type,
    message_text,
    status,
    trace_id
)
VALUES (
    :id,
    :update_id,
    :chat_id,
    :from_user_id,
    :message_type,
    :message_text,
    'received',
    :trace_id
)
ON CONFLICT(update_id) DO NOTHING;
```

### 17）标记 Telegram update 处理成功
```sql
UPDATE telegram_updates
SET
    status = 'processed',
    processed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
    error_message = NULL
WHERE update_id = :update_id;
```

### 18）标记 Telegram update 处理失败
```sql
UPDATE telegram_updates
SET
    status = 'failed',
    processed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
    error_message = :error_message
WHERE update_id = :update_id;
```

### 19）OCR 结果查询
```sql
SELECT
    ocr.id,
    ocr.ocr_mode,
    ocr.raw_text,
    ocr.fields_json,
    ocr.boxes_json,
    ocr.language,
    ocr.confidence,
    ocr.created_at
FROM ocr_results ocr
WHERE ocr.source_media_id = :source_media_id
ORDER BY ocr.created_at DESC
LIMIT 1;
```

### 20）全文检索：按 OCR 文本搜 observation
```sql
SELECT
    o.id,
    o.object_name,
    o.camera_id,
    o.zone_id,
    o.observed_at,
    o.ocr_text
FROM observations_fts f
JOIN observations o
  ON o.rowid = f.rowid
WHERE observations_fts MATCH :query
ORDER BY o.observed_at DESC
LIMIT :limit;
```

### 21）全文检索：按事件摘要搜 recent events
```sql
SELECT
    e.id,
    e.event_type,
    e.summary,
    e.event_at
FROM events_fts f
JOIN events e
  ON e.rowid = f.rowid
WHERE events_fts MATCH :query
ORDER BY e.event_at DESC
LIMIT :limit;
```

### 22）查需要发送通知的规则（带冷却窗口）
```sql
SELECT
    nr.id,
    nr.user_id,
    nr.rule_name,
    nr.trigger_type,
    nr.target_scope,
    nr.condition_json,
    nr.cooldown_sec,
    nr.last_triggered_at
FROM notification_rules nr
WHERE nr.is_enabled = 1
  AND (
        nr.last_triggered_at IS NULL
        OR nr.last_triggered_at < :cooldown_before
      );
```

---

## 第二部分：迁移版本草案

### 1）纯 SQL 版本迁移文件

#### 001_init.sql
```sql
-- 001_init.sql
-- 创建基础表 users, devices, observations, events, object_states, zone_states, media_items, audit_logs, telegram_updates, notification_rules, facts, ocr_results
-- 完整建表语句见上一节“建表草案”
```

#### 002_fts.sql
```sql
-- 002_fts.sql
-- 创建 FTS5 虚拟表：observations_fts, events_fts, ocr_results_fts
-- 完整 FTS5 建表语句见上一节“FTS5 草案”
```

#### 003_views_triggers.sql
```sql
-- 003_views_triggers.sql
-- 创建视图和触发器

-- 视图
CREATE VIEW IF NOT EXISTS world_state_view AS ... ;
CREATE VIEW IF NOT EXISTS active_notification_rules_view AS ... ;
CREATE VIEW IF NOT EXISTS recent_device_health_view AS ... ;

-- FTS 同步触发器
CREATE TRIGGER IF NOT EXISTS observations_ai ... ;
CREATE TRIGGER IF NOT EXISTS observations_ad ... ;
CREATE TRIGGER IF NOT EXISTS observations_au ... ;

CREATE TRIGGER IF NOT EXISTS events_ai ... ;
CREATE TRIGGER IF NOT EXISTS events_ad ... ;
CREATE TRIGGER IF NOT EXISTS events_au ... ;

CREATE TRIGGER IF NOT EXISTS ocr_results_ai ... ;
CREATE TRIGGER IF NOT EXISTS ocr_results_ad ... ;
CREATE TRIGGER IF NOT EXISTS ocr_results_au ... ;

-- 更新时间触发器
CREATE TRIGGER IF NOT EXISTS users_set_updated_at ... ;
CREATE TRIGGER IF NOT EXISTS devices_set_updated_at ... ;
CREATE TRIGGER IF NOT EXISTS object_states_set_updated_at ... ;
CREATE TRIGGER IF NOT EXISTS zone_states_set_updated_at ... ;
CREATE TRIGGER IF NOT EXISTS notification_rules_set_updated_at ... ;
CREATE TRIGGER IF NOT EXISTS facts_set_updated_at ... ;
```

#### 004_indexes.sql
```sql
-- 004_indexes.sql
-- 创建所有索引（见上一节“推荐索引草案”）
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
...
```

#### 005_data_fts_rebuild.sql
```sql
-- 005_data_fts_rebuild.sql
-- 如果 FTS 表在创建前已有数据，回填一次
INSERT INTO observations_fts(rowid, object_name, object_class, ocr_text, raw_payload_json)
SELECT rowid, object_name, object_class, ocr_text, raw_payload_json FROM observations;

INSERT INTO events_fts(rowid, event_type, summary, payload_json)
SELECT rowid, event_type, summary, payload_json FROM events;

INSERT INTO ocr_results_fts(rowid, raw_text, fields_json)
SELECT rowid, raw_text, fields_json FROM ocr_results;
```

---

### 2）Alembic 版本骨架（可选）

Alembic 的典型结构是每个 revision 一个 Python 文件，包含 `upgrade()` 和 `downgrade()` 方法。以下是一个骨架示例，包含基础表和索引的迁移。

#### 初始 revision：`versions/xxxx_create_initial_tables.py`
```python
"""create initial tables

Revision ID: xxxx
Revises: 
Create Date: 2026-03-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'xxxx'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 创建 users 表
    op.create_table('users',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('telegram_user_id', sa.Text(), nullable=False),
        sa.Column('telegram_chat_id', sa.Text()),
        sa.Column('display_name', sa.Text()),
        sa.Column('username', sa.Text()),
        sa.Column('role', sa.Text(), server_default='viewer'),
        sa.Column('is_allowed', sa.Integer(), server_default='1'),
        sa.Column('media_scope', sa.Text(), server_default='all'),
        sa.Column('note', sa.Text()),
        sa.Column('created_at', sa.Text(), server_default=sa.text("(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))")),
        sa.Column('updated_at', sa.Text(), server_default=sa.text("(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))")),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_user_id')
    )
    # 其他表类似 ...

def downgrade():
    op.drop_table('ocr_results')
    op.drop_table('facts')
    op.drop_table('notification_rules')
    op.drop_table('telegram_updates')
    op.drop_table('audit_logs')
    op.drop_table('media_items')
    op.drop_table('zone_states')
    op.drop_table('object_states')
    op.drop_table('events')
    op.drop_table('observations')
    op.drop_table('devices')
    op.drop_table('users')
```

#### 第二个 revision：`versions/yyyy_create_fts_tables.py`
```python
"""create fts tables

Revision ID: yyyy
Revises: xxxx
Create Date: 2026-03-13 12:10:00.000000

"""
from alembic import op

def upgrade():
    # SQLite 的虚拟表创建无法用普通 SQLAlchemy 表示，使用 execute 执行原生 SQL
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts
        USING fts5(
            object_name,
            object_class,
            ocr_text,
            raw_payload_json,
            content='observations',
            content_rowid='rowid'
        )
    """)
    # 同样创建 events_fts, ocr_results_fts

def downgrade():
    op.execute("DROP TABLE IF EXISTS observations_fts")
    op.execute("DROP TABLE IF EXISTS events_fts")
    op.execute("DROP TABLE IF EXISTS ocr_results_fts")
```

#### 第三个 revision：`versions/zzzz_create_views_triggers.py`
```python
"""create views and triggers

Revision ID: zzzz
Revises: yyyy
Create Date: 2026-03-13 12:20:00.000000

"""
from alembic import op

def upgrade():
    # 视图
    op.execute("""
        CREATE VIEW IF NOT EXISTS world_state_view AS
        SELECT ... ;
    """)
    # 触发器
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS observations_ai ...
    """)
    # ...

def downgrade():
    op.execute("DROP VIEW IF EXISTS world_state_view")
    op.execute("DROP VIEW IF EXISTS active_notification_rules_view")
    op.execute("DROP VIEW IF EXISTS recent_device_health_view")
    op.execute("DROP TRIGGER IF EXISTS observations_ai")
    op.execute("DROP TRIGGER IF EXISTS observations_ad")
    op.execute("DROP TRIGGER IF EXISTS observations_au")
    # ... 其他触发器
```

#### 第四个 revision：`versions/aaaa_create_indexes.py`
```python
"""create indexes

Revision ID: aaaa
Revises: zzzz
Create Date: 2026-03-13 12:30:00.000000

"""
from alembic import op

def upgrade():
    op.create_index('idx_users_role', 'users', ['role'])
    op.create_index('idx_devices_status', 'devices', ['status'])
    # ... 所有索引

def downgrade():
    op.drop_index('idx_users_role')
    op.drop_index('idx_devices_status')
    # ...
```

#### 第五个 revision：`projects/bbbb_fts_rebuild.py`
```python
"""rebuild fts data after creation

Revision ID: bbbb
Revises: aaaa
Create Date: 2026-03-13 12:40:00.000000

"""
from alembic import op

def upgrade():
    op.execute("""
        INSERT INTO observations_fts(rowid, object_name, object_class, ocr_text, raw_payload_json)
        SELECT rowid, object_name, object_class, ocr_text, raw_payload_json FROM observations;
    """)
    op.execute("""
        INSERT INTO events_fts(rowid, event_type, summary, payload_json)
        SELECT rowid, event_type, summary, payload_json FROM events;
    """)
    op.execute("""
        INSERT INTO ocr_results_fts(rowid, raw_text, fields_json)
        SELECT rowid, raw_text, fields_json FROM ocr_results;
    """)

def downgrade():
    op.execute("DELETE FROM observations_fts")
    op.execute("DELETE FROM events_fts")
    op.execute("DELETE FROM ocr_results_fts")
```

> **注意**：在 SQLite 中，使用 Alembic 进行复杂迁移时，建议开启 `render_as_batch` 模式（设置 `context.configure(render_as_batch=True)`）以自动处理 SQLite 的 ALTER TABLE 限制。([alembic.sqlalchemy.org](https://alembic.sqlalchemy.org/en/latest/batch.html?utm_source=chatgpt.com))

---

以上即为你提供的高频查询 SQL 和迁移草案的整理版本，未改动任何内容。如需进一步整合到完整产品计划书中，或补充其他部分，请告知。