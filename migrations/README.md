# Vision Butler v5 数据库迁移说明

本目录用于维护 Vision Butler v5 的 SQLite 迁移版本。

## 迁移策略
- 正式数据库：SQLite
- 文本检索：FTS5（`observations_fts` / `events_fts` / `ocr_results_fts`）
- 迁移按顺序执行：`001` 到 `007`
- 复杂 schema 变更采用“新表迁移 + 重建索引/触发器/视图”

## 目录结构
- `migrations/sql/001_init_core.sql`
- `migrations/sql/002_aux_tables.sql`
- `migrations/sql/003_indexes.sql`
- `migrations/sql/004_fts.sql`
- `migrations/sql/005_fts_triggers.sql`
- `migrations/sql/006_views.sql`
- `migrations/sql/007_backfill_fts.sql`

## 初始化方式
方式 A：一键执行 `schema.sql`
```bash
sqlite3 vision_butler.db < schema.sql
```

方式 B：按迁移顺序执行
```bash
sqlite3 vision_butler.db < migrations/sql/001_init_core.sql
sqlite3 vision_butler.db < migrations/sql/002_aux_tables.sql
sqlite3 vision_butler.db < migrations/sql/003_indexes.sql
sqlite3 vision_butler.db < migrations/sql/004_fts.sql
sqlite3 vision_butler.db < migrations/sql/005_fts_triggers.sql
sqlite3 vision_butler.db < migrations/sql/006_views.sql
sqlite3 vision_butler.db < migrations/sql/007_backfill_fts.sql
```

## 迁移原则（强制）
- 不引入 PostgreSQL 特有语法
- 不在 migration 文件中写业务逻辑
- 保持 Telegram update 去重能力（`telegram_updates.update_id` 唯一约束）
- 每次结构性变更同步维护索引、FTS、触发器、视图

## 推荐 smoke queries
```sql
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;
SELECT name FROM sqlite_master WHERE type='index' ORDER BY name;
SELECT name FROM sqlite_master WHERE type='view' ORDER BY name;
SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_fts';
SELECT COUNT(*) FROM devices;
SELECT COUNT(*) FROM observations;
SELECT COUNT(*) FROM object_states;
```
