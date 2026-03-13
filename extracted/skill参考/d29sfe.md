<!-- source: skill参考.md | id: d29sfe -->
# DEPLOYMENT.md

## 1. 文档目的

本文档用于说明 Vision Butler v5 的正式部署方式。

本项目的正式部署组成如下：
- Telegram Bot：唯一用户入口
- nanobot：唯一主控宿主
- Qwen3.5 多模态模型：理解、工具决策、简单 OCR
- Backend Sidecar Services：memory / state / policy / security / device / OCR
- MCP Servers：把正式能力暴露给 nanobot
- SQLite + FTS5：正式单机数据层
- RK3566 Edge Device：边缘采集、轻量检测、事件压缩、心跳与媒体回传

---

## 2. 正式部署原则

1. Telegram 是正式入口，不是测试入口。
2. nanobot 是正式宿主，但不是业务真相层。
3. 所有正式业务能力优先通过 MCP 暴露给 nanobot。
4. 后端服务是状态、记忆、OCR、设备与权限的事实层。
5. RK3566 前端只负责事件感知与媒体回传。
6. 当前阶段正式数据库采用 SQLite + FTS5。
7. 正式与开发环境必须隔离。

---

## 3. 推荐部署拓扑

### 3.1 x86 主机运行内容
- nanobot
- backend API
- MCP servers
- SQLite 数据库
- media storage
- logs / audit logs

### 3.2 RK3566 前端运行内容
- camera capture
- detector / tracker
- event compressor
- ring buffer cache
- device API
- heartbeat sender

### 3.3 Telegram 入口
- Telegram Bot API
- nanobot Telegram channel
- allowFrom 只允许正式用户

---

## 4. 目录约定

推荐目录：

- config/
- docs/
- gateway/
- edge_device/
- src/
- skills/
- scripts/
- tests/

关键路径：
- config/nanobot.config.json
- gateway/nanobot_workspace/
- schema.sql
- migrations/
- media/
- logs/

---

## 5. 环境变量建议

建议使用环境变量提供敏感配置，不要把真实密钥写死在仓库。

### 主机侧建议环境变量
- TELEGRAM_BOT_TOKEN
- TELEGRAM_ALLOWED_USER_ID
- QWEN_PROVIDER_NAME
- QWEN_MODEL_NAME
- QWEN_API_BASE
- QWEN_API_KEY
- SQLITE_DB_PATH
- MEDIA_ROOT
- MCP_VISION_URL
- MCP_MEMORY_URL
- MCP_STATE_POLICY_URL
- MCP_OCR_DEVICE_URL
- BACKEND_HOST
- BACKEND_PORT

### 前端侧建议环境变量
- EDGE_DEVICE_ID
- EDGE_CAMERA_ID
- EDGE_API_KEY
- EDGE_BACKEND_BASE
- EDGE_SNAPSHOT_DIR
- EDGE_CLIP_DIR
- EDGE_MODEL_NAME

---

## 6. 正式部署顺序

建议按以下顺序启动：

1. 初始化数据库
2. 启动 backend API
3. 启动 MCP servers
4. 启动 nanobot gateway
5. 启动 RK3566 edge service
6. 执行 smoke test
7. 用 Telegram 做首次验证

---

## 7. 数据库初始化

第一次部署前执行：

