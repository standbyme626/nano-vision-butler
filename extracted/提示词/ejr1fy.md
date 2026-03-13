<!-- source: 提示词.md | id: ejr1fy -->
你正在为 Vision Butler v5 实现正式数据层。

任务目标：
建立 SQLite + FTS5 数据库初始化与迁移系统。

必须创建：
- schema.sql
- migrations/README.md
- migrations/sql/001_init_core.sql
- migrations/sql/002_aux_tables.sql
- migrations/sql/003_indexes.sql
- migrations/sql/004_fts.sql
- migrations/sql/005_fts_triggers.sql
- migrations/sql/006_views.sql
- migrations/sql/007_backfill_fts.sql
- scripts/init_db.sh

必须包含的主表：
- users
- devices
- observations
- events
- object_states
- zone_states
- media_items
- audit_logs
- telegram_updates
- notification_rules
- facts
- ocr_results

必须包含：
- FTS5：observations_fts / events_fts / ocr_results_fts
- views：world_state_view / active_notification_rules_view / recent_device_health_view
- 必要索引
- FTS 同步触发器

必须遵守：
1. 以 SQLite 为正式数据库。
2. 复杂表变更在 README 中说明采用“新表迁移”策略。
3. Telegram update 去重必须落表。
4. schema.sql 必须可直接执行。
5. init_db.sh 必须能初始化空数据库。

不要做的事情：
- 不要引入 PostgreSQL 特有语法
- 不要把业务逻辑写进 migration
- 不要省略 FTS 和视图

完成后请：
1. 列出创建的表、索引、视图、FTS 表
2. 给出 `sqlite3 <db> < schema.sql` 可执行说明
3. 说明 smoke query 如何验证建库成功
