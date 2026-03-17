# Nano Vision Butler v5

基于 Telegram 的视觉管家系统正式仓库（与 `AGENTS.md` 和 `计划书.md` 对齐版）。

## 项目定位
- 正式唯一用户入口：Telegram
- 唯一主控宿主：nanobot（会话、模型与工具编排）
- 正式能力层：MCP / Skills
- RK3566 前端只负责边缘感知，不承载长期记忆、权限治理和状态真相层

## 当前实现状态（截至 2026-03-17）
- `TASKS.md` 中 T0~T17（含 Hotfix）均为 `DONE`
- 后端 sidecar、MCP server、edge runtime、Telegram update 处理链路均可本地运行
- 测试矩阵现状：`unit=13`、`integration=14`、`e2e=7`

## 目录职责
- `gateway/`：nanobot 接入配置与运行栈
- `src/`：后端 sidecar（memory / perception / state / policy / security / device）
- `src/mcp_server/`：MCP tools/resources/prompts 暴露层
- `skills/`：正式 Skill 定义
- `edge_device/`：RK3566 边缘采集、检测、跟踪、压缩、缓存、设备 API
- `config/`：settings/policies/access/devices/cameras/aliases
- `tests/`：unit/integration/e2e
- `docs/`：产品、架构、部署、测试、边缘专项文档

## 当前已落地能力

### 1. 后端与数据层
- FastAPI 路由：
  - `/memory/recent-events`
  - `/memory/last-seen`
  - `/memory/object-state`
  - `/memory/zone-state`
  - `/memory/world-state`
  - `/policy/evaluate-staleness`
  - `/device/status`
  - `/device/command/take-snapshot`
  - `/device/command/get-recent-clip`
  - `/device/ingest/event`
  - `/device/heartbeat`
  - `/ocr/quick-read`
  - `/ocr/extract-fields`
  - `/telegram/update`
- SQLite + FTS5 已落地，核心表包含：`observations/events/object_states/zone_states/media_items/audit_logs/telegram_updates/ocr_results` 等
- Telegram update 去重已落库（`telegram_updates`）

### 2. MCP 能力层
- Tools（当前实现 12 个）：
  - `take_snapshot`
  - `get_recent_clip`
  - `describe_scene`
  - `last_seen_object`
  - `get_object_state`
  - `get_zone_state`
  - `get_world_state`
  - `query_recent_events`
  - `evaluate_staleness`
  - `ocr_quick_read`
  - `ocr_extract_fields`
  - `device_status`
- Resources（当前实现 6 个）：
  - `resource://memory/observations`
  - `resource://memory/events`
  - `resource://memory/object_states`
  - `resource://memory/zone_states`
  - `resource://policy/freshness`
  - `resource://devices/status`
- Prompts（当前实现 7 个）：
  - `scene_query`
  - `history_query`
  - `last_seen_query`
  - `object_state_query`
  - `zone_state_query`
  - `ocr_query`
  - `device_status_query`

### 3. Skill 层
- 当前注册并可调用：
  - `scene_query`
  - `history_query`
  - `last_seen`
  - `object_state`
  - `zone_state`
  - `ocr_query`
  - `device_status`

### 4. Telegram 交互链路
- 支持命令：`/snapshot /clip /lastseen /state /ocr /device /help`
- 支持文本、图片、视频三类消息分支
- 长回复自动分片（当前默认每段最多 3500 字符）
- 返回 `sendChatAction` 动作建议（`typing/upload_photo/upload_video/record_video`）
- 用户访问控制走 `security_guard`，拒绝与允许动作都进入审计

### 5. RK3566 边缘链路
- `edge_device` 支持：采集（V4L2/GStreamer/FFmpeg）、检测（含 RKNN）、轻量跟踪、事件压缩、快照与 clip ring buffer、heartbeat
- `scripts/start_edge.sh` 支持 `run-once/heartbeat/take-snapshot/get-recent-clip`
- 默认模型路径已切换为 Rockchip 优化版 YOLOv8n INT8（可通过环境变量覆盖）

## 本地最小启动
1. 初始化数据库：`./scripts/init_db.sh`
2. 启动后端：`./scripts/start_backend.sh`
3. 启动 MCP：`./scripts/start_mcp.sh`
4. 预检查 gateway：`NANOBOT_DRY_RUN=1 NANOBOT_INSTANCE=dev ./scripts/start_gateway.sh`
5. 边缘 run-once：`EDGE_ACTION=run-once ./scripts/start_edge.sh`
6. 冒烟测试：`./scripts/smoke_test.sh`

## 后台常驻启动
- 启动：`NANOBOT_INSTANCE=prod NANOBOT_AUTO_DISABLE_MCP=0 ./scripts/stack_ctl.sh start`
- 状态：`./scripts/stack_ctl.sh status`
- 日志：`./scripts/stack_ctl.sh logs gateway`
- 停止：`./scripts/stack_ctl.sh stop`

## Telegram 重复回复排查
- 同一个 token 只能由一个 gateway 实例消费
- 建议 `TELEGRAM_BOT_TOKEN_DEV` 与 `TELEGRAM_BOT_TOKEN` 分离
- 出现重复消费可执行：`./scripts/stack_ctl.sh stop && pkill -f "nanobot.*gateway" || true`

## 模型与密钥切换（nanobot）
- 生效配置：
  - `config/runtime/nanobot.config.json`
  - `config/runtime/nanobot.dev.config.json`
- 关键字段：
  - `agents.defaults.model`
  - `agents.defaults.provider`
  - `providers.openai.apiBase`
  - `providers.openai.apiKey`
- 修改后重启：`./scripts/stack_ctl.sh restart`

## 计划书与当前项目差异（截至 2026-03-17）
1. 计划书给出的 MCP Tools 中 `refresh_object_state`、`refresh_zone_state`、`audit_recent_access` 尚未在 MCP tool registry 暴露。
2. 计划书给出的 `resource://security/access_scope` 尚未在 MCP resources 中实现。
3. 计划书建议多 MCP server 分拆（vision/memory/state-policy/ocr-device）；当前仓库为单一 `vision-butler-mcp` 进程统一暴露。
4. Telegram 正式入口在产品上定义为 polling/webhook；本仓库侧实现的是 `/telegram/update` 处理链路，真实 Telegram 通道接入依赖 nanobot 运行环境配置。
5. 计划书包含“规则触发主动通知”；当前 `notification_rules` 表已存在，但完整主动通知调度闭环尚未在仓库内形成独立服务模块。
6. OCR 双通道已具备接口与工具能力（`ocr_quick_read`/`ocr_extract_fields`），但独立外部 OCR 服务（如专门 OCR 微服务）仍属于可选部署项。

## 参考文档
- `docs/ARCHITECTURE.md`
- `docs/DEPLOYMENT.md`
- `docs/DELIVERY_CHECKLIST.md`
- `docs/TEST_PLAN.md`
- `docs/EDGE_DEVICE.md`
