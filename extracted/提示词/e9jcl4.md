<!-- source: 提示词.md | id: e9jcl4 -->
# AGENTS.md

## 项目名称
Vision Butler v5

## 项目定位
本项目是一个通过 Telegram 交互的视觉管家系统。

系统正式组成：
- Telegram Bot：正式唯一用户入口
- nanobot：唯一主控入口与 Agent 宿主
- Qwen3.5 多模态模型：理解用户问题、理解图片与短视频、执行简单 OCR、决定是否调用工具、整合工具结果
- MCP Server：把视觉、记忆、状态、OCR、设备能力暴露给模型
- Skills：定义标准执行模板、工具使用顺序、freshness 策略和 fallback 规则
- RK3566 单目前端：采集、轻量检测、轻量跟踪、事件压缩、短时媒体缓存、设备心跳
- Backend Sidecar Services：事实层，负责 observation / event / state / policy / security / device / OCR

## 项目目标
实现一个完整可运行的视觉管家系统，至少支持以下正式能力：
1. 当前观察
2. 最近事件
3. last_seen
4. object_state
5. zone_state
6. world_state 摘要
7. take_snapshot
8. get_recent_clip
9. 简单 OCR
10. 结构化 OCR
11. 设备状态查询
12. 主动通知
13. 权限控制与审计

## 明确非目标
以下内容不在当前项目范围内：
- 运动控制
- ROS / ROS2 集成
- 3D 建图
- 多机器人协同
- 云端多租户 SaaS
- 多摄像头空间拓扑重建
- 单目前端精确三维定位
- 完整 Web 后台
- 高并发分布式部署

## 一条总原则
模型负责理解与决策，工具负责事实与动作，前端负责事件感知，后端负责状态真相，Telegram 负责用户入口，nanobot 负责统一宿主。

## 核心架构边界
1. Telegram 是正式入口，不是后续增强项。
2. nanobot 是唯一主控入口，但不是业务真相层。
3. MCP / Skill 是正式能力层，不是临时扩展。
4. RK3566 前端只负责边缘感知，不负责长期记忆、状态聚合、权限控制、Telegram 交互。
5. object_state / zone_state / freshness / stale / fallback 必须落到后端服务与数据库中，不能只靠模型临时回答。

## 仓库级硬约束
以下目录与职责边界必须保持：
- docs/：设计与项目文档
- config/：配置
- edge_device/：RK3566 前端代码
- src/services/：后端服务
- src/security/：权限与访问控制
- src/schemas/：数据模型
- src/db/：数据库与 repository
- src/mcp_server/：MCP tools/resources/prompts
- skills/：Skill 定义
- tests/：测试
- scripts/：运行与辅助脚本

## 不允许做的事情
1. 不要深改 nanobot 核心代码来实现业务功能。
2. 不要把状态逻辑硬编码进 Telegram 处理层。
3. 不要把数据库访问散落到无约束脚本中。
4. 不要把 OCR、state、policy 直接写成模型提示词逻辑，必须有服务层或工具层。
5. 不要让前端 RK3566 承担长期记忆、世界状态推理或复杂工具编排。
6. 不要跳过测试直接交付。
7. 不要在没有明确验收条件时大范围重构目录结构。

## 开发约束
1. 先补齐最小可运行骨架，再逐步填能力。
2. 每个任务必须有清晰输出文件。
3. 每个任务必须有可执行验收方式。
4. 优先写可测试、可回滚、可维护代码。
5. 任何跨模块逻辑都必须经过 service 层或 repository 层。
6. 对 SQLite 的复杂 schema 变更，优先采用“新表迁移 + 重建索引/触发器”的方式。
7. Telegram update 必须去重。
8. 所有敏感动作必须进入 audit_logs。

## 正式能力层约束
### MCP Tools
正式工具至少包括：
- take_snapshot
- get_recent_clip
- describe_scene
- last_seen_object
- get_object_state
- get_zone_state
- get_world_state
- query_recent_events
- evaluate_staleness
- ocr_quick_read
- ocr_extract_fields
- device_status
- refresh_object_state
- refresh_zone_state

### Skills
正式 Skill 至少包括：
- scene_query
- history_query
- last_seen
- object_state
- zone_state
- ocr_query
- device_status

每个 Skill 必须明确：
- trigger_patterns
- allowed_tools
- allowed_resources
- freshness_policy
- fallback_rules
- steps
- output_schema

## 数据层约束
必须保留以下核心表：
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

必须保留以下 FTS：
- observations_fts
- events_fts
- ocr_results_fts

## 关键运行命令（目标状态）
以下命令是仓库完成后应能工作的目标命令：
- ./scripts/init_db.sh
- ./scripts/start_backend.sh
- ./scripts/start_edge.sh
- ./scripts/start_gateway.sh
- ./scripts/smoke_test.sh
- pytest -q

## 必须具备的测试
- unit: state / policy / security / memory / OCR
- integration: device_event_flow / state_flow / stale_fallback / access_control / telegram_flow
- e2e: current scene / last_seen / object_state / OCR / take_snapshot / device offline alert

## 完成定义
一个任务只有同时满足下面条件才算完成：
1. 目标文件已创建或正确修改
2. 代码可以运行
3. 对应测试通过
4. 不破坏现有目录职责边界
5. 结果与项目书一致
6. 重要行为可通过日志或审计追踪

## 交付风格
所有提交应遵循：
- 小步提交
- 目录职责清晰
- 配置与代码分离
- 明确错误处理
- 明确注释关键边界
- 不引入无必要的复杂框架

## 给 Codex 的工作方式
1. 一次只解决一个明确任务。
2. 先读相关文件，再修改最少文件集合。
3. 完成后优先跑该任务对应测试。
4. 如果发现需求冲突，优先遵守 AGENTS.md、PRODUCT_PLAN.md、ARCHITECTURE.md。
5. 任何超出边界的优化都不要顺手做。
