可以，下面我把两份一起给你：

1. `README.md` 初版
2. `docs/ARCHITECTURE.md` 初版

这两份内容已经按你现在的正式方案收束好了：**Telegram 是正式唯一入口，nanobot 是唯一主控宿主，Qwen3.5 多模态模型负责理解与工具决策，MCP 是标准能力暴露层，SQLite + FTS5 是正式单机数据层**。这些边界和外部事实是对齐的：Telegram Bot API 是 HTTP 接口，`getUpdates` 与 `setWebhook` 是两种互斥更新方式；nanobot 当前公开支持 Telegram、workspace、多实例和 `tools.mcpServers`；MCP 规范明确区分 tools、resources、prompts；Qwen Function Calling 是“模型决定是否调工具，应用执行，再回灌结果”的模式；SQLite FTS5 则是通过虚拟表提供全文检索。([core.telegram.org](https://core.telegram.org/bots/api?utm_source=chatgpt.com)) ([core.telegram.org](https://core.telegram.org/bots/webhooks?utm_source=chatgpt.com)) ([github.com](https://github.com/HKUDS/nanobot/blob/main/README.md?utm_source=chatgpt.com)) ([modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-03-26?utm_source=chatgpt.com)) ([modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-06-18/server/tools?utm_source=chatgpt.com)) ([help.aliyun.com](https://help.aliyun.com/zh/model-studio/qwen-function-calling?utm_source=chatgpt.com)) ([sqlite.org](https://sqlite.org/fts5.html?utm_source=chatgpt.com))

---

## `README.md`

````text id="m2pwjk"
# Vision Butler v5

基于 nanobot 的视觉管家系统 v5。  
正式入口为 Telegram，正式宿主为 nanobot，正式认知核心为 Qwen3.5 多模态模型，正式能力层为 MCP + Skills，正式前端为 RK3566 单目前端，正式事实层为 backend sidecar services。

---

## 1. 项目简介

Vision Butler v5 是一个通过 Telegram 进行交互的视觉管家系统。  
它不是普通“看图聊天机器人”，也不是传统安防 NVR，而是一个能够：

- 回答当前画面里有什么
- 回答最近发生了什么
- 回答某个对象最后一次在哪里出现
- 回答某个对象现在大概率还在不在
- 回答某个区域当前像不像有人或有物
- 对图片、快照和局部内容做简单 OCR / 结构化 OCR
- 主动拍照、回传最近视频片段
- 查询设备在线状态、负载、心跳与异常

的完整视觉管家系统。

---

## 2. 系统正式组成

系统由以下部分组成：

### 2.1 Telegram Bot
唯一正式用户入口，负责接收文本、图片、命令与媒体请求。

### 2.2 nanobot
唯一主控入口与 Agent 宿主，负责：
- 会话管理
- 模型调用
- Skill 加载
- MCP 工具挂载
- 最终回复生成

### 2.3 Qwen3.5 多模态模型
负责：
- 理解用户问题
- 理解图片与短视频
- 执行简单 OCR
- 判断是否调用工具
- 整合工具结果并输出回答

### 2.4 MCP Server 层
负责把正式业务能力暴露为：
- Tools
- Resources
- Prompts

### 2.5 Skills
负责定义标准执行模板：
- 何时调用哪些工具
- 哪些工具可用
- freshness 策略
- fallback 规则
- 输出结构要求

### 2.6 Backend Sidecar Services
负责：
- perception_service
- memory_service
- state_service
- policy_service
- security_guard
- device_service
- ocr_service

### 2.7 RK3566 单目前端
负责：
- 相机采集
- 轻量检测
- 轻量跟踪
- 事件压缩
- 快照缓存
- 最近视频片段缓存
- 设备心跳
- 响应拍照和取 clip 命令

---

## 3. 正式能力

本项目首发即纳入正式范围的能力包括：

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

---

## 4. 核心设计原则

### 4.1 入口统一
Telegram 是正式唯一入口。

### 4.2 主控统一
nanobot 是唯一主控宿主，但不是业务真相层。

### 4.3 能力分层
- 模型负责理解与决策
- 工具负责事实与动作
- 前端负责事件感知
- 后端负责状态真相

### 4.4 单目前端边界清晰
RK3566 单目前端不是完整智能体。  
它只负责边缘感知，不负责长期记忆、复杂状态聚合、Telegram 交互和权限控制。

### 4.5 状态显式化
系统不只回答“最后一次看到”，还要回答“现在大概率还在不在”，因此必须有 state / policy 层。

---

## 5. 明确非目标

当前版本明确不做：

- 运动控制
- ROS / ROS2 集成
- 3D 建图
- 多机器人协同
- 云端多租户 SaaS
- 高并发分布式部署
- 多摄像头空间拓扑重建
- 单目前端精确三维定位
- 完整 Web 管理后台

---

## 6. 仓库结构

推荐仓库结构如下：

```text
vision_butler/
├─ AGENTS.md
├─ README.md
├─ schema.sql
├─ migrations/
├─ docs/
├─ config/
├─ gateway/
├─ edge_device/
├─ src/
├─ skills/
├─ tests/
└─ scripts/
````

核心目录职责：

* `docs/`：产品与架构文档
* `config/`：配置文件
* `gateway/`：nanobot workspace
* `edge_device/`：RK3566 前端代码
* `src/`：后端服务、路由、schema、repository、MCP server
* `skills/`：Skill 定义
* `tests/`：测试
* `scripts/`：初始化与启动脚本

---

## 7. 关键数据层

正式数据层使用 SQLite + FTS5。

核心正式表：

* users
* devices
* observations
* events
* object_states
* zone_states
* media_items
* audit_logs
* telegram_updates
* notification_rules
* facts
* ocr_results

FTS 表：

* observations_fts
* events_fts
* ocr_results_fts

---

## 8. 正式 MCP 能力

### 8.1 Tools

* take_snapshot
* get_recent_clip
* describe_scene
* last_seen_object
* get_object_state
* get_zone_state
* get_world_state
* query_recent_events
* evaluate_staleness
* ocr_quick_read
* ocr_extract_fields
* device_status
* refresh_object_state
* refresh_zone_state

### 8.2 Resources

* resource://memory/observations
* resource://memory/events
* resource://memory/object_states
* resource://memory/zone_states
* resource://policy/freshness
* resource://devices/status

### 8.3 Prompts

* scene_query
* history_query
* last_seen_query
* object_state_query
* zone_state_query
* ocr_query
* device_status_query

---

## 9. 正式 Skills

* scene_query
* history_query
* last_seen
* object_state
* zone_state
* ocr_query
* device_status

---

## 10. 运行顺序

建议正式启动顺序：

1. 初始化数据库
2. 启动 backend API
3. 启动 MCP servers
4. 启动 nanobot gateway
5. 启动 RK3566 edge service
6. 执行 smoke test
7. 用 Telegram 做首次验证

---

## 11. 快速开始

### 11.1 初始化数据库

执行：

* `./scripts/init_db.sh`

### 11.2 启动后端

执行：

* `./scripts/start_backend.sh`

### 11.3 启动 nanobot

执行：

* `./scripts/start_gateway.sh`

### 11.4 启动边缘前端

执行：

* `./scripts/start_edge.sh`

### 11.5 执行 smoke test

执行：

* `./scripts/smoke_test.sh`

---

## 12. 测试要求

项目正式测试分为三层：

### Unit

* state_service
* policy_service
* security_guard
* memory_service
* ocr_service

### Integration

* device_event_flow
* object_state_flow
* zone_state_flow
* stale_fallback_flow
* access_control_flow
* telegram_message_flow

### E2E

* current_scene_query
* last_seen_query
* object_state_query
* ocr_query
* take_snapshot_command
* device_offline_alert

---

## 13. 当前开发阶段说明

当前仓库允许部分能力先以 adapter / stub 方式落地，包括：

* 真实 RKNN 检测器
* 真实 OCR provider
* 真实 edge 设备命令执行
* 真实 MCP server 框架适配

但以下部分必须真实存在：

* 仓库结构
* 数据库 schema
* 配置文件
* 后端服务骨架
* MCP 能力定义
* Skill 定义
* 启动脚本
* 测试骨架
* 文档

---

## 14. 开发规则

请先阅读：

* `AGENTS.md`
* `docs/ARCHITECTURE.md`
* `docs/TEST_PLAN.md`
* `docs/DEPLOYMENT.md`
* `TASKS.md`

本项目推荐按小任务推进，不建议大范围无边界改动。

---

## 15. 完成定义

一个任务只有同时满足以下条件才算完成：

1. 目标文件已创建或正确修改
2. 代码可运行
3. 对应测试可执行
4. 不破坏目录职责边界
5. 与产品计划书一致
6. 关键行为可追踪、可审计

---

## 16. 备注

本 README 是仓库级入口文档。
更完整的正式说明请见：

* `docs/ARCHITECTURE.md`
* `docs/DEPLOYMENT.md`
* `docs/TEST_PLAN.md`
* `AGENTS.md`

````

这份 README 里关于 Telegram、nanobot、MCP、Qwen Function Calling、SQLite FTS5 的设计边界，已经与官方公开能力保持一致。([core.telegram.org](https://core.telegram.org/bots/api?utm_source=chatgpt.com)) ([github.com](https://github.com/HKUDS/nanobot/blob/main/README.md?utm_source=chatgpt.com)) ([modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-03-26?utm_source=chatgpt.com)) ([help.aliyun.com](https://help.aliyun.com/zh/model-studio/qwen-function-calling?utm_source=chatgpt.com)) ([sqlite.org](https://sqlite.org/fts5.html?utm_source=chatgpt.com))

---

## `docs/ARCHITECTURE.md`

```text id="78q7z6"
# ARCHITECTURE.md

## 1. 文档目的

本文档用于说明 Vision Butler v5 的正式架构设计、模块职责、数据流与系统边界。

本架构不是通用聊天机器人架构，而是一个“Telegram 正式入口 + nanobot 正式宿主 + Qwen3.5 多模态认知核心 + MCP/Skill 能力层 + RK3566 单目前端 + backend sidecar 事实层”的完整视觉管家架构。

---

## 2. 总体架构原则

### 2.1 单一用户入口
系统只有一个正式用户入口：Telegram。

### 2.2 单一主控宿主
系统只有一个正式主控宿主：nanobot。

### 2.3 认知与事实分离
Qwen3.5 负责理解、视觉认知、简单 OCR 和工具决策；  
状态、时效、设备、OCR 结构化结果与审计必须落在服务层与数据库中。

### 2.4 工具与模板分离
MCP 提供正式工具、资源和提示模板；  
Skill 负责某类问题的标准执行流程。

### 2.5 边缘与后端分离
RK3566 前端负责事件感知与媒体缓存；  
后端负责 observation / event / state / policy / security / OCR / device 管理。

---

## 3. 正式分层

## 3.1 入口层
### Telegram Bot
职责：
- 接收文本、图片、视频、命令
- 作为正式唯一用户入口
- 将 update 交给 nanobot / gateway

不负责：
- 状态计算
- 设备控制逻辑
- OCR 结构化逻辑
- 权限真相层

---

## 3.2 主控层
### nanobot Gateway
职责：
- 会话管理
- 模型调度
- Skill 加载
- MCP tool 挂载
- 最终回复生成
- workspace / runtime 管理

不负责：
- observation / state / policy 真相存储
- 设备认证与命令持久化
- 媒体授权规则
- 业务数据库 schema

---

## 3.3 认知层
### Qwen3.5 多模态模型
职责：
- 理解用户意图
- 理解图片与短视频
- 简单 OCR
- 判断是否调用外部工具
- 整合工具结果并输出自然语言或结构化结果

不负责：
- 长期保存状态
- 充当数据库
- 直接替代 stale/freshness 规则
- 替代权限系统

---

## 3.4 能力层
### MCP
正式能力分为：
- Tools
- Resources
- Prompts

作用：
- 让 nanobot 和模型看到统一能力面
- 把 sidecar services 变成模型可调用的标准能力

### Skills
作用：
- 规定问题类型与执行模板
- 指定 allowed_tools / allowed_resources
- 定义 freshness_policy / fallback_rules / output_schema

---

## 3.5 业务事实层
正式 sidecar services 包括：

### perception_service
- 接收前端事件
- 写 observation
- 触发状态更新

### memory_service
- observation / event / fact 读写与查询
- last_seen
- recent_events

### state_service
- object_state
- zone_state
- world_state 摘要

### policy_service
- freshness
- stale
- fallback_required
- reason_code

### security_guard
- 用户校验
- 设备校验
- tool / resource / media 访问控制
- 审计

### device_service
- snapshot
- recent clip
- device status
- heartbeat

### ocr_service
- quick_read
- extract_fields
- ocr_results 写入与关联

---

## 3.6 边缘层
### RK3566 单目前端
职责：
- 采集图像
- 轻量检测
- 轻量跟踪
- 事件压缩
- 最近快照 / clip 缓存
- 设备心跳
- 响应拍照与 clip 请求

不负责：
- 长期记忆
- 状态聚合
- stale/freshness
- Telegram 交互
- MCP
- 权限控制

---

## 3.7 数据层
### SQLite + FTS5
职责：
- 关系数据持久化
- observation / event / state / audit / OCR 结果存储
- OCR / event / observation 的全文检索

正式表：
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

FTS：
- observations_fts
- events_fts
- ocr_results_fts

---

## 4. 关键模块边界

## 4.1 Telegram 与 nanobot 的边界
Telegram 只提供用户入口；  
nanobot 负责会话、模型、工具和最终回复；  
两者都不应直接承载 state / policy 真相逻辑。

## 4.2 nanobot 与 MCP 的边界
nanobot 是 MCP 客户端宿主；  
MCP 提供正式能力面；  
业务能力通过 sidecar service 实现，再映射成 MCP tools / resources / prompts。

## 4.3 Qwen 与工具的边界
Qwen3.5 负责决定是否调用工具；  
工具负责执行动作与返回结构化结果；  
模型再整合这些结果。

## 4.4 前端与后端的边界
前端只负责“感知与上报”；  
后端负责“记忆、状态、时效、审计与权限”。

---

## 5. 正式数据流

## 5.1 当前查询流
用户通过 Telegram 提问  
→ nanobot 接收  
→ Qwen3.5 理解问题  
→ 选择 Skill  
→ 视情况调用 MCP tool  
→ backend services 提供事实  
→ Qwen3.5 整合结果  
→ Telegram 回复用户

## 5.2 事件上报流
RK3566 采集并检测  
→ 事件压缩  
→ perception_service 接收  
→ 写 observations  
→ 必要时升级为 events  
→ state_service 刷新状态  
→ 命中规则时主动通知用户

## 5.3 OCR 流
用户上传图片或请求读取当前画面  
→ Qwen3.5 判断直接 OCR 或调用工具 OCR  
→ ocr_service 结构化处理  
→ 写 ocr_results  
→ 必要时写 observation / event  
→ 回复用户

---

## 6. 正式能力层定义

## 6.1 MCP Tools
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

## 6.2 MCP Resources
- resource://memory/observations
- resource://memory/events
- resource://memory/object_states
- resource://memory/zone_states
- resource://policy/freshness
- resource://devices/status

## 6.3 MCP Prompts
- scene_query
- history_query
- last_seen_query
- object_state_query
- zone_state_query
- ocr_query
- device_status_query

## 6.4 Skills
- scene_query
- history_query
- last_seen
- object_state
- zone_state
- ocr_query
- device_status

---

## 7. 状态层设计

### 7.1 object_state
用于回答：
- 某物体现在大概率还在不在

字段重点：
- object_name
- state_value
- state_confidence
- observed_at
- fresh_until
- is_stale
- evidence_count
- reason_code

### 7.2 zone_state
用于回答：
- 某区域现在像不像有人 / 有物

字段重点：
- zone_id
- state_value
- state_confidence
- fresh_until
- is_stale
- reason_code

### 7.3 world_state
只作为摘要聚合视图，不做复杂图谱。

---

## 8. freshness / stale 设计

policy_service 负责：
- query_recency_class
- freshness_window
- fresh_until
- is_stale
- fallback_required
- reason_code

基本原则：
1. stale 不等于无效，但必须改变措辞。
2. 当前问题优先 fresh 结果。
3. stale 且高实时问题应优先 fallback。
4. 设备离线也可以触发 stale。

---

## 9. OCR 双通道设计

### 9.1 模型 OCR
适用：
- 简单读字
- 局部纸条、标签、门牌
- 用户上传单图的轻 OCR 问答

### 9.2 工具 OCR
适用：
- 字段提取
- 长文本
- 结构化结果
- 需要写 observation / event 的 OCR 内容

正式结论：
OCR 是正式能力，不是后续增强项。

---

## 10. 安全与治理

### 10.1 入口级控制
通过 nanobot 的 allowFrom 限制 Telegram 允许用户。

### 10.2 业务级控制
通过 security_guard 统一管理：
- user_allowlist
- device_allowlist
- tool_allowlist_per_skill
- resource_scope_per_skill
- media_visibility_scope

### 10.3 审计
以下行为必须进入 audit_logs：
- 用户访问
- 工具调用
- 权限拒绝
- 设备命令
- 媒体读取
- OCR 结构化抽取

---

## 11. 正式部署架构

### 11.1 主机侧
- nanobot
- backend API
- MCP servers
- SQLite
- media storage
- logs

### 11.2 边缘侧
- capture
- inference
- tracking
- compression
- cache
- health
- device API

### 11.3 入口侧
- Telegram Bot API
- nanobot Telegram channel

---

## 12. 非目标回顾

本架构明确不做：
- 运动控制
- ROS / ROS2
- 3D 建图
- 多机器人协同
- 高并发云平台
- 单目前端精确三维定位
- 完整 Web 管理后台

---

## 13. 最终架构结论

Vision Butler v5 的正式架构结论是：

- Telegram 是正式入口
- nanobot 是正式宿主
- Qwen3.5 是认知核心
- MCP + Skill 是标准能力层
- backend sidecar services 是业务真相层
- RK3566 是边缘事件感知层
- SQLite + FTS5 是正式数据层

该架构的核心价值在于：  
它把“会看”“会记”“会判断当前大概率状态”“会解释自己有多确定”统一到一个清晰可维护的系统中。
````

这份 `ARCHITECTURE.md` 对 Telegram / nanobot / MCP / Qwen / SQLite 的表述同样与公开文档保持一致。([core.telegram.org](https://core.telegram.org/bots/api?utm_source=chatgpt.com)) ([github.com](https://github.com/HKUDS/nanobot/blob/main/README.md?utm_source=chatgpt.com)) ([modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-03-26?utm_source=chatgpt.com)) ([modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-06-18/server/tools?utm_source=chatgpt.com)) ([help.aliyun.com](https://help.aliyun.com/zh/model-studio/qwen-function-calling?utm_source=chatgpt.com)) ([sqlite.org](https://sqlite.org/fts5.html?utm_source=chatgpt.com))

---

到这里，你的**文档侧启动包**已经基本闭环了。
你现在手里已经有：

* 项目书主内容
* 图和图注
* 数据库表说明
* `schema.sql`
* 迁移说明
* `AGENTS.md`
* `TASKS.md`
* 15 个 Codex 专用提示词
* `nanobot.config.json`
* 7 个 `SKILL.md`
* `DEPLOYMENT.md`
* 启动脚本
* `README.md`
* `ARCHITECTURE.md`

下一步最实际的动作，就是把这些文本落进仓库，然后把 **Prompt 1 → Prompt 2 → Prompt 3** 依次扔给 Codex。
