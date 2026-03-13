可以，下面我直接把三份一次性给你，都是**可直接复制进仓库**的版本。
之所以这样组织，是因为 Codex 官方就强调它最适合处理**目标清晰、约束明确、可运行命令和测试验收**的工程任务；而 nanobot 当前公开能力也已经覆盖了 Telegram 接入、多实例 workspace、以及通过配置挂载 MCP servers 的方式，所以你的仓库级约束和任务板应该围绕这些边界来写。([developers.openai.com](https://developers.openai.com/codex/cli?utm_source=chatgpt.com)) ([developers.openai.com](https://developers.openai.com/codex/cli/features?utm_source=chatgpt.com)) ([github.com](https://github.com/HKUDS/nanobot/blob/main/README.md?utm_source=chatgpt.com))

---

## 1）`AGENTS.md`

```text id="e9jcl4"
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
```

---

## 2）`TASKS.md`

```text id="w9nfxh"
# TASKS.md

本文件用于驱动 Codex 按阶段完成 Vision Butler v5。

规则：
- 按顺序执行，除非明确标注可并行
- 每个任务完成后必须更新状态
- 每个任务必须通过本任务的验收标准
- 不允许跳过“数据库 / 配置 / 测试”直接堆业务代码

任务状态：
- TODO
- DOING
- DONE
- BLOCKED

---

## T0 仓库初始化与约束固化
状态：TODO
优先级：P0
依赖：无

### 目标
建立正式仓库骨架，并把项目约束固化到仓库。

### 输出
- AGENTS.md
- README.md
- docs/PRODUCT_PLAN.md
- docs/ARCHITECTURE.md
- docs/TEST_PLAN.md
- docs/DEPLOYMENT.md
- config/ 空模板
- scripts/ 空模板
- 顶层目录结构

### 验收
- 仓库目录存在
- 文档可读
- AGENTS.md 已写明硬边界
- README 能说明项目定位与启动方式

---

## T1 数据库与迁移系统
状态：TODO
优先级：P0
依赖：T0

### 目标
建立 SQLite + FTS5 的正式数据层和迁移目录。

### 输出
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

### 验收
- 能初始化空库
- 表、索引、FTS、视图存在
- smoke queries 可执行
- telegram_updates 去重表存在
- world_state_view 存在

---

## T2 配置系统
状态：TODO
优先级：P0
依赖：T0

### 目标
建立统一配置加载机制，管理 settings / policies / access / devices / cameras。

### 输出
- config/settings.yaml
- config/policies.yaml
- config/access.yaml
- config/devices.yaml
- config/cameras.yaml
- config/aliases.yaml
- src/settings.py 或等价模块

### 验收
- 程序可加载所有配置文件
- 缺失关键配置时报清晰错误
- 配置对象可被 services 和 app 注入

---

## T3 Schema 与 Repository
状态：TODO
优先级：P0
依赖：T1, T2

### 目标
完成数据模型与 repository 查询封装。

### 输出
- src/schemas/memory.py
- src/schemas/state.py
- src/schemas/policy.py
- src/schemas/security.py
- src/schemas/device.py
- src/schemas/telegram.py
- src/db/session.py
- src/db/repositories/*.py

### 验收
- 支持 observation/event/state/device/audit 的基本读写
- 至少实现：
  - last_seen
  - get_object_state
  - get_zone_state
  - query_recent_events
  - device_status
  - save_telegram_update
- 单元测试可运行

---

## T4 FastAPI 后端骨架
状态：TODO
优先级：P0
依赖：T2, T3

### 目标
建立可运行的后端服务入口、路由注册和依赖注入。

### 输出
- src/app.py
- src/dependencies.py
- src/routes_memory.py
- src/routes_state.py
- src/routes_policy.py
- src/routes_device.py
- src/routes_ocr.py

### 验收
- 应用可启动
- /healthz 可访问
- 路由与 service 分层清晰
- 统一异常处理存在

---

## T5 memory_service 与 perception_service
状态：TODO
优先级：P1
依赖：T3, T4

### 目标
打通 observation / event / heartbeat 写入链路。

### 输出
- src/services/memory_service.py
- src/services/perception_service.py
- /device/ingest/event
- /device/heartbeat

### 验收
- 前端事件可写 observations
- 可根据规则升级为 events
- heartbeat 可刷新 devices.last_seen 和 status
- 关键动作写 audit_logs

---

## T6 state_service 与 policy_service
状态：TODO
优先级：P1
依赖：T5

### 目标
实现 object_state / zone_state / world_state / stale / fallback。

### 输出
- src/services/state_service.py
- src/services/policy_service.py
- /memory/object-state
- /memory/zone-state
- /memory/world-state
- /policy/evaluate-staleness

### 验收
- object_state 可查询
- zone_state 可查询
- stale 正常计算
- fallback_required 正常输出
- reason_code 有值

---

## T7 device_service 与媒体链路
状态：TODO
优先级：P1
依赖：T5

### 目标
打通拍照、视频片段、设备状态查询。

### 输出
- src/services/device_service.py
- /device/status
- /device/command/take-snapshot
- /device/command/get-recent-clip

### 验收
- snapshot 返回 media URI
- clip 返回 media URI
- 设备离线时有明确错误
- media_items 正常入库

---

## T8 OCR 双通道
状态：TODO
优先级：P1
依赖：T4, T5

### 目标
实现模型 OCR + 工具 OCR 双通道。

### 输出
- src/services/ocr_service.py
- /ocr/quick-read
- /ocr/extract-fields
- ocr_results 写入逻辑

### 验收
- 简单 OCR 可返回文本
- 结构化 OCR 可返回 fields_json
- OCR 结果可与 observation/event 关联

---

## T9 MCP Server 层
状态：TODO
优先级：P1
依赖：T6, T7, T8

### 目标
把正式能力暴露成标准 MCP tools/resources/prompts。

### 输出
- src/mcp_server/tools/*.py
- src/mcp_server/resources/*.py
- src/mcp_server/prompts/*.py
- MCP 启动入口

### 验收
- tools 可列出
- tools 可调用
- resources 可读取
- prompts 可读取
- 至少实现核心工具清单

---

## T10 Skill 层
状态：TODO
优先级：P1
依赖：T9

### 目标
建立正式 Skills，并与 MCP 工具对齐。

### 输出
- skills/scene_query/SKILL.md
- skills/history_query/SKILL.md
- skills/last_seen/SKILL.md
- skills/object_state/SKILL.md
- skills/zone_state/SKILL.md
- skills/ocr_query/SKILL.md
- skills/device_status/SKILL.md
- 可选 skill_registry.py

### 验收
- 每个 Skill 都有明确字段
- 与工具清单一致
- freshness / fallback 有定义

---

## T11 nanobot 集成
状态：TODO
优先级：P1
依赖：T9, T10

### 目标
将 nanobot 作为正式宿主接入 Telegram、Qwen3.5、MCP 和 Skills。

### 输出
- config/nanobot.config.json
- gateway/nanobot_workspace/
- scripts/start_gateway.sh

### 验收
- nanobot 能启动
- Telegram channel 可用
- MCP servers 可被发现
- workspace 可创建
- allowFrom 生效

---

## T12 Telegram 正式交互链路
状态：TODO
优先级：P1
依赖：T11

### 目标
把 Telegram 当正式入口完整打通。

### 输出
- reply_service / reply_builder
- update 去重处理
- 长消息分片
- sendChatAction
- 基础命令入口

### 验收
- 文本问答可用
- 图片问答可用
- 拍照命令可用
- 长消息自动分片
- 长任务有 processing 提示

---

## T13 RK3566 前端最小正式实现
状态：TODO
优先级：P2
依赖：T5, T7

### 目标
实现可接入的边缘设备最小正式版本。

### 输出
- edge_device/capture/
- edge_device/inference/
- edge_device/tracking/
- edge_device/compression/
- edge_device/cache/
- edge_device/health/
- edge_device/api/

### 验收
- 能采图
- 能检测
- 能上报 heartbeat
- 能响应 snapshot / clip 请求

---

## T14 测试矩阵落地
状态：TODO
优先级：P1
依赖：T6, T7, T8, T9, T11, T12

### 目标
把项目书中的测试矩阵变成真实测试。

### 输出
- tests/unit/*.py
- tests/integration/*.py
- tests/e2e/*.py
- scripts/smoke_test.sh

### 验收
- unit / integration / e2e 三层测试存在
- 核心路径有覆盖
- pytest -q 可执行

---

## 推荐并行方式

### A 线：数据与事实层
- T1
- T3
- T5
- T6

### B 线：接口与能力层
- T4
- T7
- T8
- T9

### C 线：宿主与入口层
- T10
- T11
- T12

### D 线：边缘层
- T13

### 收尾线：测试与验收
- T14
```

---

## 3）前 5 个 Codex 专用提示词

下面这 5 个提示词，我按“**可以直接发给 Codex 执行**”的标准写。
Codex 官方最佳实践本质上就是：给清晰目标、限制修改范围、给验收条件、让它跑命令和测试。([developers.openai.com](https://developers.openai.com/codex/cli?utm_source=chatgpt.com)) ([developers.openai.com](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide?utm_source=chatgpt.com))

---

### Prompt 1：初始化仓库与文档骨架

```text id="wc8q37"
你正在为一个新仓库实现 Vision Butler v5 的正式代码骨架。

任务目标：
建立正式仓库目录结构，并创建以下基础文件：
- AGENTS.md
- README.md
- docs/PRODUCT_PLAN.md
- docs/ARCHITECTURE.md
- docs/TEST_PLAN.md
- docs/DEPLOYMENT.md
- config/ 空模板文件
- scripts/ 空模板文件

必须遵守：
1. Telegram 是正式唯一用户入口。
2. nanobot 是唯一主控宿主，但不是业务真相层。
3. MCP / Skill 是正式能力层。
4. RK3566 单目前端只负责边缘感知，不负责长期记忆、状态聚合和 Telegram 交互。
5. 不要写业务实现代码，只做仓库骨架与文档初始化。
6. 不要引入无关框架或 Docker 编排。

目标目录结构：
- docs/
- config/
- gateway/
- edge_device/
- src/
- skills/
- tests/
- scripts/

输出要求：
- 所有文件内容必须与 Vision Butler v5 的最终方案一致。
- README 需要清晰说明项目定位、核心组成和启动顺序。
- AGENTS.md 需要明确写出目标、非目标、禁止事项、目录职责和完成定义。
- docs/ARCHITECTURE.md 需要包含分层架构说明。
- docs/TEST_PLAN.md 需要包含 unit / integration / e2e 三层测试规划。

完成后请：
1. 列出新建文件清单
2. 简要说明每个文件用途
3. 不要额外重构目录
```

---

### Prompt 2：实现数据库与迁移系统

```text id="ejr1fy"
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
```

---

### Prompt 3：实现 Schema 与 Repository 层

```text id="iy3tyj"
你正在为 Vision Butler v5 实现数据模型与 repository 层。

任务目标：
在 `src/schemas/` 和 `src/db/repositories/` 中实现正式的数据模型与查询封装。

必须创建或补齐：
- src/schemas/memory.py
- src/schemas/state.py
- src/schemas/policy.py
- src/schemas/security.py
- src/schemas/device.py
- src/schemas/telegram.py
- src/db/session.py
- src/db/repositories/observation_repo.py
- src/db/repositories/event_repo.py
- src/db/repositories/state_repo.py
- src/db/repositories/device_repo.py
- src/db/repositories/media_repo.py
- src/db/repositories/audit_repo.py
- src/db/repositories/telegram_update_repo.py

必须实现的核心方法：
- save_observation
- save_event
- get_last_seen
- get_object_state
- get_zone_state
- query_recent_events
- get_device_status
- save_telegram_update
- mark_telegram_update_processed
- mark_telegram_update_failed
- save_audit_log

必须遵守：
1. repository 只做数据访问，不混入业务策略。
2. state 与 policy 的复杂逻辑不要写在 repository。
3. 所有时间字段使用一致的 ISO8601 字符串格式。
4. 参数要有基础校验，错误要可读。
5. 不要把 SQL 写散在任意服务中。

输出要求：
- schema 类命名清晰
- repository 方法签名清晰
- 代码可测试
- 尽量提供类型标注

完成后请：
1. 列出每个 repository 的职责
2. 列出已实现的关键查询
3. 标出后续 service 层会依赖哪些方法
```

---

### Prompt 4：实现 FastAPI 后端骨架

```text id="p5vt6x"
你正在为 Vision Butler v5 实现 FastAPI 后端骨架。

任务目标：
建立正式可运行的后端入口、依赖注入和基础路由结构。

必须创建或补齐：
- src/app.py
- src/dependencies.py
- src/routes_memory.py
- src/routes_state.py
- src/routes_policy.py
- src/routes_device.py
- src/routes_ocr.py

最低要求：
- /healthz
- 路由注册清晰
- 基础异常处理
- 统一 JSON 响应格式
- 配置加载与数据库连接初始化

必须遵守：
1. 路由层不直接写复杂业务逻辑。
2. service 层与 repository 层解耦。
3. healthz 必须可用于 smoke test。
4. 不要提前写 nanobot 集成逻辑。
5. 不要引入无关中间件或复杂认证框架。

希望实现的正式路由占位：
- /memory/recent-events
- /memory/last-seen
- /memory/object-state
- /memory/zone-state
- /memory/world-state
- /policy/evaluate-staleness
- /device/status
- /device/command/take-snapshot
- /device/command/get-recent-clip
- /device/ingest/event
- /device/heartbeat
- /ocr/quick-read
- /ocr/extract-fields

完成后请：
1. 说明应用启动入口
2. 列出路由清单
3. 说明哪些路由目前只是骨架，哪些已经可用
```

---

### Prompt 5：实现 memory_service 与 perception_service

```text id="s3f1ka"
你正在为 Vision Butler v5 实现 observation / event / heartbeat 的正式写入链路。

任务目标：
实现：
- src/services/memory_service.py
- src/services/perception_service.py

并打通：
- /device/ingest/event
- /device/heartbeat

必须实现的能力：
1. 接收前端事件 payload
2. 基础设备校验
3. 写入 observations
4. 根据规则选择是否升级为 events
5. 写入 audit_logs
6. heartbeat 刷新 devices 表中的 last_seen、status、温度、负载等字段

必须遵守：
1. perception_service 只负责接入、校验、写 observation、触发后续动作。
2. event 升级规则先做保守版本，不要过度复杂化。
3. state 刷新只预留调用点，不要在此任务里实现完整 state_service。
4. 所有敏感动作必须写 audit。
5. 设备无权限或缺失时返回明确错误。

输入假设：
- schema.sql 已存在
- repository 层已完成
- FastAPI 骨架已存在

输出要求：
- 代码可运行
- 至少补一个最小设备事件 JSON 样例
- 至少补 heartbeat JSON 样例
- 给出集成测试建议

完成后请：
1. 说明事件上报流程
2. 说明 observation 升 event 的当前规则
3. 列出后续 state_service 将接入的钩子点
```

---

你现在已经可以直接开始了。
这三份材料的作用分别是：

* `AGENTS.md`：锁边界
* `TASKS.md`：排执行顺序
* Codex prompts：让 Codex 一次只做一件事，而且做完能验收

下一步最顺的是：
先把这三份放进仓库，然后把 **Prompt 1** 发给 Codex 开始跑。

可以，下面我把**第 6～10 个 Codex 专用提示词**一次性给你。
这 5 个正好接在你已经拿到的前 5 个之后，继续往“正式可运行系统”推进。之所以继续按这种粒度拆，是因为 Codex 官方提示指南明确建议把复杂工程任务拆成更小、更聚焦、可验证的步骤；同时 Codex 也支持并行处理多个软件工程任务，所以你既可以顺序执行，也可以把这些任务拆到不同线程或 worktree 中推进。([developers.openai.com](https://developers.openai.com/codex/prompting?utm_source=chatgpt.com)) ([openai.com](https://openai.com/index/introducing-codex/?utm_source=chatgpt.com))

---

## Prompt 6：实现 `state_service` 与 `policy_service`

```text id="l80rk5"
你正在为 Vision Butler v5 实现最关键的“当前状态推定 + stale/freshness”能力。

任务目标：
实现以下服务与对应路由：
- src/services/state_service.py
- src/services/policy_service.py
- /memory/object-state
- /memory/zone-state
- /memory/world-state
- /policy/evaluate-staleness

项目背景（必须遵守）：
1. Telegram 是正式唯一用户入口，但本任务不直接实现 Telegram 交互。
2. nanobot 是唯一主控宿主，但不是业务真相层。
3. 当前状态必须落在数据库和服务层，不能只靠模型临时回答。
4. object_state 用于回答“某物现在大概率还在不在”。
5. zone_state 用于回答“某区域现在像不像有人 / 有物”。
6. world_state 只做摘要视图，不做复杂图谱。
7. policy_service 负责 freshness、stale、fallback_required、reason_code，不负责数据库写入。

必须实现的能力：
- get_object_state(object_name, camera_id?, zone_id?)
- get_zone_state(camera_id, zone_id)
- get_world_state()
- refresh_object_state(...)
- refresh_zone_state(...)
- evaluate_staleness(query_recency_class, fresh_until, device_status, now)
- classify_query_recency(query_text or query_type)

最小行为要求：
- object_state.state_value 支持：present / absent / unknown
- zone_state.state_value 支持：occupied / empty / likely_occupied / unknown
- policy 输出至少包括：
  - fresh_until
  - is_stale
  - fallback_required
  - reason_code
  - recency_class

必须遵守：
1. state_service 依赖 repository 和 memory/perception 结果，不要绕过 repository 直接写散 SQL。
2. policy_service 不做拍照、不做回复、不做 observation 写入。
3. 对缺失数据要返回“unknown + reason_code”，不要抛出模糊异常。
4. world_state 只做聚合摘要，不要设计成复杂知识图谱。
5. 路由层只负责参数解析和调用 service，不写业务逻辑。

建议输出文件：
- src/services/state_service.py
- src/services/policy_service.py
- src/routes_state.py
- src/routes_policy.py
- tests/unit/test_state_service.py
- tests/unit/test_policy_service.py

验收标准：
- object_state 查询可运行
- zone_state 查询可运行
- stale 逻辑可运行
- fallback_required 能正确输出
- reason_code 始终有值
- pytest 至少覆盖 present/absent/unknown 和 stale/non-stale 分支

完成后请：
1. 说明 object_state 的最小推定逻辑
2. 说明 zone_state 的最小推定逻辑
3. 列出 reason_code 的集合
4. 给出 3 个可直接运行的请求示例
```

---

## Prompt 7：实现 `device_service` 与媒体链路

```text id="lfudxw"
你正在为 Vision Butler v5 实现设备控制与媒体链路。

任务目标：
实现以下服务与路由：
- src/services/device_service.py
- /device/status
- /device/command/take-snapshot
- /device/command/get-recent-clip

项目背景（必须遵守）：
1. RK3566 前端只负责边缘感知、拍照、短视频缓存、心跳，不负责长期记忆与状态真相层。
2. 设备命令由后端 service 发起，前端执行并回传 media URI 或错误。
3. 所有设备命令都必须写 audit_logs。
4. 设备离线时要返回明确错误，不允许静默失败。
5. media_items 是正式媒体索引表，不允许只返回临时路径而不入库。

必须实现的能力：
- get_device_status(device_id)
- take_snapshot(device_id or camera_id)
- get_recent_clip(device_id or camera_id, duration_sec)
- 设备在线/离线判定
- 媒体索引写入 media_items
- 审计写入 audit_logs

输出要求：
- src/services/device_service.py
- src/routes_device.py
- 可选：src/schemas/device.py 补齐命令/响应模型
- tests/unit/test_device_service.py
- tests/integration/test_device_command_flow.py

必须遵守：
1. 当前任务不要实现真实 RK3566 SDK 调用，可用 adapter / stub / interface 方式占位。
2. 但 service 层接口必须稳定，便于后续 edge_device 接入。
3. take_snapshot 和 get_recent_clip 必须返回结构化结果：
   - ok
   - summary
   - data
   - meta
4. data 中至少包含：
   - media_id
   - uri
   - media_type
5. 对设备不可用、参数错误、媒体写入失败分别返回不同错误原因。

建议路由：
- GET /device/status?device_id=...
- POST /device/command/take-snapshot
- POST /device/command/get-recent-clip

验收标准：
- 设备状态查询可用
- take_snapshot 可返回 media URI 并写入 media_items
- get_recent_clip 可返回 clip URI 并写入 media_items
- 所有命令写 audit_logs
- 至少有 1 个设备离线测试分支

完成后请：
1. 说明 device_service 的接口边界
2. 说明媒体索引写入流程
3. 列出设备错误码 / 错误原因集合
4. 给出 2 个请求示例和对应响应示例
```

---

## Prompt 8：实现 OCR 双通道

```text id="5nlffx"
你正在为 Vision Butler v5 实现正式 OCR 能力。

任务目标：
实现模型 OCR + 工具 OCR 双通道的后端能力。

需要创建或补齐：
- src/services/ocr_service.py
- /ocr/quick-read
- /ocr/extract-fields
- ocr_results 的写入逻辑
- OCR 结果与 observations / media_items 的关联逻辑

项目背景（必须遵守）：
1. 简单 OCR 可以由多模态模型直接完成。
2. 结构化 OCR、高价值抽取、需要入库的 OCR 结果必须经过工具化通道。
3. OCR 是正式能力，不是后续增强项。
4. OCR 结果不能只留在模型回答里，必须支持写入 ocr_results。
5. OCR 结果在需要时可以写 observation 或升级为 event。

必须实现的能力：
- quick_read(image_uri or media_id)
- extract_fields(image_uri or media_id, field_schema?)
- save_ocr_result(...)
- attach_ocr_result_to_observation(...)
- 可选：promote_ocr_to_event(...)

返回结构要求：
- raw_text
- fields_json
- boxes_json
- language
- confidence
- source_media_id
- ocr_mode（model_direct / tool_structured）

必须遵守：
1. 当前任务不要真实调用外部 OCR 平台，可用 adapter / interface 占位。
2. service 层必须能清晰区分 quick_read 和 extract_fields。
3. extract_fields 必须支持返回结构化 JSON。
4. 如果 media_id 不存在，要返回明确错误。
5. 路由层不写 OCR 逻辑。

建议输出：
- src/services/ocr_service.py
- src/routes_ocr.py
- tests/unit/test_ocr_service.py
- tests/integration/test_ocr_flow.py

建议路由：
- POST /ocr/quick-read
- POST /ocr/extract-fields

验收标准：
- quick_read 返回文本
- extract_fields 返回结构化字段
- ocr_results 正常入库
- 结果能关联 source_media_id
- 至少覆盖正常 / media 不存在 / OCR 失败 三类测试

完成后请：
1. 说明双通道 OCR 的边界
2. 说明何时只返回结果，何时写 observation/event
3. 列出返回 schema
4. 给出 quick_read 和 extract_fields 的请求示例
```

---

## Prompt 9：实现 MCP Server 层

```text id="s59gkl"
你正在为 Vision Butler v5 实现正式 MCP Server 层。

任务目标：
将后端正式能力暴露为标准 MCP tools / resources / prompts。

需要创建或补齐：
- src/mcp_server/tools/
- src/mcp_server/resources/
- src/mcp_server/prompts/
- MCP server 启动入口

项目背景（必须遵守）：
1. nanobot 通过 MCP 挂载外部能力，不应通过深改核心实现业务逻辑。
2. MCP 是正式能力层，不是临时适配。
3. tools 负责动作，resources 负责上下文读取，prompts 负责模板。
4. 返回结构必须统一、稳定、可供模型整合。

最少必须实现的 MCP Tools：
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

最少必须实现的 Resources：
- resource://memory/observations
- resource://memory/events
- resource://memory/object_states
- resource://memory/zone_states
- resource://policy/freshness
- resource://devices/status

最少必须实现的 Prompts：
- scene_query
- history_query
- last_seen_query
- object_state_query
- zone_state_query
- ocr_query
- device_status_query

统一返回格式：
{
  "ok": true,
  "summary": "...",
  "data": {},
  "meta": {
    "source_layer": "...",
    "confidence": 0.0,
    "fresh_until": "...",
    "is_stale": false,
    "fallback_required": false,
    "trace_id": "..."
  }
}

必须遵守：
1. MCP tool 只是 service 包装层，不重复实现底层业务逻辑。
2. 不要把 Telegram 逻辑写进 MCP。
3. 所有 tool 调用都要尽量保留 trace_id。
4. 不要跳过参数校验。
5. 不要把 prompt 设计成和 tool 耦合死的长文本垃圾堆。

建议输出：
- src/mcp_server/server.py
- src/mcp_server/tools/*.py
- src/mcp_server/resources/*.py
- src/mcp_server/prompts/*.py
- tests/integration/test_mcp_tools.py

验收标准：
- tools 可枚举
- tools 可调用
- resources 可读取
- prompts 可返回模板
- 至少有一个端到端测试：tool -> service -> response

完成后请：
1. 列出所有 MCP tools 与 resources
2. 说明每个 tool 对应的 service
3. 说明统一返回结构
4. 给出 MCP server 的启动方式
```

---

## Prompt 10：实现 Skill 层

```text id="hfw3cd"
你正在为 Vision Butler v5 实现正式 Skill 层。

任务目标：
把项目中的标准问题类型写成正式 Skill 文件，并与 MCP tools / resources 对齐。

必须创建：
- skills/scene_query/SKILL.md
- skills/history_query/SKILL.md
- skills/last_seen/SKILL.md
- skills/object_state/SKILL.md
- skills/zone_state/SKILL.md
- skills/ocr_query/SKILL.md
- skills/device_status/SKILL.md

可选创建：
- src/skill_registry.py

项目背景（必须遵守）：
1. Skill 是正式能力层的一部分。
2. Skill 不是工具本身，而是“如何解决某类问题”的标准执行模板。
3. Skill 必须约束工具调用，而不是鼓励模型自由乱调工具。
4. Skill 必须表达 freshness 与 fallback 规则。
5. Skill 的内容要与项目的 MCP 工具清单一致。

每个 Skill 必须包含：
- name
- description
- trigger_patterns
- allowed_tools
- allowed_resources
- auth_policy
- freshness_policy
- memory_write_policy
- state_effects
- fallback_rules
- steps
- output_schema

各 Skill 的职责：
- scene_query：当前场景、当前画面
- history_query：最近事件、时间范围查询
- last_seen：对象最后出现
- object_state：对象当前大概率状态
- zone_state：区域当前状态
- ocr_query：简单 OCR 与结构化 OCR
- device_status：设备状态与健康信息

必须遵守：
1. Skill 不写数据库访问逻辑。
2. Skill 不重复实现工具逻辑。
3. Skill 内容必须简明、可读、可被模型用作执行模板。
4. scene_query、ocr_query 必须明确说明何时直接回答，何时调用工具。
5. object_state、zone_state 必须明确 stale/fallback 处理。

验收标准：
- 每个 Skill 文件都存在
- 每个 Skill 都包含必需字段
- allowed_tools 与 MCP tool 清单一致
- fallback_rules 有实际内容
- output_schema 明确

完成后请：
1. 总结每个 Skill 的职责
2. 标出各 Skill 允许调用的 tools
3. 说明 freshness_policy 与 fallback_rules 的最小集合
4. 如果创建了 skill_registry.py，说明其职责
```

---



你现在手上已经有：

* 前 5 个提示词
* 这次的第 6～10 个提示词

也就是一共 **10 个 Codex 专用提示词**了。
如果你继续按这个节奏走，下一组就是最后 5 个，也就是：

* T11 nanobot 集成（如果你想拆细，可再细化）
* T12 Telegram 正式交互链路
* T13 RK3566 前端最小正式实现
* T14 测试矩阵落地
* 以及一个**最终收尾 / 联调 / 交付**任务

你下一条只要说一声，我就把**最后 5 个 Codex 专用提示词**也补齐。

可以，下面我把**第 6～10 个 Codex 专用提示词**一次性给你。
这 5 个正好接在你已经拿到的前 5 个之后，继续往“正式可运行系统”推进。之所以继续按这种粒度拆，是因为 Codex 官方提示指南明确建议把复杂工程任务拆成更小、更聚焦、可验证的步骤；同时 Codex 也支持并行处理多个软件工程任务，所以你既可以顺序执行，也可以把这些任务拆到不同线程或 worktree 中推进。([developers.openai.com](https://developers.openai.com/codex/prompting?utm_source=chatgpt.com)) ([openai.com](https://openai.com/index/introducing-codex/?utm_source=chatgpt.com))

---

## Prompt 6：实现 `state_service` 与 `policy_service`

```text id="l80rk5"
你正在为 Vision Butler v5 实现最关键的“当前状态推定 + stale/freshness”能力。

任务目标：
实现以下服务与对应路由：
- src/services/state_service.py
- src/services/policy_service.py
- /memory/object-state
- /memory/zone-state
- /memory/world-state
- /policy/evaluate-staleness

项目背景（必须遵守）：
1. Telegram 是正式唯一用户入口，但本任务不直接实现 Telegram 交互。
2. nanobot 是唯一主控宿主，但不是业务真相层。
3. 当前状态必须落在数据库和服务层，不能只靠模型临时回答。
4. object_state 用于回答“某物现在大概率还在不在”。
5. zone_state 用于回答“某区域现在像不像有人 / 有物”。
6. world_state 只做摘要视图，不做复杂图谱。
7. policy_service 负责 freshness、stale、fallback_required、reason_code，不负责数据库写入。

必须实现的能力：
- get_object_state(object_name, camera_id?, zone_id?)
- get_zone_state(camera_id, zone_id)
- get_world_state()
- refresh_object_state(...)
- refresh_zone_state(...)
- evaluate_staleness(query_recency_class, fresh_until, device_status, now)
- classify_query_recency(query_text or query_type)

最小行为要求：
- object_state.state_value 支持：present / absent / unknown
- zone_state.state_value 支持：occupied / empty / likely_occupied / unknown
- policy 输出至少包括：
  - fresh_until
  - is_stale
  - fallback_required
  - reason_code
  - recency_class

必须遵守：
1. state_service 依赖 repository 和 memory/perception 结果，不要绕过 repository 直接写散 SQL。
2. policy_service 不做拍照、不做回复、不做 observation 写入。
3. 对缺失数据要返回“unknown + reason_code”，不要抛出模糊异常。
4. world_state 只做聚合摘要，不要设计成复杂知识图谱。
5. 路由层只负责参数解析和调用 service，不写业务逻辑。

建议输出文件：
- src/services/state_service.py
- src/services/policy_service.py
- src/routes_state.py
- src/routes_policy.py
- tests/unit/test_state_service.py
- tests/unit/test_policy_service.py

验收标准：
- object_state 查询可运行
- zone_state 查询可运行
- stale 逻辑可运行
- fallback_required 能正确输出
- reason_code 始终有值
- pytest 至少覆盖 present/absent/unknown 和 stale/non-stale 分支

完成后请：
1. 说明 object_state 的最小推定逻辑
2. 说明 zone_state 的最小推定逻辑
3. 列出 reason_code 的集合
4. 给出 3 个可直接运行的请求示例
```

---

## Prompt 7：实现 `device_service` 与媒体链路

```text id="lfudxw"
你正在为 Vision Butler v5 实现设备控制与媒体链路。

任务目标：
实现以下服务与路由：
- src/services/device_service.py
- /device/status
- /device/command/take-snapshot
- /device/command/get-recent-clip

项目背景（必须遵守）：
1. RK3566 前端只负责边缘感知、拍照、短视频缓存、心跳，不负责长期记忆与状态真相层。
2. 设备命令由后端 service 发起，前端执行并回传 media URI 或错误。
3. 所有设备命令都必须写 audit_logs。
4. 设备离线时要返回明确错误，不允许静默失败。
5. media_items 是正式媒体索引表，不允许只返回临时路径而不入库。

必须实现的能力：
- get_device_status(device_id)
- take_snapshot(device_id or camera_id)
- get_recent_clip(device_id or camera_id, duration_sec)
- 设备在线/离线判定
- 媒体索引写入 media_items
- 审计写入 audit_logs

输出要求：
- src/services/device_service.py
- src/routes_device.py
- 可选：src/schemas/device.py 补齐命令/响应模型
- tests/unit/test_device_service.py
- tests/integration/test_device_command_flow.py

必须遵守：
1. 当前任务不要实现真实 RK3566 SDK 调用，可用 adapter / stub / interface 方式占位。
2. 但 service 层接口必须稳定，便于后续 edge_device 接入。
3. take_snapshot 和 get_recent_clip 必须返回结构化结果：
   - ok
   - summary
   - data
   - meta
4. data 中至少包含：
   - media_id
   - uri
   - media_type
5. 对设备不可用、参数错误、媒体写入失败分别返回不同错误原因。

建议路由：
- GET /device/status?device_id=...
- POST /device/command/take-snapshot
- POST /device/command/get-recent-clip

验收标准：
- 设备状态查询可用
- take_snapshot 可返回 media URI 并写入 media_items
- get_recent_clip 可返回 clip URI 并写入 media_items
- 所有命令写 audit_logs
- 至少有 1 个设备离线测试分支

完成后请：
1. 说明 device_service 的接口边界
2. 说明媒体索引写入流程
3. 列出设备错误码 / 错误原因集合
4. 给出 2 个请求示例和对应响应示例
```

---

## Prompt 8：实现 OCR 双通道

```text id="5nlffx"
你正在为 Vision Butler v5 实现正式 OCR 能力。

任务目标：
实现模型 OCR + 工具 OCR 双通道的后端能力。

需要创建或补齐：
- src/services/ocr_service.py
- /ocr/quick-read
- /ocr/extract-fields
- ocr_results 的写入逻辑
- OCR 结果与 observations / media_items 的关联逻辑

项目背景（必须遵守）：
1. 简单 OCR 可以由多模态模型直接完成。
2. 结构化 OCR、高价值抽取、需要入库的 OCR 结果必须经过工具化通道。
3. OCR 是正式能力，不是后续增强项。
4. OCR 结果不能只留在模型回答里，必须支持写入 ocr_results。
5. OCR 结果在需要时可以写 observation 或升级为 event。

必须实现的能力：
- quick_read(image_uri or media_id)
- extract_fields(image_uri or media_id, field_schema?)
- save_ocr_result(...)
- attach_ocr_result_to_observation(...)
- 可选：promote_ocr_to_event(...)

返回结构要求：
- raw_text
- fields_json
- boxes_json
- language
- confidence
- source_media_id
- ocr_mode（model_direct / tool_structured）

必须遵守：
1. 当前任务不要真实调用外部 OCR 平台，可用 adapter / interface 占位。
2. service 层必须能清晰区分 quick_read 和 extract_fields。
3. extract_fields 必须支持返回结构化 JSON。
4. 如果 media_id 不存在，要返回明确错误。
5. 路由层不写 OCR 逻辑。

建议输出：
- src/services/ocr_service.py
- src/routes_ocr.py
- tests/unit/test_ocr_service.py
- tests/integration/test_ocr_flow.py

建议路由：
- POST /ocr/quick-read
- POST /ocr/extract-fields

验收标准：
- quick_read 返回文本
- extract_fields 返回结构化字段
- ocr_results 正常入库
- 结果能关联 source_media_id
- 至少覆盖正常 / media 不存在 / OCR 失败 三类测试

完成后请：
1. 说明双通道 OCR 的边界
2. 说明何时只返回结果，何时写 observation/event
3. 列出返回 schema
4. 给出 quick_read 和 extract_fields 的请求示例
```

---

## Prompt 9：实现 MCP Server 层

```text id="s59gkl"
你正在为 Vision Butler v5 实现正式 MCP Server 层。

任务目标：
将后端正式能力暴露为标准 MCP tools / resources / prompts。

需要创建或补齐：
- src/mcp_server/tools/
- src/mcp_server/resources/
- src/mcp_server/prompts/
- MCP server 启动入口

项目背景（必须遵守）：
1. nanobot 通过 MCP 挂载外部能力，不应通过深改核心实现业务逻辑。
2. MCP 是正式能力层，不是临时适配。
3. tools 负责动作，resources 负责上下文读取，prompts 负责模板。
4. 返回结构必须统一、稳定、可供模型整合。

最少必须实现的 MCP Tools：
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

最少必须实现的 Resources：
- resource://memory/observations
- resource://memory/events
- resource://memory/object_states
- resource://memory/zone_states
- resource://policy/freshness
- resource://devices/status

最少必须实现的 Prompts：
- scene_query
- history_query
- last_seen_query
- object_state_query
- zone_state_query
- ocr_query
- device_status_query

统一返回格式：
{
  "ok": true,
  "summary": "...",
  "data": {},
  "meta": {
    "source_layer": "...",
    "confidence": 0.0,
    "fresh_until": "...",
    "is_stale": false,
    "fallback_required": false,
    "trace_id": "..."
  }
}

必须遵守：
1. MCP tool 只是 service 包装层，不重复实现底层业务逻辑。
2. 不要把 Telegram 逻辑写进 MCP。
3. 所有 tool 调用都要尽量保留 trace_id。
4. 不要跳过参数校验。
5. 不要把 prompt 设计成和 tool 耦合死的长文本垃圾堆。

建议输出：
- src/mcp_server/server.py
- src/mcp_server/tools/*.py
- src/mcp_server/resources/*.py
- src/mcp_server/prompts/*.py
- tests/integration/test_mcp_tools.py

验收标准：
- tools 可枚举
- tools 可调用
- resources 可读取
- prompts 可返回模板
- 至少有一个端到端测试：tool -> service -> response

完成后请：
1. 列出所有 MCP tools 与 resources
2. 说明每个 tool 对应的 service
3. 说明统一返回结构
4. 给出 MCP server 的启动方式
```

---

## Prompt 10：实现 Skill 层

```text id="hfw3cd"
你正在为 Vision Butler v5 实现正式 Skill 层。

任务目标：
把项目中的标准问题类型写成正式 Skill 文件，并与 MCP tools / resources 对齐。

必须创建：
- skills/scene_query/SKILL.md
- skills/history_query/SKILL.md
- skills/last_seen/SKILL.md
- skills/object_state/SKILL.md
- skills/zone_state/SKILL.md
- skills/ocr_query/SKILL.md
- skills/device_status/SKILL.md

可选创建：
- src/skill_registry.py

项目背景（必须遵守）：
1. Skill 是正式能力层的一部分。
2. Skill 不是工具本身，而是“如何解决某类问题”的标准执行模板。
3. Skill 必须约束工具调用，而不是鼓励模型自由乱调工具。
4. Skill 必须表达 freshness 与 fallback 规则。
5. Skill 的内容要与项目的 MCP 工具清单一致。

每个 Skill 必须包含：
- name
- description
- trigger_patterns
- allowed_tools
- allowed_resources
- auth_policy
- freshness_policy
- memory_write_policy
- state_effects
- fallback_rules
- steps
- output_schema

各 Skill 的职责：
- scene_query：当前场景、当前画面
- history_query：最近事件、时间范围查询
- last_seen：对象最后出现
- object_state：对象当前大概率状态
- zone_state：区域当前状态
- ocr_query：简单 OCR 与结构化 OCR
- device_status：设备状态与健康信息

必须遵守：
1. Skill 不写数据库访问逻辑。
2. Skill 不重复实现工具逻辑。
3. Skill 内容必须简明、可读、可被模型用作执行模板。
4. scene_query、ocr_query 必须明确说明何时直接回答，何时调用工具。
5. object_state、zone_state 必须明确 stale/fallback 处理。

验收标准：
- 每个 Skill 文件都存在
- 每个 Skill 都包含必需字段
- allowed_tools 与 MCP tool 清单一致
- fallback_rules 有实际内容
- output_schema 明确

完成后请：
1. 总结每个 Skill 的职责
2. 标出各 Skill 允许调用的 tools
3. 说明 freshness_policy 与 fallback_rules 的最小集合
4. 如果创建了 skill_registry.py，说明其职责
```

---

## Prompt 11：nanobot 集成与正式 Telegram 宿主配置

```text id="ctr75k"
你正在为 Vision Butler v5 完成 nanobot 集成。

任务目标：
将 nanobot 作为正式唯一主控宿主接入 Telegram、Qwen3.5、多实例 workspace 和 MCP servers。

必须创建或补齐：
- config/nanobot.config.json
- gateway/nanobot_workspace/
- scripts/start_gateway.sh
- docs/DEPLOYMENT.md 中关于 nanobot 的启动说明

项目背景（必须遵守）：
1. Telegram 是正式唯一用户入口。
2. nanobot 是唯一主控宿主，但不是业务真相层。
3. 所有业务能力优先通过 MCP servers 暴露给 nanobot。
4. 不要深改 nanobot 核心代码。
5. 要支持正式实例和开发实例分离。

配置至少应覆盖：
- Telegram channel enabled
- Telegram token 占位
- allowFrom 配置
- model provider / model name
- tools.mcpServers
- workspace 路径
- runtime 相关目录
- 可选：tool timeout / concurrency

必须遵守：
1. 所有敏感配置用占位符，不要填真实 token。
2. config 文件结构要尽量贴近 nanobot 正式能力边界。
3. 不要把 MCP server 逻辑写进 nanobot 配置之外的 hack 脚本。
4. start_gateway.sh 要能表达完整启动意图。
5. DEPLOYMENT.md 要说明正式实例 / 开发实例的区别。

验收标准：
- nanobot.config.json 结构清晰
- 可以看出 Telegram、模型、MCP、workspace 四部分配置
- start_gateway.sh 有清晰命令和环境变量说明
- DEPLOYMENT.md 说明正式与测试实例如何隔离

完成后请：
1. 解释 nanobot 配置结构
2. 说明 allowFrom、workspace、mcpServers 的作用
3. 给出正式实例和开发实例的配置差异建议
4. 说明为什么此任务不应通过深改 nanobot 完成
```

---

你现在手上已经有：

* 前 5 个提示词
* 这次的第 6～10 个提示词

也就是一共 **10 个 Codex 专用提示词**了。
如果你继续按这个节奏走，下一组就是最后 5 个，也就是：

* T11 nanobot 集成（如果你想拆细，可再细化）
* T12 Telegram 正式交互链路
* T13 RK3566 前端最小正式实现
* T14 测试矩阵落地
* 以及一个**最终收尾 / 联调 / 交付**任务

你下一条只要说一声，我就把**最后 5 个 Codex 专用提示词**也补齐。

可以，下面我把**最后 5 个 Codex 专用提示词**一次性补齐。
这样你手上就有完整的 15 个任务包了，能直接按顺序推进，也能按模块并行推进。Codex 官方能力说明里明确提到，它既适合在本地仓库中读代码、改文件、跑命令，也支持更复杂的工作流；而 nanobot 当前 README 也明确支持 Telegram、多实例配置和通过 `--config` / workspace 组织运行时，因此把“入口层、宿主层、边缘层、测试层、联调收尾”拆成最后 5 个任务，是很适合 Codex 的做法。([developers.openai.com](https://developers.openai.com/codex/cli/features?utm_source=chatgpt.com)) ([github.com](https://github.com/HKUDS/nanobot/blob/main/README.md?utm_source=chatgpt.com))

---

## Prompt 11B：Telegram 正式交互链路

```text id="twt9xh"
你正在为 Vision Butler v5 实现 Telegram 正式交互链路。

任务目标：
把 Telegram 作为正式唯一用户入口完整打通，并与 nanobot / Qwen3.5 / MCP tools 对接。

需要创建或补齐：
- src/services/reply_service.py 或 src/services/reply_builder.py
- Telegram update 去重处理逻辑
- 长消息分片逻辑
- sendChatAction 调用逻辑
- 基础命令式入口规范
- 与 telegram_updates 表的状态联动

项目背景（必须遵守）：
1. Telegram 是正式唯一用户入口，不是临时入口。
2. Telegram Bot API 的 getUpdates 与 setWebhook 是互斥方式，未消费更新在服务器端最长只保留 24 小时。
3. Telegram 文本消息单条有长度限制，因此系统必须支持长回复分片。
4. 长耗时视觉任务必须有 processing / typing / upload_photo 等状态提示。
5. 入口层不能承载状态真相层逻辑，业务事实必须继续由后端 services + MCP 提供。

必须实现的能力：
- save incoming update with dedup
- route text / photo / video / command
- send processing status
- split long text replies
- persist processed / failed update status
- 将 MCP tool 返回结果格式化为 Telegram 友好回复
- 支持至少这些命令：
  - /snapshot
  - /clip
  - /lastseen
  - /state
  - /ocr
  - /device
  - /help

必须遵守：
1. 不要在 Telegram 处理层直接写 state / policy / OCR 业务逻辑。
2. 不要把 nanobot 核心协议重写成自定义机器人框架。
3. 不要跳过 update_id 去重。
4. 对失败 update 必须写 telegram_updates.status = failed。
5. 回复要考虑文本和媒体混合场景。

建议输出：
- src/services/reply_service.py 或 reply_builder.py
- src/schemas/telegram.py
- tests/integration/test_telegram_message_flow.py
- tests/e2e/test_telegram_commands.py
- docs/TELEGRAM_FLOW.md

验收标准：
- 文本问答可用
- 图片输入可转发给模型 / OCR 流程
- 命令入口可用
- 长消息自动分片
- 长任务有 sendChatAction
- telegram_updates 有 received / processed / failed 三种状态流转

完成后请：
1. 说明 Telegram update 生命周期
2. 说明长消息分片规则
3. 说明图片/视频/命令三类输入的处理分支
4. 给出 3 个 Telegram 请求示例和对应输出示例
```

---

## Prompt 12：RK3566 前端最小正式实现

```text id="w3fi7e"
你正在为 Vision Butler v5 实现 RK3566 单目前端的最小正式版本。

任务目标：
建立 edge_device/ 下可运行的前端骨架，使其能够完成采集、轻量检测、事件压缩、心跳上报、拍照和最近视频片段回传。

必须创建或补齐：
- edge_device/capture/
- edge_device/inference/
- edge_device/tracking/
- edge_device/compression/
- edge_device/cache/
- edge_device/health/
- edge_device/api/

项目背景（必须遵守）：
1. 前端硬件是 2G+16G 的 RK3566 单目前端。
2. 前端定位是“边缘事件感知终端”，不是完整智能体。
3. 前端负责：
   - 图像采集
   - 轻量检测
   - 轻量跟踪
   - 事件压缩
   - 快照缓存
   - 最近片段缓存
   - 设备状态上报
4. 前端不负责：
   - 长期记忆
   - 状态推理
   - stale/freshness
   - Telegram 交互
   - MCP
   - 权限控制
5. 当前任务允许使用 adapter / stub 模拟模型调用，但结构必须为后续 RKNN 接入预留清晰边界。

必须实现的能力：
- capture latest frame
- run lightweight detection interface
- assign / pass through track_id
- compress detections into event envelope
- maintain ring buffer for recent snapshots / clips
- heartbeat payload assembly
- respond to take_snapshot command
- respond to get_recent_clip command

建议输出：
- edge_device/api/server.py 或等价入口
- edge_device/capture/camera.py
- edge_device/inference/detector.py
- edge_device/tracking/tracker.py
- edge_device/compression/event_compressor.py
- edge_device/cache/ring_buffer.py
- edge_device/health/heartbeat.py
- docs/EDGE_DEVICE.md

必须遵守：
1. 不要在前端写业务数据库逻辑。
2. 不要把后端 policy/state 逻辑挪到前端。
3. 所有对外输出都要走统一 event envelope / command response。
4. 拍照与 clip 返回必须可被后端 device_service 消费。
5. 代码要对后续接入 RKNN / GStreamer / V4L2 友好。

验收标准：
- 能构造 device heartbeat
- 能生成 observation 风格事件 envelope
- take_snapshot 可返回 snapshot uri/path
- get_recent_clip 可返回 clip uri/path
- ring buffer 行为可测试
- 至少有前端单元测试或模拟测试

完成后请：
1. 说明前端模块职责划分
2. 给出 event envelope 示例
3. 给出 heartbeat payload 示例
4. 标出哪些位置后续接真实 RKNN / 相机驱动
```

---

## Prompt 13：安全与访问控制落地

```text id="6j98f5"
你正在为 Vision Butler v5 实现正式安全与访问控制层。

任务目标：
实现统一的 security_guard / access_policy，使 Telegram 用户、设备、tools、resources 和媒体访问都受控，并可审计。

需要创建或补齐：
- src/security/security_guard.py
- src/security/access_policy.py
- src/schemas/security.py
- tests/unit/test_security_guard.py
- tests/integration/test_access_control_flow.py

项目背景（必须遵守）：
1. nanobot 的 allowFrom 是入口层白名单，不等于系统内部完整权限模型。
2. 系统内部还需要：
   - user_allowlist
   - device_allowlist
   - tool_allowlist_per_skill
   - resource_scope_per_skill
   - media_visibility_scope
3. 所有拒绝行为都必须进入 audit_logs。
4. 安全层要独立，不允许把权限规则散落在路由和服务里。

必须实现的能力：
- validate_user_access(user_id / telegram_user_id)
- validate_device_access(device_id, api_key or equivalent)
- validate_tool_access(skill_name, tool_name)
- validate_resource_access(skill_name, resource_uri)
- validate_media_visibility(user_id, media_id)
- audit_allow / audit_deny

必须遵守：
1. security_guard 只负责校验和审计，不负责业务回答。
2. 不要把配置写死在代码里，应从 access.yaml / devices.yaml 等配置加载。
3. 拒绝必须返回明确 reason。
4. 所有工具调用前必须有 validate_tool_access 的接入点。
5. 所有资源读取前必须有 validate_resource_access 的接入点。

建议输出：
- access policy 数据模型
- guard 层服务
- 与 repository / audit_repo 的集成
- 示例 access.yaml 结构
- 测试覆盖 allow / deny / missing policy / unauthorized device

验收标准：
- 非 allowlist 用户会被拒绝
- 非 allowlist 设备会被拒绝
- Skill 调未授权 tool 会被拒绝
- 读取未授权 resource 会被拒绝
- 读取未授权 media 会被拒绝
- 所有拒绝行为有 audit 记录

完成后请：
1. 说明安全模型结构
2. 列出至少 5 个 reason_code / denial reason
3. 说明 allowFrom 与内部 security_guard 的边界区别
4. 给出 access.yaml 示例
```

---

## Prompt 14：测试矩阵落地

```text id="fhgj4o"
你正在为 Vision Butler v5 把项目书中的测试矩阵落成真实测试。

任务目标：
实现 unit / integration / e2e 三层测试，并补齐 smoke test 脚本。

需要创建或补齐：
- tests/unit/
- tests/integration/
- tests/e2e/
- scripts/smoke_test.sh

项目背景（必须遵守）：
1. 本项目必须测试，不允许“功能先写，测试以后补”。
2. 测试矩阵已在项目书中定义，必须尽量落地。
3. Telegram 是正式入口，因此必须至少有 Telegram 相关集成或 e2e 测试。
4. 核心风险区在：state / policy / OCR / access control / device flow / Telegram flow。

至少需要覆盖的测试：
### Unit
- test_state_service.py
- test_policy_service.py
- test_security_guard.py
- test_memory_service.py
- test_ocr_service.py

### Integration
- test_device_event_flow.py
- test_object_state_flow.py
- test_zone_state_flow.py
- test_stale_fallback_flow.py
- test_access_control_flow.py
- test_telegram_message_flow.py

### E2E
- test_current_scene_query.py
- test_last_seen_query.py
- test_object_state_query.py
- test_ocr_query.py
- test_take_snapshot_command.py
- test_device_offline_alert.py

必须遵守：
1. 测试文件命名清晰。
2. 尽量避免真实外部依赖，优先 mock / fake adapter。
3. 测试要围绕正式行为，不要只测 trivial getter。
4. smoke_test.sh 至少验证：
   - 数据库初始化
   - /healthz
   - 一个核心查询路由
5. 如果暂时无法做完整 e2e，可先用 stub / fake nanobot/Telegram 层，但目录和意图必须完整。

验收标准：
- pytest -q 可运行
- 三层测试目录完整
- 至少核心路径有可运行测试
- smoke_test.sh 可执行
- 测试名称和项目书一致

完成后请：
1. 列出已创建测试文件
2. 标注哪些是真单测，哪些是假集成
3. 说明当前尚未 fully-real 的测试点
4. 给出推荐的 CI 执行顺序
```

---

## Prompt 15：最终联调、收尾与交付打包

```text id="xywuhl"
你正在为 Vision Butler v5 做最终联调与交付打包。

任务目标：
在不重构核心边界的前提下，对整个仓库做一次“可运行、可验收、可交付”的最终收尾。

需要完成：
- 检查目录结构是否与 AGENTS.md / PRODUCT_PLAN.md 一致
- 检查 config/ 是否齐全
- 检查 scripts/ 是否齐全
- 检查 docs/ 是否齐全
- 检查 tests/ 是否齐全
- 补齐遗漏的 README / 使用说明
- 补齐最小启动脚本
- 跑 smoke test
- 输出交付摘要

项目背景（必须遵守）：
1. 不要趁联调阶段大改架构。
2. 不要顺手做无关优化。
3. 所有补丁必须服务于“让项目能启动、能测试、能理解”。
4. 不要改动 nanobot 的核心外部依赖方式。
5. 所有正式入口、正式能力、正式文档都必须可被定位。

必须检查的交付项：
- AGENTS.md
- README.md
- docs/PRODUCT_PLAN.md
- docs/ARCHITECTURE.md
- docs/TEST_PLAN.md
- docs/DEPLOYMENT.md
- schema.sql
- migrations/
- config/*.yaml
- config/nanobot.config.json
- src/app.py
- src/mcp_server/
- skills/
- tests/
- scripts/init_db.sh
- scripts/start_backend.sh
- scripts/start_gateway.sh
- scripts/start_edge.sh
- scripts/smoke_test.sh

必须遵守：
1. 只做“让交付完整”的修改。
2. 缺文档就补文档，缺脚本就补脚本，缺占位就补占位。
3. 不要因为联调而把 TODO 伪装成 DONE。
4. 对尚未完全实现的部分，必须在 README 或 DEPLOYMENT.md 中诚实标注。
5. 输出必须包含“当前可运行范围”和“后续待接真实适配器范围”。

验收标准：
- 仓库结构完整
- 启动脚本存在
- smoke test 可运行
- 文档可指导第一次启动
- 明确哪些地方仍是 stub / adapter

完成后请：
1. 给出交付清单
2. 标出当前已真实可运行的模块
3. 标出当前仍为 stub / adapter 的模块
4. 给出建议的第一次启动顺序
```

---

到这里，你已经拿到 **完整 15 个 Codex 专用提示词** 了：

* 前 5 个：仓库、数据库、配置、Schema/Repo、FastAPI 骨架
* 第 6～10 个：state/policy、device/media、OCR、MCP、Skill
* 第 11～15 个：Telegram、RK3566 前端、安全、测试、最终联调

现在最实际的建议是：

**不要一次把 15 个都扔给 Codex。**
按下面顺序最稳：

1. Prompt 1
2. Prompt 2
3. Prompt 3
4. Prompt 4
5. Prompt 5
6. Prompt 6～10 可半并行
7. Prompt 11 + 11B + 12～15 做集成与收尾

如果你愿意，我下一条可以继续给你一个真正能直接用的 **`config/nanobot.config.json` 初版模板**，再加上 **7 个 `SKILL.md` 初版内容**。