- 初始化 SQLite 数据库
- 执行 schema.sql 或依次执行 migrations/sql/*
- 检查主表、索引、FTS、视图是否存在

建议最少检查：
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
- ocr_results
- observations_fts
- events_fts
- ocr_results_fts

---

## 8. backend API 启动要求

backend API 负责：
- /healthz
- /memory/*
- /policy/*
- /device/*
- /ocr/*
- /device/heartbeat
- /device/ingest/event

启动前确认：
- 数据库路径有效
- 配置文件完整
- media 根目录存在
- audit / log 目录可写

---

## 9. MCP servers 启动要求

正式 MCP 能力至少包括：

### vision-mcp
- take_snapshot
- get_recent_clip
- describe_scene

### memory-mcp
- query_recent_events
- last_seen_object

### state-policy-mcp
- get_object_state
- get_zone_state
- get_world_state
- evaluate_staleness

### ocr-device-mcp
- ocr_quick_read
- ocr_extract_fields
- device_status
- refresh_object_state
- refresh_zone_state

部署时要确认：
- 每个 MCP server 都有独立端口或独立进程
- nanobot.config.json 中的 mcpServers URL 正确
- health endpoint（如果有）可访问
- tool timeout 合理

---

## 10. nanobot 启动要求

正式 nanobot 应满足：
- 使用单独 config 文件启动
- 使用独立 workspace
- Telegram channel enabled
- allowFrom 生效
- 正确挂载 MCP servers
- 使用正式 Qwen3.5 模型配置

正式环境应至少准备两个实例：
- prod：正式 bot
- dev：测试 bot

正式与测试实例必须隔离：
- 独立 Telegram token
- 独立 workspace
- 独立数据库或独立 DB 文件
- 独立 media 目录
- 独立 logs

---

## 11. RK3566 前端启动要求

前端启动前确认：
- 摄像头可用
- 本地缓存目录存在
- device_id / camera_id / api_key 已配置
- 能访问 backend API
- heartbeat 间隔合理

前端必须支持：
- 定时 heartbeat
- 接收 snapshot / clip 命令
- 输出统一 event envelope
- 保存最近 snapshot / clip
- 失败时给出明确错误日志

---

## 12. Telegram 正式上线前检查

上线前必须检查：

1. Bot token 是否正确
2. allowFrom 是否只包含允许用户
3. nanobot 实例是否连到正式 workspace
4. telegram_updates 去重逻辑是否可用
5. 长消息分片是否可用
6. sendChatAction 是否可用
7. 图片消息是否能进入 OCR / scene query 流程
8. 命令入口是否可用：
   - /snapshot
   - /clip
   - /lastseen
   - /state
   - /ocr
   - /device
   - /help

---

## 13. 正式 smoke test

正式 smoke test 至少应验证：

1. backend /healthz 正常
2. 数据库主表存在
3. 至少一个 MCP tool 可调用
4. nanobot 能启动
5. Telegram 文本消息可收到并处理
6. 设备状态查询可用
7. snapshot 命令可用
8. OCR quick read 可用

---

## 14. 日志与审计

正式部署必须保留以下日志：
- backend service logs
- nanobot logs
- edge device logs
- audit_logs 数据表
- telegram_updates 状态表

所有敏感行为必须进入审计：
- 用户访问
- 工具调用
- 权限拒绝
- 设备命令
- 媒体读取
- OCR 结构化提取

---

## 15. 当前可运行范围与 stub 说明

当前版本允许以下部分以 adapter / stub 方式先运行：
- 真实 RKNN 检测器
- 真实 OCR provider
- 真实 MCP server 框架适配
- 真实 edge 设备命令执行

但以下部分应当是真正存在的：
- 仓库结构
- 数据库 schema
- 路由与服务骨架
- nanobot 配置
- Skills
- 基础测试
- 启动脚本
- smoke test

---

## 16. 首次启动建议顺序

1. 配置环境变量
2. 运行 scripts/init_db.sh
3. 运行 scripts/start_backend.sh
4. 运行 scripts/start_gateway.sh
5. 运行 scripts/start_edge.sh
6. 运行 scripts/smoke_test.sh
7. 用 Telegram 发送 /help
8. 再测试 /device、/snapshot、/ocr

---

## 17. 故障排查建议

### backend 无法启动
检查：
- SQLite 路径
- 配置文件
- 端口占用
- schema 是否已初始化

### nanobot 无法调用工具
检查：
- mcpServers URL
- tool timeout
- MCP 服务是否已启动
- workspace 是否正确

### Telegram 无响应
检查：
- Bot token
- allowFrom
- update 去重逻辑
- polling / webhook 是否冲突

### edge 无法回传事件
检查：
- device_id / api_key
- backend 地址
- 本地缓存目录
- heartbeat 是否成功

---

## 18. 正式部署完成定义

只有同时满足以下条件，才算部署完成：
- 数据库初始化成功
- backend 服务可用
- MCP tools 可调用
- nanobot 正常启动
- Telegram 问答可用
- 设备状态查询可用
- snapshot 可用
- OCR 可用
- 审计可记录
- smoke test 通过
