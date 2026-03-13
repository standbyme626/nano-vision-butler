下面我直接给你一版**最终版完整产品计划书**，不是商业融资稿，也不是 MVP 草案，而是按“**完整功能、完整内容、可直接作为项目总纲和研发规格书母本**”来写。先说我的总判断：

**这个项目是成立的，而且方向已经非常清晰：**
它不是单纯的“Telegram 机器人”，也不是“给 nanobot 加个摄像头”，而是一个**以 Telegram 为正式用户入口、以 nanobot 为唯一主控宿主、以你当前接入的 Qwen3.5 多模态模型为认知核心、以 MCP/Skill 为能力扩展层、以 RK3566 单目前端为边缘感知层、以后端状态/记忆/策略服务为事实层**的完整视觉管家系统。这个组合与现有外部能力边界是匹配的：Telegram Bot API 本身就是 HTTP 接口，支持 `getUpdates` 与 `setWebhook` 两种互斥更新模式，更新只保留 24 小时；nanobot 当前已经原生支持 Telegram、多实例工作区隔离和 MCP 工具挂载；Qwen 官方文档已经把视觉理解、工具调用、结构化输出列为正式能力；MCP 规范也明确把 tools、resources、prompts 作为标准暴露面。([Telegram][1])

---

# 基于 nanobot 的视觉管家系统 v5

## 最终版完整产品计划书（Telegram 正式版 / RK3566 单目前端 / Qwen3.5 多模态）

## 一、项目定义

本项目定义为：**一个通过 Telegram 进行交互的视觉管家系统**。
系统由六个正式组成部分构成：

1. **Telegram Bot**：正式用户入口，负责接收文本、图片、语音、文件与回执。
2. **nanobot Gateway**：唯一主控入口与 Agent 宿主，负责会话、模型调用、Skill 加载、MCP 接入与统一运行时。
3. **Qwen3.5 多模态模型**：负责自然语言理解、视觉理解、简单 OCR、工具选择、答案整合。
4. **MCP / Skill 层**：负责将外部能力标准化暴露给模型，并通过 Skill 约束调用顺序、时效规则与 fallback。
5. **RK3566 单目前端**：负责图像采集、轻量检测、轻量跟踪、事件压缩、短时媒体缓存与设备健康上报。
6. **后端 sidecar 服务**：负责 observation / event / state / policy / security / device 等业务事实层。

这个定义与当前外部生态是相容的：nanobot README 已明确支持 Telegram channel、独立 workspace、MCP server 挂载，并可通过本地进程或 HTTP 远程服务接入外部能力；MCP 规范也明确允许 LLM 应用通过 JSON-RPC 2.0 与外部服务交换 tools、resources、prompts。([GitHub][2])

---

## 二、项目总目标

本项目的最终目标不是做“看图聊天”，而是做一个**具备当前观察、历史回溯、当前状态推定、事件取证、简单 OCR、设备监测与权限边界**的完整视觉管家系统。系统必须支持下面这六类核心问题：

* 现在看到了什么
* 最近发生了什么
* 某个对象最后一次在哪里出现
* 某个对象现在大概率还在不在
* 某个区域现在像不像有人 / 有物
* 对当前画面、截图、标签、纸条做简单 OCR 或信息抽取

其中，“**现在大概率还在不在**”和“**当前像不像有人**”是本项目区别于普通摄像头 Bot 的关键能力；它们不能只靠视觉大模型临时判断，而必须依赖 observation → event → state → freshness 的完整链路。Qwen 官方 Function Calling 文档明确指出：正确模式是“模型决定是否调用工具，应用执行工具，再把结果回灌给模型生成最终回答”；因此状态和记忆必须在工具层和服务层中保存，不能只在模型上下文里临时存在。([help.aliyun.com][3])

---

## 三、项目边界

### 3.1 纳入范围

本计划书的正式范围包括：

* Telegram Bot 正式接入与消息处理
* nanobot 作为唯一主控入口
* Qwen3.5 多模态推理接入
* RK3566 单目前端事件感知
* snapshot / recent clip 获取
* 当前画面问答
* 最近事件查询
* last_seen 查询
* object_state / zone_state / world_state 查询
* stale / freshness 判定
* 简单 OCR 与结构化提取
* MCP tools / resources / prompts
* Skill 执行模板
* 权限控制、设备认证与审计日志
* SQLite + FTS5 数据层
* 本地媒体存储与索引
* 单机正式部署

### 3.2 明确不做

本项目明确不做：

* 运动控制
* ROS/ROS2 集成
* 3D 建图
* 多机器人协同
* 云端多租户 SaaS
* 高并发分布式平台
* 完整 web 后台
* 多摄像头空间拓扑重建
* 基于单目的精确绝对深度和三维坐标系统

最后这条尤其关键。因为你前端是**单目摄像头**，而单目视觉在绝对尺度和稳定 3D 深度上先天受限；因此本系统的“当前状态”应定义为**带时效与证据的推定状态**，而不是精确几何位置。Qwen 视觉模型文档虽然提到高精度物体识别与定位等能力，但你的系统应在产品层面主动把“几何精定位”排除在目标之外，把能力焦点放在“状态判断”和“时效判断”上。([help.aliyun.com][4])

---

## 四、总体产品定位

本系统的正式产品定位是：

> 一个通过 Telegram 与用户交互、能够理解视觉内容、调取历史证据、判断当前状态并以自然语言回报的单空间视觉管家。

它不是监控平台，也不是通用安防 NVR。
它更像是一个“**会看、会记、会回想、会说明自己把握有多大**”的空间助手。

这个定位决定了它的输出风格必须是：

* 回答“看到了什么”
* 回答“我依据什么这么说”
* 告诉用户“这条信息新不新”
* 在证据不足时主动说明“不确定”或触发拍照回查

MCP tools 规范强调 tools 是“模型可发现并自动调用的外部操作”，同时要求实现方重视安全和人工可控；你的系统正好适合这种范式：模型负责决定，工具负责执行，用户在 Telegram 中看到最终解释与证据摘要。([Model Context Protocol][5])

---

## 五、完整功能清单

### 5.1 用户可直接使用的正式功能

用户通过 Telegram 应能直接完成以下交互：

1. **当前画面询问**
   例如：

   * 现在客厅里有什么
   * 门口现在有人吗
   * 厨房桌上现在是什么情况

2. **最近事件查询**
   例如：

   * 最近 1 小时门口发生了什么
   * 今天下午有没有人来过
   * 最近有没有看到猫

3. **最后一次出现查询**
   例如：

   * 杯子最后一次在哪里出现
   * 快递最后一次是什么时候看到的

4. **当前状态推定查询**
   例如：

   * 杯子现在大概率还在桌上吗
   * 沙发区域现在像不像有人
   * 玄关区域当前像不像有快递

5. **主动取证**
   例如：

   * 现在拍一张门口
   * 发最近 10 秒视频
   * 重新确认一下桌面

6. **简单 OCR / 信息抽取**
   例如：

   * 读一下门口纸条
   * 看一下快递单写了什么
   * 把标签里的编号提取出来

7. **设备状态查询**
   例如：

   * 摄像头在线吗
   * 最近有没有掉线
   * 当前设备温度和负载怎样

8. **规则与通知**
   例如：

   * 检测到门口有人就提醒
   * 设备离线就发消息
   * 物体状态变更时通知我

这些功能全部应该作为正式功能写进计划书，不再作为“以后升级”。Telegram 官方 Bot API 已支持文本、图片、视频、语音、文档等消息类能力，并规定文本消息单条为 1–4096 字符；这意味着系统回复层必须支持**长回复分片**、**媒体附带说明**和**较长任务的过程反馈**。([Telegram][1])

---

## 六、系统总体架构

系统采用“**单一用户入口 + 单一主控入口 + 外部业务事实层 + 边缘事件感知层**”架构。

### 6.1 逻辑分层

**入口层**

* Telegram Bot

**主控层**

* nanobot gateway
* channel adapter
* session/runtime/workspace

**认知层**

* Qwen3.5 多模态模型
* intent parsing
* tool decision
* answer synthesis

**扩展层**

* MCP tools
* MCP resources
* MCP prompts
* Skills

**业务事实层**

* perception_service
* memory_service
* state_service
* policy_service
* security_guard
* device_service

**边缘层**

* RK3566 单目前端
* capture / detect / track / compress / cache / device api

**数据层**

* SQLite + FTS5
* media storage
* optional vector index

这样切分的原因很明确：MCP 规范把 Resources、Prompts、Tools 定义为服务对外暴露的三种正式能力；nanobot 现阶段则已经能把外部 MCP 服务接成“原生 agent tools”。所以业务能力不应写死在 nanobot 核心内，而应放在 sidecar 服务，经 MCP 暴露给 nanobot。([Model Context Protocol][6])

---

## 七、Telegram 正式接入方案

Telegram 在本项目中不是临时入口，而是**正式唯一用户入口**。

### 7.1 接入方式

系统首选 **polling（getUpdates）** 作为正式运行方式，同时保留 webhook 兼容能力。这样做不是因为 webhook 不重要，而是因为你当前系统目标是单机、单实例、单空间视觉管家，而 Telegram 官方明确说明 `getUpdates` 和 `setWebhook` 是两种互斥方式，且未被消费的更新最多只保留 24 小时。对于单机管家系统，polling 更容易部署、调试和恢复。([Telegram][1])

### 7.2 Telegram 层必须具备的正式能力

* 私聊问答
* 图片/视频接收
* 语音/文档接收（可选）
* 长消息分片
* sendChatAction 状态提示
* 媒体回传
* 命令式触发与自然语言触发并存
* chat_id / user_id 白名单绑定
* update offset 持久化
* 异常恢复后避免重复消费

### 7.3 Telegram 层的产品规则

* 任何需要较长处理时间的请求，都要先发 typing / upload_photo 等状态提示。Telegram 官方专门提供 `sendChatAction` 来表达“系统正在处理”，用于避免长耗时视觉任务给用户造成“无响应”的感受。([Telegram][1])
* 任意自然语言结果超过 4096 字符时，必须自动切分或转为摘要 + 附件。Telegram 对文本长度的官方限制就是 1–4096 字符。([Telegram][1])
* 任何主动通知都必须落在 allowlist 目标上，不允许广播式滥发。

---

## 八、nanobot 在系统中的正式角色

在本项目里，nanobot 的角色必须写死为：

> **唯一主控入口、唯一 Agent 宿主、唯一模型调度入口；但不是业务事实层。**

### 8.1 nanobot 负责什么

* Telegram channel 接入
* 会话管理
* Qwen3.5 模型调用
* Skill 加载
* MCP server 连接
* 工具调用编排
* 回复生成与发送
* 运行时 workspace / media / state 管理
* 多实例隔离（测试 / 正式）

nanobot 当前 README 已明确支持 Telegram 实例配置、workspace 隔离、多实例运行和 MCP server 配置；最新 release 也明确把 Telegram、MCP/tool 可靠性和多实例支持列为重点增强项。([GitHub][2])

### 8.2 nanobot 不负责什么

* observation / event / state 真相存储
* stale/freshness 决策
* device auth
* 媒体访问授权
* 业务数据库 schema
* 前端事件协议
* 视觉业务专用 dispatcher

也就是说：**nanobot 是内核，不是你的业务真相层**。

---

## 九、Qwen3.5 多模态模型的正式职责

你当前已经接入的是 **Qwen3.5 多模态本地量化模型**。在本计划书里，它的职责应定义为：

### 9.1 模型负责

* 理解用户自然语言
* 理解图片与短视频的语义
* 执行简单视觉问答
* 执行简单 OCR
* 判断是否需要调用外部工具
* 将工具输出整合成可读回答
* 使用结构化输出产出 JSON 格式结果

Qwen 官方文档把 Qwen3.5 明确定位为视觉理解模型，覆盖多模态推理、复杂文档解析、视觉 Agent 等任务；阿里云的 Function Calling 文档也说明 Qwen3.5 支持“带工具清单的多轮调用”；结构化输出文档则说明可以用 JSON Object 或 JSON Schema 强制约束模型输出。([help.aliyun.com][4])

### 9.2 模型不负责

* 充当数据库
* 充当状态真相层
* 直接保存历史世界状态
* 判定设备是否在线
* 替代 stale/freshness 规则
* 单独决定安全授权

模型在本系统中是**认知与调度层**，不是**事实层**。

---

## 十、MCP 与 Skill 的正式定位

### 10.1 MCP 的正式作用

MCP 在本项目中是**标准化能力暴露层**。
MCP 规范明确指出，Servers 可以向客户端暴露三类正式能力：

* **Resources**：上下文与数据
* **Prompts**：模板化工作流
* **Tools**：可执行函数

同时，Tools 被设计成模型可发现并自动调用的操作，使用 `tools/list` 与 `tools/call` 完成发现与执行。([Model Context Protocol][6])

### 10.2 Skill 的正式作用

Skill 在本项目中的角色不是替代工具，也不是替代 MCP，而是：

* 把某类用户问题写成标准执行模板
* 描述哪类问题触发哪些工具
* 定义 freshness 优先级
* 定义 fallback 顺序
* 定义回复风格与证据引用方式

也就是：
**MCP 提供能力，Skill 组织能力，Qwen 决定是否触发能力。**

### 10.3 本项目正式 MCP Tool 列表

以下工具应作为首发正式工具纳入：

* `take_snapshot`
* `get_recent_clip`
* `describe_scene`
* `last_seen_object`
* `get_object_state`
* `get_zone_state`
* `get_world_state`
* `query_recent_events`
* `evaluate_staleness`
* `device_status`
* `refresh_object_state`
* `refresh_zone_state`
* `ocr_quick_read`
* `ocr_extract_fields`
* `audit_recent_access`

### 10.4 本项目正式 MCP Resource 列表

* `resource://memory/observations`
* `resource://memory/events`
* `resource://memory/object_states`
* `resource://memory/zone_states`
* `resource://policy/freshness`
* `resource://security/access_scope`
* `resource://devices/status`

### 10.5 本项目正式 MCP Prompt 列表

* `scene_query`
* `history_query`
* `last_seen_query`
* `object_state_query`
* `zone_state_query`
* `ocr_query`
* `device_status_query`

---

## 十一、RK3566 单目前端正式设计

### 11.1 前端硬件定位

前端硬件是：**2G + 16G 的泰山派 RK3566，单目摄像头，Ubuntu 社区系统，已验证可运行 YOLO**。
本计划书将其正式定义为：

> **边缘事件感知终端**，不是边缘智能体，不是状态真相层。

这一定义与 RK3566 官方能力相匹配：Rockchip 官方产品页给出的 RK3566 关键特性包括四核 Cortex-A55、1TOPS NPU、8M ISP；官方 brief datasheet 还列出 16-bit Camera Interface、4-lane MIPI-CSI RX、eMMC 5.1 等接口能力。也就是说，它非常适合做前端采集与轻量视觉，但不是用来承载复杂后端认知逻辑的。([rock-chips.com][7])

### 11.2 前端正式职责

前端只负责：

* 相机采集
* 预处理与 ISP 稳定
* 轻量检测
* 轻量跟踪
* 事件压缩
* 最近快照缓存
* 最近片段缓存
* 设备状态与心跳上报
* 响应主动命令（拍照、取最近视频）

### 11.3 前端明确不负责

* 长期记忆
* 状态聚合
* stale/freshness 计算
* 权限控制
* Telegram 交互
* MCP 调度
* 大模型推理主流程
* 复杂 OCR 主服务
* world_state 生成

### 11.4 前端模型选型原则

Rockchip 的 RKNN Model Zoo 已明确支持 RK3566 平台，并列出了多种检测、分割、人脸与 OCR 模型，包括 YOLOv5、YOLOv6、YOLOv8、RetinaFace、PPOCR-Det、PPOCR-Rec 等。RKNN Toolkit2 的官方说明也明确要求：模型先在 PC 上转换成 RKNN，再在开发板上用 C API 或 Python API 执行推理。([GitHub][8])

因此，前端的正式模型策略为：

* **常驻主模型**：轻量目标检测模型 1 个
* **按需模型**：文字检测/文字识别、人脸检测、局部分割
* **不常驻**：重型图文匹配、大型分割、大 VLM

### 11.5 前端推荐模型组合

正式推荐组合为：

* 主检测：`YOLOv6n` 或 `YOLOv5n`
* 可选检测备份：`YOLOv8n`
* OCR 检测：`PPOCR-Det`
* OCR 识别：`PPOCR-Rec`
* 人脸触发：`RetinaFace_mobile320`

这不是因为它们“最先进”，而是因为 Rockchip 官方工具链对这些模型已经给出明确的 RK3566 支持路径。([GitHub][8])

---

## 十二、OCR 的最终正式方案

这部分不再模糊，直接定为**双通道 OCR**。

### 12.1 通道 A：模型原生 OCR

用于：

* 低频问答式 OCR
* 简单标签 / 纸条 / 门牌 / 屏幕字
* OCR 与视觉理解混合问题
* 用户直接发一张图并问“写了什么”

Qwen 官方视觉文档已把文字识别与信息抽取纳入多模态能力；结构化输出文档则允许你要求模型直接输出 JSON。([help.aliyun.com][4])

### 12.2 通道 B：专用 OCR Tool

用于：

* 结构化字段提取
* 长文本 OCR
* 表格/票据/文档类 OCR
* 需要保存为 observation/event 的高价值识别结果

这个通道建议正式纳入项目首发，不再留到以后。
可选实现有两条：

* **Qwen-OCR 服务**：阿里云官方文档明确把 `qwen-vl-ocr` 定义为专用于文字提取的视觉理解模型，可做文本提取与结构化解析。([help.aliyun.com][9])
* **PaddleOCR 服务**：PaddleOCR 官方项目明确支持模型库、推理与服务化部署，适合做独立 OCR 服务。([GitHub][10])

### 12.3 正式产品策略

* **默认**：简单 OCR 先由 Qwen3.5 直接处理
* **结构化/高价值**：由 `ocr_extract_fields` 工具处理
* **前端板端**：只做 OCR 候选区域检测与可选轻量识别，不承担系统主 OCR 真相层

这样做的好处是：
用户体验最好，系统也最可维护。

---

## 十三、核心业务模型：Observation / Event / State / Policy / Security

### 13.1 Observation

Observation 是原始或半结构化观察记录，字段至少包括：

* `id`
* `camera_id`
* `zone_id`
* `object_name`
* `object_class`
* `track_id`
* `observed_at`
* `confidence`
* `snapshot_uri`
* `clip_uri`
* `fresh_until`
* `source_event_id`
* `visibility_scope`

### 13.2 Event

Event 是显著变化记录，不是每条 observation 都升级为 event。
事件包括：

* 有人出现 / 消失
* 目标进入 / 离开区域
* 设备上线 / 离线
* OCR 提取到关键字段
* 物体状态变化

### 13.3 State

State 是当前推定层，分为：

* `object_state`
* `zone_state`
* `world_state`
* `presence_state`

其中：

* `object_state` 表示某对象当前大概率在/不在/未知
* `zone_state` 表示某区域当前占用/空/未知
* `world_state` 作为全局摘要视图，不应过度复杂化
* `presence_state` 用于人或生物体出现类判断

### 13.4 Policy

Policy 单独成层，负责：

* `freshness_window`
* `fresh_until`
* `is_stale`
* `recency_class`
* `fallback_required`
* `reason_code`

### 13.5 Security

Security 单独成层，负责：

* Telegram 用户 allowlist
* 设备 allowlist
* tool allowlist per skill
* resource scope per skill
* media visibility scope
* 审计日志

MCP 规范明确提醒：工具意味着外部操作和代码执行，实施方必须认真处理安全与人机确认问题。你的安全层不是附属物，而是系统主层之一。([Model Context Protocol][6])

---

## 十四、数据库与存储

### 14.1 数据库选型

正式数据层使用：

* SQLite
* FTS5
* 本地 media storage
* optional vector index

选择 SQLite 不是妥协，而是因为本项目边界就是**单机、单空间、单实例优先**。

### 14.2 正式表结构

* `observations`
* `events`
* `object_states`
* `zone_states`
* `devices`
* `media_items`
* `audit_logs`
* `facts`（仅长期稳定信息）

### 14.3 存储规则

* 板端只保留短时缓存
* 后端保留中长期媒体索引
* observation 全量写入
* event 仅显著性升级写入
* state 只能由 observation/event 聚合生成
* fact 仅写长期稳定信息

---

## 十五、后端服务设计

### 15.1 perception_service

接收前端事件流，校验设备身份，写 observation，触发状态更新。

### 15.2 memory_service

负责 observation / event / fact / state 的统一读写与查询。

### 15.3 state_service

负责生成与查询 object_state、zone_state、world_state。

### 15.4 policy_service

负责 freshness、stale、fallback 与 reason_code。

### 15.5 device_service

负责设备注册、在线状态、命令下发、设备回执。

### 15.6 security_guard

负责用户、设备、工具、资源、媒体的统一权限校验。

### 15.7 reply_builder

负责把工具结果、state 结果和模型生成结果拼成 Telegram 回复，并附带简明证据与 freshness 提示。

---

## 十六、正式 API 与内部契约

### 16.1 正式对外查询接口

* `/memory/recent-events`
* `/memory/last-seen`
* `/memory/object-state`
* `/memory/zone-state`
* `/memory/world-state`
* `/policy/evaluate-staleness`
* `/device/status`

### 16.2 正式内部接口

* `/device/command/take-snapshot`
* `/device/command/get-recent-clip`
* `/device/ingest/event`
* `/device/heartbeat`
* `/ocr/quick-read`
* `/ocr/extract-fields`

### 16.3 正式返回规范

所有查询结果必须带：

* `summary`
* `source_layer`
* `state_confidence`
* `fresh_until`
* `is_stale`
* `fallback_required`
* `evidence_count`

这样 Telegram 端才能给出“**我为什么这么说**”。

---

## 十七、正式 Skill 设计

每个 Skill 必须具备下面字段：

* `name`
* `description`
* `trigger_patterns`
* `allowed_tools`
* `allowed_resources`
* `auth_policy`
* `freshness_policy`
* `memory_write_policy`
* `state_effects`
* `fallback_rules`
* `steps`
* `output_schema`

正式 Skill 至少包括：

* `scene_query_skill`
* `history_query_skill`
* `last_seen_skill`
* `object_state_skill`
* `zone_state_skill`
* `ocr_skill`
* `device_status_skill`

---

## 十八、配置与部署设计

### 18.1 nanobot 正式配置

* 独立 `config.json`
* Telegram channel enabled
* token 配置
* `allowFrom`
* model provider / model name
* `tools.mcpServers`
* workspace 路径
* gateway 端口

nanobot README 已明确说明：
Telegram 可作为独立实例运行；workspace、cron、media/runtime state 都可从配置目录衍生；MCP servers 可通过 `command+args` 或 `url+headers` 两种方式接入。([GitHub][2])

### 18.2 前端部署

* Ubuntu 社区系统
* camera bring-up
* RKNN runtime
* detector service
* tracker / compressor
* local ring buffer
* heartbeat daemon

### 18.3 后端部署

* nanobot gateway
* sidecar services
* SQLite
* media directory
* logs / audit
* optional OCR service

---

## 十九、测试与验收

### 19.1 单元测试

* `test_state_service`
* `test_policy_service`
* `test_security_guard`
* `test_memory_tiering`
* `test_perception_service`
* `test_ocr_routing`

### 19.2 集成测试

* `test_device_event_flow`
* `test_object_state_flow`
* `test_zone_state_flow`
* `test_stale_fallback_flow`
* `test_access_control_flow`
* `test_telegram_message_flow`

### 19.3 e2e 测试

* Telegram 发问 → 返回当前观察
* Telegram 发问 → 返回 last_seen
* Telegram 发问 → 返回 stale 状态与 fallback
* Telegram 发图 → 返回 OCR 结果
* Telegram 请求拍照 → 返回最新图片
* 设备离线 → 状态标记 stale → Telegram 告警

### 19.4 正式验收标准

系统只有同时满足以下条件才算完成：

* Telegram 作为正式入口可稳定工作
* nanobot + MCP + Skill 调度链路打通
* RK3566 前端稳定上报事件
* object_state / zone_state / world_state 可查询
* stale / freshness / fallback 正确生效
* 简单 OCR 能跑，结构化 OCR 工具可调用
* 权限模型有效
* 设备离线能被识别和告警
* 所有关键路径有测试覆盖

---

## 二十、最终分析与结论

我对这版最终方案的评价是：

**这已经不是一个“想法”，而是一套可以直接组织开发的完整项目方案。**

它最强的地方有四个。

第一，**入口统一**。
Telegram 是正式入口，不再漂移；Telegram 官方接口限制和 nanobot 当前 Telegram 支持都足以支撑这一设计。([Telegram][1])

第二，**主控统一**。
nanobot 被清楚地定义成唯一主控入口和 Agent 宿主；它现有的 MCP、workspace、多实例能力足够承担这个角色。([GitHub][2])

第三，**模型职责明确**。
Qwen3.5 负责理解和调度，而不是替代数据库、状态机和安全系统。这个边界和官方 Function Calling/结构化输出机制完全一致。([help.aliyun.com][3])

第四，**前端边界正确**。
RK3566 单目 2G+16G 被定义成“事件感知终端”，而不是“前端智能体”；这个决定会让整个系统长期可维护。Rockchip 官方资料显示 RK3566 具备 1TOPS NPU、8M ISP、MIPI-CSI 接入与 RKNN 部署路径，足以支撑轻量检测、OCR 候选检测和事件压缩，但不适合承担系统事实层。([rock-chips.com][7])

**我建议你把这版作为“最终母版项目书”使用。**
它已经可以直接往下派生成：架构说明、开发规格书、接口文档、测试计划、AGENTS.md、Skill 定义和 MCP 工具清单。

下一步最合理的动作，就是把这版继续收敛成你要的正式文档格式：
**“最终版产品计划书 v1.0”**，按章节号、条款、接口清单、模块职责、测试矩阵整理成可直接发团队执行的版本。

[1]: https://core.telegram.org/bots/api "Telegram Bot API"
[2]: https://github.com/HKUDS/nanobot/blob/main/README.md "nanobot/README.md at main · HKUDS/nanobot · GitHub"
[3]: https://help.aliyun.com/zh/model-studio/qwen-function-calling "如何通过Function Calling 实现工具调用-大模型服务平台百炼(Model Studio)-阿里云帮助中心"
[4]: https://help.aliyun.com/zh/model-studio/vision "如何使用Qwen3.5模型实现视觉理解（图像与视频理解）-大模型服务平台百炼(Model Studio)-阿里云帮助中心"
[5]: https://modelcontextprotocol.io/specification/2025-06-18/server/tools "Tools - Model Context Protocol"
[6]: https://modelcontextprotocol.io/specification/2025-03-26 "Specification - Model Context Protocol"
[7]: https://www.rock-chips.com/a/en/products/RK35_Series/2021/0113/1274.html "Rockchip-瑞芯微电子股份有限公司"
[8]: https://github.com/airockchip/rknn_model_zoo/blob/main/README_CN.md "rknn_model_zoo/README_CN.md at main · airockchip/rknn_model_zoo · GitHub"
[9]: https://help.aliyun.com/zh/model-studio/qwen-vl-ocr "文字识别模型qwen-vl-ocr如何使用-大模型服务平台百炼(Model Studio)-阿里云帮助中心"
[10]: https://github.com/PaddlePaddle/PaddleOCR "GitHub - PaddlePaddle/PaddleOCR: Turn any PDF or image document into structured data for your AI. A powerful, lightweight OCR toolkit that bridges the gap between images/PDFs and LLMs. Supports 100+ languages. · GitHub"






好，下面我直接**继续上文**，把这份最终版产品计划书补到“可直接开工执行”的程度。以下内容建议作为原项目书的**第二部分 / 下半部**接续使用。

---

## 二十一、目录结构与仓库组织

本项目建议采用“**主控仓 + 前端仓 + 配置仓**”三层组织，但如果你希望先用单仓推进，也可以先在一个仓库中按模块拆目录。核心原则不变：**nanobot 保持上游兼容，业务逻辑通过 MCP/Skill/sidecar 外挂**。nanobot 当前已经原生支持通过配置挂载 Telegram 与 MCP server，因此项目不应通过深改 nanobot 内核来组织业务。([GitHub][1])

建议最终目录结构如下：

```text
vision_butler/
├─ AGENTS.md
├─ README.md
├─ docs/
│  ├─ PRODUCT_PLAN.md
│  ├─ ARCHITECTURE.md
│  ├─ DEPLOYMENT.md
│  ├─ TELEGRAM_FLOW.md
│  ├─ MCP_TOOLS.md
│  ├─ SKILL_DESIGN.md
│  ├─ STATE_MODEL.md
│  ├─ FRESHNESS_POLICY.md
│  ├─ SECURITY_MODEL.md
│  ├─ OCR_STRATEGY.md
│  └─ TEST_PLAN.md
├─ config/
│  ├─ nanobot.config.json
│  ├─ settings.yaml
│  ├─ policies.yaml
│  ├─ access.yaml
│  ├─ devices.yaml
│  ├─ cameras.yaml
│  └─ aliases.yaml
├─ gateway/
│  └─ nanobot_workspace/
├─ edge_device/
│  ├─ capture/
│  ├─ inference/
│  ├─ tracking/
│  ├─ compression/
│  ├─ cache/
│  ├─ health/
│  └─ api/
├─ src/
│  ├─ app.py
│  ├─ dependencies.py
│  ├─ routes_memory.py
│  ├─ routes_state.py
│  ├─ routes_policy.py
│  ├─ routes_device.py
│  ├─ routes_ocr.py
│  ├─ services/
│  │  ├─ perception_service.py
│  │  ├─ memory_service.py
│  │  ├─ state_service.py
│  │  ├─ policy_service.py
│  │  ├─ device_service.py
│  │  ├─ ocr_service.py
│  │  └─ reply_service.py
│  ├─ security/
│  │  ├─ security_guard.py
│  │  └─ access_policy.py
│  ├─ schemas/
│  │  ├─ memory.py
│  │  ├─ state.py
│  │  ├─ policy.py
│  │  ├─ security.py
│  │  ├─ device.py
│  │  └─ telegram.py
│  ├─ db/
│  │  ├─ session.py
│  │  ├─ migrations/
│  │  └─ repositories/
│  │     ├─ observation_repo.py
│  │     ├─ event_repo.py
│  │     ├─ state_repo.py
│  │     ├─ device_repo.py
│  │     ├─ media_repo.py
│  │     └─ audit_repo.py
│  └─ mcp_server/
│     ├─ tools/
│     ├─ resources/
│     └─ prompts/
├─ skills/
│  ├─ scene_query/
│  │  └─ SKILL.md
│  ├─ history_query/
│  │  └─ SKILL.md
│  ├─ last_seen/
│  │  └─ SKILL.md
│  ├─ object_state/
│  │  └─ SKILL.md
│  ├─ zone_state/
│  │  └─ SKILL.md
│  ├─ ocr_query/
│  │  └─ SKILL.md
│  └─ device_status/
│     └─ SKILL.md
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ e2e/
└─ scripts/
   ├─ start_gateway.sh
   ├─ start_backend.sh
   ├─ start_edge.sh
   ├─ init_db.sh
   └─ smoke_test.sh
```

---

## 二十二、Telegram 用户交互设计

Telegram 是本项目的正式入口，因此交互设计不能只停留在“能收发消息”，而要有**明确的产品交互语义**。Telegram Bot API 是 HTTP 接口；更新处理可用 `getUpdates` 或 `setWebhook`；同时官方支持 `sendChatAction`、图片、视频、文档、语音等多种消息类型。([Telegram][2])

### 22.1 交互类型

正式支持 4 类用户输入：

1. **自然语言文本**
2. **图片上传**
3. **短视频上传**
4. **命令式指令**

### 22.2 文本交互规范

自然语言文本是第一入口，示例包括：

* 现在门口是什么情况
* 杯子最后一次在哪看到
* 客厅现在像不像有人
* 读一下这张图上的字
* 给我发最近 10 秒门口画面

Telegram 文本单条上限为 4096 字符，所以系统必须内建：

* 自动分片回复
* 摘要优先
* 大段 debug 信息折叠或转附件
* 大结果优先回摘要，再补细节

这些是正式产品要求，不是工程补丁。([Telegram][2])

### 22.3 命令式交互规范

为方便稳定操作，系统同时提供固定命令入口：

* `/snapshot door`
* `/clip living_room 10`
* `/lastseen cup`
* `/state desk`
* `/ocr`
* `/device`
* `/help`

命令的作用不是替代自然语言，而是给调试、验收和低歧义操作提供快速入口。

### 22.4 处理过程反馈

任何超过 2 秒的请求，都必须发送 `sendChatAction` 类型反馈，例如：

* `typing`
* `upload_photo`
* `record_video`

Telegram 官方提供该接口就是为了表达“机器人正在处理”；视觉任务和工具调用天然可能比纯文本回复更慢，所以这是正式交互规范的一部分。([Telegram][2])

---

## 二十三、完整消息流设计

### 23.1 用户查询当前状态

标准链路：

1. 用户在 Telegram 发出自然语言问题
2. nanobot 接收消息
3. Qwen3.5 解析意图
4. Skill 选择执行模板
5. 若需事实查询，则调用 MCP tool
6. tool 访问 state / memory / policy 服务
7. 返回结构化结果
8. Qwen3.5 整合结果生成自然语言回答
9. nanobot 将回答发回 Telegram

这条链路完全符合 Qwen Function Calling 的官方模式：应用先传工具清单，模型判断是否需要工具；若需要则返回 JSON 工具调用指令；应用执行工具，再把结果追加到 messages 中，由模型生成最终自然语言结果。([阿里云帮助中心][3])

### 23.2 用户请求拍照或视频

1. 用户发出“现在拍一张门口”
2. 模型选择 `take_snapshot`
3. MCP tool 转发到 device_service
4. device_service 向 RK3566 下发命令
5. 前端返回 snapshot URI
6. nanobot 回传图片到 Telegram
7. 若用户继续追问“图里写了什么”，则模型可直接看图，或触发 OCR tool

### 23.3 前端事件主动上报

1. RK3566 发现目标进入区域
2. event_compressor 生成事件
3. perception_service 接收并验签
4. 写入 observation
5. 判断是否升级为 event
6. state_service 刷新 object_state / zone_state
7. 若命中通知规则，则经 nanobot 主动发 Telegram 提醒

### 23.4 OCR 查询流

1. 用户上传图片或要求读取已拍照片
2. Qwen3.5 先判断是否可直接完成简单 OCR
3. 若是结构化提取或高价值内容，则调用 `ocr_extract_fields`
4. OCR 服务返回文本、框、置信度和字段
5. 若结果需记忆化，则写入 observation/event
6. 最终由 Qwen3.5 生成用户可读回复

---

## 二十四、Skill 运行策略

Skill 不承担底层事实存储，而承担“**如何解决某类问题**”的标准流程。Qwen 的工具调用机制说明了工具调用是一个多轮应用交互过程，因此 Skill 最适合承载“哪个问题先查哪个工具、何时回退、何时直接回答”的策略。([阿里云帮助中心][3])

### 24.1 scene_query_skill

适用问题：

* 现在看到什么
* 这张图里有什么
* 门口现在什么情况

默认步骤：

1. 若用户上传图片，则优先模型直接看图
2. 若无图片且请求实时画面，则 `take_snapshot`
3. 若已有最新 snapshot，可直接 `describe_scene`
4. 输出当前观察摘要
5. 若用户追问文字内容，再触发 OCR 分支

### 24.2 history_query_skill

适用问题：

* 最近发生了什么
* 今天下午有没有人来过

默认步骤：

1. 解析时间范围
2. 调 `query_recent_events`
3. 需要时补 `get_zone_state` 作为当前摘要
4. 输出时间序列概览

### 24.3 last_seen_skill

适用问题：

* 某物最后在哪看到
* 最后一次看到快递是什么时候

默认步骤：

1. 调 `last_seen_object`
2. 若记录 stale，则补 `evaluate_staleness`
3. 若问题本身要求实时，则建议拍照回查

### 24.4 object_state_skill

适用问题：

* 杯子现在还在吗
* 快递现在还在门口吗

默认步骤：

1. `get_object_state`
2. `evaluate_staleness`
3. 若 stale 且问题要求高实时性，则 `take_snapshot`
4. 返回“当前推定 + 证据时效 + 可信度”

### 24.5 ocr_query_skill

适用问题：

* 读图中文字
* 提取编号 / 名称 / 标签

默认步骤：

1. 简单短文本优先模型直接 OCR
2. 字段提取优先 `ocr_extract_fields`
3. 如需入库则写 observation/event
4. 返回文本和结构化结果摘要

---

## 二十五、MCP Server 设计细则

MCP 的正式意义，是给 nanobot 和模型一个**稳定、可发现、可治理**的能力边界。MCP 规范明确把 Tools 设计为模型可自动发现并调用的外部操作，把 Prompts 设计为可复用模板，把 Resources 设计为上下文资源。([Model Context Protocol][4])

### 25.1 MCP Server 划分

建议至少分成 4 类 server：

1. **vision-mcp**

   * `take_snapshot`
   * `get_recent_clip`
   * `describe_scene`

2. **memory-mcp**

   * `query_recent_events`
   * `last_seen_object`

3. **state-policy-mcp**

   * `get_object_state`
   * `get_zone_state`
   * `get_world_state`
   * `evaluate_staleness`

4. **ocr-device-mcp**

   * `ocr_quick_read`
   * `ocr_extract_fields`
   * `device_status`
   * `refresh_object_state`

### 25.2 MCP 返回规范

所有 tool 返回统一 JSON 结构：

```json
{
  "ok": true,
  "summary": "string",
  "data": {},
  "meta": {
    "source_layer": "observation|event|state|policy|device|ocr",
    "confidence": 0.0,
    "fresh_until": "2026-03-13T10:00:00Z",
    "is_stale": false,
    "fallback_required": false,
    "trace_id": "..."
  }
}
```

这样做的原因是：模型整合工具结果时，最需要的是**稳定 schema**，而不是每个工具各说各话。

### 25.3 MCP 安全规则

Tools 应在实现层加入：

* 参数白名单
* 路径白名单
* 最大媒体尺寸
* 最大 clip 时长
* 超时控制
* trace_id 与审计日志

MCP tools 规范对安全的要求很明确：工具调用不应被当作无风险文本生成，系统应该保留人工与宿主的治理能力。([Model Context Protocol][5])

---

## 二十六、nanobot 配置策略

nanobot 当前 README 已给出 Telegram 接入的核心配置模式，包括：

* `channels.telegram.enabled`
* `token`
* `allowFrom`
* `tools.mcpServers`
* workspace 与运行时目录组织

README 还明确指出 Telegram 推荐只需 token 即可快速接入，同时可通过 `allowFrom` 限制允许访问的 Telegram 用户 ID。([GitHub][1])

建议正式配置策略如下：

### 26.1 正式实例

* `nanobot-prod`
* 连接正式 Telegram Bot
* 指向正式 workspace
* 挂正式 MCP servers
* allowFrom 只允许正式用户 ID

### 26.2 测试实例

* `nanobot-dev`
* 连接测试 Telegram Bot
* 指向测试 workspace
* 挂测试 MCP servers
* allowFrom 只允许开发者 ID

### 26.3 配置原则

* 不把业务逻辑写入 nanobot fork
* 不改 nanobot 核心 channel 代码
* 所有业务扩展优先经 MCP 暴露
* Skill 与配置分离
* 正式与测试实例彻底隔离

---

## 二十七、前端设备协议

虽然 Telegram 和 nanobot 是用户侧重点，但前端设备协议必须在项目书里钉死，否则后续无法稳定验收。

### 27.1 设备上报事件 envelope

建议正式协议字段：

* `event_id`
* `schema_version`
* `device_id`
* `camera_id`
* `seq_no`
* `captured_at`
* `sent_at`
* `event_type`
* `zone_id`
* `objects[]`
* `snapshot_uri`
* `clip_uri`
* `model_version`
* `compress_reason`
* `signature`

### 27.2 设备健康上报字段

* `device_id`
* `online`
* `temperature`
* `cpu_load`
* `npu_load`
* `free_mem_mb`
* `camera_fps`
* `last_capture_ok`
* `last_upload_ok`

### 27.3 设备命令集

* `take_snapshot`
* `get_recent_clip`
* `ping`
* `refresh_detection_once`

这组命令已经足够支撑完整产品体验，不需要在首版就引入复杂双向控制。

---

## 二十八、状态模型与推理原则

### 28.1 object_state

用于回答“物体现在大概率还在不在”。

字段建议：

* `object_name`
* `camera_id`
* `zone_id`
* `state_value`：`present | absent | unknown`
* `state_confidence`
* `observed_at`
* `fresh_until`
* `is_stale`
* `summary`
* `evidence_count`
* `last_confirmed_at`
* `last_changed_at`

### 28.2 zone_state

用于回答“区域当前像不像有人/有物”。

字段建议：

* `zone_id`
* `camera_id`
* `state_value`：`occupied | empty | likely_occupied | unknown`
* `state_confidence`
* `observed_at`
* `fresh_until`
* `is_stale`
* `summary`

### 28.3 world_state

在本项目里只作为**聚合摘要视图**，不做重图谱化。
它由 object_state、zone_state、device_status 汇总得到，用于回答：

* 整体空间当前情况如何
* 哪些信息已过时
* 哪些区域值得回查

### 28.4 freshness 判定原则

* 每类对象 / 区域有独立 freshness window
* `now > fresh_until` 则 stale
* 设备离线超过阈值可直接触发 stale
* stale 不等于无效，但必须改变回复措辞
* 高实时问题触发 fallback

---

## 二十九、OCR 策略正式版

这一版不再把 OCR 作为后续增强，而是作为正式能力写入。

### 29.1 模型 OCR

Qwen 官方视觉文档明确写到“文字识别与信息抽取”和“结构化输出”能力，因此**简单 OCR、短文本读取、图中局部文字理解**可直接交给 Qwen3.5 多模态模型。([阿里云帮助中心][3])

适用：

* 纸条
* 门牌
* 简单标签
* 局部屏幕文本
* 用户上传的单张图像问答

### 29.2 工具 OCR

对于以下情况必须优先用工具：

* 长文本
* 多字段抽取
* 票据/快递单类结构化内容
* 需要保存为 observation/event 的关键信息

如果你后续决定用专门 OCR 服务，这条通道可接 PaddleOCR 或其他 OCR 服务，但对计划书来说，正式要求是：**系统必须同时具备“模型 OCR”和“工具 OCR”两条通道**。这一点不会影响 nanobot 的上游兼容性，因为它仍然只是通过 MCP 调工具。([GitHub][1])

---

## 三十、测试与验收扩展版

### 30.1 Telegram 验收

必须验证：

* polling 正常收消息
* 大文本自动分片
* 图片可上传并被模型处理
* 视频可回传
* `sendChatAction` 在长任务中正常显示
* 未授权用户被拒绝

Telegram 的接口能力和消息限制都已在官方文档中定义清楚，所以这部分必须做成正式验收项，而不是“体验优化”。([Telegram][2])

### 30.2 nanobot 验收

必须验证：

* Telegram channel 能稳定接入
* `allowFrom` 生效
* `tools.mcpServers` 可正确挂载
* Skill 能参与运行
* 正式实例与测试实例互不污染

### 30.3 工具链验收

必须验证：

* MCP tools 可被发现
* MCP tools 可被调用
* 工具失败时模型能给出失败说明
* 工具返回结果可被模型整合
* trace_id 可全链路追踪

### 30.4 前端验收

必须验证：

* 设备在线离线识别
* 事件上报可落 observation
* `take_snapshot` 成功率
* `get_recent_clip` 成功率
* 状态刷新正确
* OCR 候选图可正常传回后端

### 30.5 状态层验收

必须验证：

* last_seen 优先查 state，再回退 observation
* stale 正确触发
* zone_state 可输出占用/空/未知
* object_state 可输出 present/absent/unknown
* 高实时问题可触发 fallback

---

## 三十一、研发顺序与交付节奏

虽然这是完整产品计划书，但工程上仍然需要正确顺序。正确顺序不是“哪个模块看起来重要先写哪个”，而是：

### 阶段 1：入口打通

* Telegram Bot
* nanobot 接入
* Qwen3.5 模型联通
* 基础 Skill
* 基础 MCP

### 阶段 2：前端感知打通

* RK3566 采集
* detection / tracking / event
* heartbeat
* snapshot / clip

### 阶段 3：事实层打通

* observation
* events
* state
* policy
* device

### 阶段 4：OCR 与完整交互

* 模型 OCR
* 工具 OCR
* Telegram 多轮问答
* structured output
* 审计与权限

### 阶段 5：完整验收

* e2e
* 回归
* 稳定性
* 正式部署文档
* AGENTS.md 与开发命令

这不是把 Telegram、OCR、MCP 往后拖，而是**按依赖顺序实现完整功能**。

---

## 三十二、最终补充结论

到这里，这份“最终版完整产品计划书”已经可以被视为一个**可以直接拆解为研发任务、接口文档、测试计划和交付标准**的总纲。

它现在的核心特征非常明确：

* **Telegram 是正式入口，不是临时入口**。官方 Bot API 足以支撑文本、媒体、长任务反馈和更新处理。([Telegram][2])
* **nanobot 是正式宿主，不是可随意改造的业务底座**。它适合承载 Telegram、MCP、Skill 和模型运行，而不适合承载你的业务真相层。([GitHub][1])
* **Qwen3.5 多模态模型负责理解、简单 OCR 和工具决策，不替代状态/记忆/策略系统**。这与官方 Function Calling 与视觉能力说明一致。([阿里云帮助中心][3])
* **RK3566 单目前端是正式边缘感知层，但职责必须被限制在检测、跟踪、事件、缓存和设备状态范围内**。([GitHub][1])
* **MCP/Skill 是完整产品的一部分，不是附加功能**。MCP 提供标准能力面，Skill 提供执行模板，二者共同保证系统可扩展又不侵入 nanobot 核心。([Model Context Protocol][4])

接下来最合适的动作，就是我把以上上下两部分**整理成一份完全成型的正式文档版**，用统一章节编号、正式措辞、可复制到 Markdown 文件里的格式一次性输出。

[1]: https://github.com/HKUDS/nanobot/blob/main/README.md?utm_source=chatgpt.com "nanobot/README.md at main · HKUDS/nanobot · GitHub"
[2]: https://core.telegram.org/bots/api?utm_source=chatgpt.com "Telegram Bot API"
[3]: https://help.aliyun.com/zh/model-studio/qwen-function-calling?utm_source=chatgpt.com "如何通过Function Calling 实现工具调用-大模型服务平台百炼 ..."
[4]: https://modelcontextprotocol.io/specification/2025-03-26?utm_source=chatgpt.com "Specification - Model Context Protocol"
[5]: https://modelcontextprotocol.io/specification/2025-06-18/server/tools?utm_source=chatgpt.com "Tools - Model Context Protocol"

下面是我给你**单独补充的一整套图源**。我没有把它们并进正文，全部都放在普通 `text` 代码块里，你可以直接复制到自己的文档里再按需拆分。
我按 Mermaid 官方常见图类型来组织：`flowchart`、`sequenceDiagram`、`erDiagram`、`stateDiagram-v2`、`classDiagram`；同时图里的 Telegram、nanobot、MCP 命名也和我们前面讨论的正式方案保持一致：Telegram 作为入口，nanobot 作为宿主，MCP 负责 tools/resources/prompts，MCP tools 由模型可发现并调用。([mermaid.js.org][1])

---

## 1）系统总体架构图

```text
flowchart TB
    U[用户]
    TG[Telegram Bot]
    NB[nanobot Gateway]
    QW[Qwen3.5 多模态模型]
    SK[Skill Layer]
    MCP[MCP Client]

    subgraph MCP_SERVERS[MCP Servers]
        VT[vision-mcp]
        MT[memory-mcp]
        ST[state-policy-mcp]
        OT[ocr-device-mcp]
    end

    subgraph BACKEND[Backend Sidecar Services]
        PS[perception_service]
        MS[memory_service]
        SS[state_service]
        POL[policy_service]
        SEC[security_guard]
        DS[device_service]
        OCR[ocr_service]
    end

    subgraph DATA[Data Layer]
        DB[(SQLite + FTS5)]
        MEDIA[(Media Storage)]
        AUDIT[(Audit Logs)]
    end

    subgraph EDGE[Edge Device RK3566]
        CAP[capture]
        DET[inference / detection]
        TRK[tracking]
        CMP[event_compressor]
        CAC[ring buffer cache]
        API[device api]
    end

    U --> TG --> NB
    NB --> QW
    NB --> SK
    NB --> MCP

    MCP --> VT
    MCP --> MT
    MCP --> ST
    MCP --> OT

    VT --> PS
    MT --> MS
    ST --> SS
    ST --> POL
    ST --> SEC
    OT --> OCR
    OT --> DS

    PS --> DB
    MS --> DB
    SS --> DB
    POL --> DB
    SEC --> AUDIT
    OCR --> DB
    OCR --> MEDIA
    DS --> DB

    API --> CAP --> DET --> TRK --> CMP --> PS
    DET --> CAC
    CAP --> CAC
    DS --> API
```

---

## 2）正式部署拓扑图

```text
flowchart LR
    USER[用户手机 / Telegram App]
    TGAPI[Telegram Bot API]
    HOST[x86 主机]
    EDGE[RK3566 单目前端]
    CAM[单目摄像头]

    subgraph HOST_RUN[主机运行容器 / 进程]
        NB[nanobot]
        MCPS[MCP Servers]
        APP[FastAPI Backend]
        DB[(SQLite)]
        MEDIA[(Media Directory)]
        LOG[(Audit / Logs)]
    end

    USER <--> TGAPI
    TGAPI <--> NB

    NB <--> MCPS
    MCPS <--> APP
    APP <--> DB
    APP <--> MEDIA
    APP <--> LOG

    APP <--> EDGE
    EDGE <--> CAM
```

---

## 3）nanobot 运行时组件图

```text
flowchart TB
    CFG[config.json]
    CH[Telegram Channel]
    RT[runtime/workspace]
    MODEL[Qwen3.5 Provider]
    SKILLS[Skills]
    MCPCLI[MCP Client]
    REPLY[Reply Builder]
    SESSION[Session State]

    CFG --> CH
    CFG --> MODEL
    CFG --> SKILLS
    CFG --> MCPCLI
    CFG --> RT

    CH --> SESSION
    SESSION --> MODEL
    SESSION --> SKILLS
    SKILLS --> MCPCLI
    MCPCLI --> REPLY
    MODEL --> REPLY
    REPLY --> CH
```

---

## 4）完整产品能力地图

```text
flowchart TB
    ROOT[视觉管家系统 v5]

    ROOT --> A[当前观察]
    ROOT --> B[历史事件]
    ROOT --> C[last_seen]
    ROOT --> D[object_state]
    ROOT --> E[zone_state]
    ROOT --> F[world_state]
    ROOT --> G[主动取证]
    ROOT --> H[简单 OCR]
    ROOT --> I[结构化 OCR]
    ROOT --> J[设备状态]
    ROOT --> K[主动通知]
    ROOT --> L[安全与审计]

    G --> G1[take_snapshot]
    G --> G2[get_recent_clip]

    H --> H1[模型直接 OCR]
    I --> I1[ocr_extract_fields]

    J --> J1[device_status]
    J --> J2[heartbeat]
    J --> J3[online/offline]

    K --> K1[有人出现]
    K --> K2[状态变化]
    K --> K3[设备离线]
```

---

## 5）Telegram 用户查询主流程图

```text
flowchart TB
    A[Telegram 用户发消息]
    B[nanobot 接收 update]
    C[基础权限检查]
    D[Qwen3.5 解析意图]
    E[选择 Skill]
    F{是否需要工具}
    G[直接生成回答]
    H[调用 MCP Tool]
    I[后端服务执行]
    J[返回结构化结果]
    K[Qwen3.5 整合结果]
    L[Reply Builder]
    M[Telegram 回消息]

    A --> B --> C --> D --> E --> F
    F -- 否 --> G --> L --> M
    F -- 是 --> H --> I --> J --> K --> L --> M
```

---

## 6）当前观察查询时序图

```text
sequenceDiagram
    participant User as 用户
    participant TG as Telegram
    participant NB as nanobot
    participant QW as Qwen3.5
    participant SK as scene_query_skill
    participant MCP as vision-mcp
    participant DEV as device_service
    participant EDGE as RK3566

    User->>TG: 现在门口什么情况
    TG->>NB: message update
    NB->>QW: 解析问题
    QW->>SK: 匹配 scene_query_skill
    SK->>MCP: take_snapshot(camera=door)
    MCP->>DEV: 下发拍照命令
    DEV->>EDGE: take_snapshot
    EDGE-->>DEV: snapshot_uri
    DEV-->>MCP: snapshot_uri
    MCP-->>SK: snapshot_uri
    SK->>QW: 图像 + 任务说明
    QW-->>NB: 当前画面描述
    NB-->>TG: 文本/图片回复
    TG-->>User: 最终结果
```

---

## 7）历史事件查询时序图

```text
sequenceDiagram
    participant User as 用户
    participant TG as Telegram
    participant NB as nanobot
    participant QW as Qwen3.5
    participant SK as history_query_skill
    participant MCP as memory-mcp
    participant MEM as memory_service
    participant DB as SQLite

    User->>TG: 最近 1 小时门口发生了什么
    TG->>NB: update
    NB->>QW: 解析时间范围与对象
    QW->>SK: 选择 history_query_skill
    SK->>MCP: query_recent_events(zone=door, range=1h)
    MCP->>MEM: query_recent_events
    MEM->>DB: SELECT events / observations
    DB-->>MEM: rows
    MEM-->>MCP: structured history
    MCP-->>SK: history result
    SK->>QW: 生成摘要
    QW-->>NB: 自然语言总结
    NB-->>TG: 回复
    TG-->>User: 结果
```

---

## 8）last_seen / object_state 查询时序图

```text
sequenceDiagram
    participant User as 用户
    participant TG as Telegram
    participant NB as nanobot
    participant QW as Qwen3.5
    participant SK as object_state_skill
    participant MCP as state-policy-mcp
    participant ST as state_service
    participant POL as policy_service
    participant DB as SQLite

    User->>TG: 杯子现在大概率还在桌上吗
    TG->>NB: update
    NB->>QW: 理解问题
    QW->>SK: object_state_skill
    SK->>MCP: get_object_state(object=cup, zone=desk)
    MCP->>ST: get_object_state
    ST->>DB: SELECT object_states
    DB-->>ST: object_state row
    ST-->>MCP: state result
    SK->>MCP: evaluate_staleness(state=result)
    MCP->>POL: evaluate_staleness
    POL-->>MCP: stale / fallback decision
    MCP-->>SK: state + policy meta
    SK->>QW: 生成带时效说明的答案
    QW-->>NB: 最终回答
    NB-->>TG: 回复
    TG-->>User: 结果
```

---

## 9）OCR 查询时序图（双通道）

```text
sequenceDiagram
    participant User as 用户
    participant TG as Telegram
    participant NB as nanobot
    participant QW as Qwen3.5
    participant SK as ocr_query_skill
    participant MCP as ocr-device-mcp
    participant OCR as ocr_service

    User->>TG: 读一下这张图上的字
    TG->>NB: image + text
    NB->>QW: 图像理解 + OCR判断
    QW->>SK: ocr_query_skill

    alt 简单 OCR 直接可读
        SK->>QW: 直接 OCR / 结构化输出
        QW-->>NB: OCR 文本结果
    else 需要字段提取 / 长文本
        SK->>MCP: ocr_extract_fields
        MCP->>OCR: structured OCR
        OCR-->>MCP: text + boxes + fields
        MCP-->>SK: OCR structured result
        SK->>QW: 结果整合
        QW-->>NB: 最终可读回复
    end

    NB-->>TG: 回复
    TG-->>User: 结果
```

---

## 10）主动通知流程图

```text
flowchart TB
    A[RK3566 检测到事件]
    B[event_compressor 生成事件]
    C[perception_service 接收]
    D[写 observation]
    E[是否升级为 event]
    F[刷新 state]
    G[匹配通知规则]
    H{是否命中规则}
    I[写 audit log]
    J[nanobot 发送 Telegram 通知]
    K[结束]

    A --> B --> C --> D --> E
    E --> F --> G --> H
    H -- 否 --> I --> K
    H -- 是 --> I --> J --> K
```

---

## 11）前端事件上报流程图

```text
flowchart LR
    CAM[Camera]
    CAP[capture]
    PRE[preprocess / ISP]
    DET[detection]
    TRK[tracking]
    CMP[event_compressor]
    BUF[ring buffer cache]
    API[device api]
    BE[perception_service]

    CAM --> CAP --> PRE --> DET --> TRK --> CMP --> API --> BE
    CAP --> BUF
    DET --> BUF
    TRK --> BUF
```

---

## 12）状态刷新流程图

```text
flowchart TB
    A[收到新的 observation / event]
    B[识别对象 / 区域]
    C[读取最近证据]
    D[计算 state_value]
    E[计算 state_confidence]
    F[计算 fresh_until]
    G[写 object_state / zone_state]
    H[更新 world_state 摘要]
    I[返回结果]

    A --> B --> C --> D --> E --> F --> G --> H --> I
```

---

## 13）freshness / stale 判定流程图

```text
flowchart TB
    A[输入 query + state]
    B[识别 query_recency_class]
    C[读取 freshness policy]
    D[获取 observed_at / fresh_until]
    E{设备是否离线超阈值}
    F{now > fresh_until}
    G[is_stale=false]
    H[is_stale=true]
    I{query 是否要求高实时}
    J[fallback_required=false]
    K[fallback_required=true]
    L[输出 reason_code]

    A --> B --> C --> D --> E
    E -- 是 --> H
    E -- 否 --> F
    F -- 否 --> G
    F -- 是 --> H

    G --> J --> L
    H --> I
    I -- 否 --> J
    I -- 是 --> K
    K --> L
```

---

## 14）Skill / Tool 决策流程图

```text
flowchart TB
    A[用户问题]
    B[Qwen3.5 理解意图]
    C[选择 Skill]
    D[加载 allowed_tools / allowed_resources]
    E{问题是否可直接回答}
    F[模型直接回答]
    G[调用 Tool]
    H[Tool 返回结构化结果]
    I[模型整合结果]
    J[Reply Builder]
    K[输出给 Telegram]

    A --> B --> C --> D --> E
    E -- 是 --> F --> J --> K
    E -- 否 --> G --> H --> I --> J --> K
```

---

## 15）权限校验链路图

```text
flowchart TB
    A[收到用户请求]
    B[validate_user_access]
    C{用户是否允许}
    D[拒绝并审计]
    E[解析意图]
    F[选择 Skill]
    G[validate_tool_access]
    H{Tool 是否允许}
    I[拒绝并审计]
    J[validate_resource_access]
    K{Resource 是否允许}
    L[拒绝并审计]
    M[执行工具]
    N[返回结果并审计]

    A --> B --> C
    C -- 否 --> D
    C -- 是 --> E --> F --> G --> H
    H -- 否 --> I
    H -- 是 --> J --> K
    K -- 否 --> L
    K -- 是 --> M --> N
```

---

## 16）OCR 双通道选择流程图

```text
flowchart TB
    A[收到 OCR 请求]
    B[是否有图片输入]
    C[要求是简单读字还是结构化提取]
    D[模型直接 OCR]
    E[调用 ocr_extract_fields]
    F[是否需要入库]
    G[写 observation / event]
    H[直接回复]
    I[最终回复]

    A --> B
    B -- 否 --> H --> I
    B -- 是 --> C
    C -- 简单读字 --> D --> F
    C -- 结构化提取 --> E --> F
    F -- 否 --> I
    F -- 是 --> G --> I
```

---

## 17）设备状态与告警流程图

```text
flowchart TB
    A[heartbeat 到达]
    B[更新 devices 表]
    C[计算 online/offline]
    D{是否状态变化}
    E[仅更新时间戳]
    F[生成 device event]
    G[写 audit / events]
    H{是否开启设备告警}
    I[发送 Telegram 通知]
    J[结束]

    A --> B --> C --> D
    D -- 否 --> E --> J
    D -- 是 --> F --> G --> H
    H -- 否 --> J
    H -- 是 --> I --> J
```

---

## 18）系统状态机图

```text
stateDiagram-v2
    [*] --> Idle
    Idle --> ReceivingUpdate: Telegram update
    ReceivingUpdate --> Authorizing: validate user
    Authorizing --> Rejected: unauthorized
    Authorizing --> Planning: authorized
    Planning --> DirectAnswer: no tool required
    Planning --> ToolCalling: tool required
    ToolCalling --> WaitingToolResult
    WaitingToolResult --> Synthesizing
    DirectAnswer --> SendingReply
    Synthesizing --> SendingReply
    SendingReply --> Idle
    Rejected --> Idle
```

---

## 19）对象状态机图

```text
stateDiagram-v2
    [*] --> Unknown
    Unknown --> Present: observation confirms present
    Present --> Present: consistent evidence
    Present --> LikelyAbsent: no recent evidence
    LikelyAbsent --> Absent: stale + contradiction
    LikelyAbsent --> Present: new confirming evidence
    Absent --> Present: fresh observation
    Absent --> Unknown: conflicting evidence
    Present --> Unknown: device offline / ambiguity
    Unknown --> Absent: negative evidence
```

---

## 20）数据库 ER 图（总图）

```text
erDiagram
    DEVICES ||--o{ OBSERVATIONS : produces
    OBSERVATIONS ||--o{ EVENTS : may_upgrade_to
    OBSERVATIONS ||--o{ MEDIA_ITEMS : references
    EVENTS ||--o{ MEDIA_ITEMS : references
    OBJECT_STATES }o--|| DEVICES : from_camera
    ZONE_STATES }o--|| DEVICES : from_camera
    AUDIT_LOGS }o--|| DEVICES : device_related
    AUDIT_LOGS }o--|| USERS : user_related

    DEVICES {
        string device_id PK
        string camera_id
        string api_key_hash
        string status
        datetime last_seen
        float temperature
        float cpu_load
        float npu_load
        int free_mem_mb
        int camera_fps
        datetime created_at
        datetime updated_at
    }

    OBSERVATIONS {
        string id PK
        string device_id FK
        string camera_id
        string zone_id
        string object_name
        string object_class
        string track_id
        float confidence
        datetime observed_at
        datetime fresh_until
        string source_event_id
        string snapshot_uri
        string clip_uri
        string visibility_scope
        string raw_payload_json
        datetime created_at
    }

    EVENTS {
        string id PK
        string observation_id FK
        string event_type
        string category
        int importance
        string zone_id
        string object_name
        string summary
        datetime event_at
        string payload_json
        datetime created_at
    }

    OBJECT_STATES {
        string id PK
        string object_name
        string camera_id
        string zone_id
        string state_value
        float state_confidence
        datetime observed_at
        datetime last_confirmed_at
        datetime last_changed_at
        datetime fresh_until
        boolean is_stale
        int evidence_count
        string source_layer
        string summary
        datetime updated_at
    }

    ZONE_STATES {
        string id PK
        string camera_id
        string zone_id
        string state_value
        float state_confidence
        datetime observed_at
        datetime fresh_until
        boolean is_stale
        int evidence_count
        string source_layer
        string summary
        datetime updated_at
    }

    MEDIA_ITEMS {
        string id PK
        string owner_type
        string owner_id
        string media_type
        string uri
        string local_path
        string visibility_scope
        int duration_sec
        int width
        int height
        datetime created_at
    }

    USERS {
        string user_id PK
        string telegram_user_id
        string display_name
        string role
        boolean is_allowed
        datetime created_at
        datetime updated_at
    }

    AUDIT_LOGS {
        string id PK
        string user_id FK
        string device_id FK
        string action
        string target_type
        string target_id
        string decision
        string reason
        string trace_id
        datetime created_at
    }
```

---

## 21）数据库表分层图

```text
flowchart LR
    subgraph RAW[Raw Layer]
        OBS[observations]
        MEDIA[media_items]
        DEV[devices]
    end

    subgraph EVENTL[Event Layer]
        EVT[events]
    end

    subgraph STATE[State Layer]
        OST[object_states]
        ZST[zone_states]
        WST[world_state view]
    end

    subgraph GOV[Governance Layer]
        USERS[users]
        AUD[audit_logs]
        POL[policies config]
    end

    OBS --> EVT
    OBS --> OST
    OBS --> ZST
    EVT --> OST
    EVT --> ZST
    OST --> WST
    ZST --> WST
    DEV --> OBS
    USERS --> AUD
    DEV --> AUD
```

---

## 22）核心数据模型类图

```text
classDiagram
    class Observation {
        +id: str
        +device_id: str
        +camera_id: str
        +zone_id: str
        +object_name: str
        +object_class: str
        +track_id: str
        +confidence: float
        +observed_at: datetime
        +fresh_until: datetime
        +snapshot_uri: str
        +clip_uri: str
        +visibility_scope: str
    }

    class Event {
        +id: str
        +observation_id: str
        +event_type: str
        +category: str
        +importance: int
        +event_at: datetime
        +summary: str
    }

    class ObjectState {
        +id: str
        +object_name: str
        +camera_id: str
        +zone_id: str
        +state_value: str
        +state_confidence: float
        +observed_at: datetime
        +fresh_until: datetime
        +is_stale: bool
        +evidence_count: int
        +summary: str
    }

    class ZoneState {
        +id: str
        +camera_id: str
        +zone_id: str
        +state_value: str
        +state_confidence: float
        +observed_at: datetime
        +fresh_until: datetime
        +is_stale: bool
        +summary: str
    }

    class DeviceStatus {
        +device_id: str
        +online: bool
        +temperature: float
        +cpu_load: float
        +npu_load: float
        +free_mem_mb: int
        +camera_fps: int
        +last_seen: datetime
    }

    Observation --> Event
    Observation --> ObjectState
    Observation --> ZoneState
    DeviceStatus --> Observation
```

---

## 23）服务关系类图

```text
classDiagram
    class PerceptionService {
        +ingest_event()
        +write_observation()
        +trigger_state_refresh()
    }

    class MemoryService {
        +create_observation()
        +create_event()
        +query_recent_events()
        +last_seen()
    }

    class StateService {
        +refresh_object_state()
        +refresh_zone_state()
        +get_object_state()
        +get_zone_state()
        +get_world_state()
    }

    class PolicyService {
        +evaluate_staleness()
        +classify_query_recency()
    }

    class DeviceService {
        +take_snapshot()
        +get_recent_clip()
        +heartbeat()
        +device_status()
    }

    class OCRService {
        +quick_read()
        +extract_fields()
    }

    class SecurityGuard {
        +validate_user_access()
        +validate_tool_access()
        +validate_resource_access()
        +audit()
    }

    PerceptionService --> MemoryService
    PerceptionService --> StateService
    StateService --> PolicyService
    DeviceService --> SecurityGuard
    OCRService --> SecurityGuard
```

---

## 24）API 路由图

```text
flowchart TB
    APP[FastAPI / Backend App]

    APP --> H[/healthz]
    APP --> M1[/memory/recent-events]
    APP --> M2[/memory/last-seen]
    APP --> S1[/memory/object-state]
    APP --> S2[/memory/zone-state]
    APP --> S3[/memory/world-state]
    APP --> P1[/policy/evaluate-staleness]
    APP --> D1[/device/status]
    APP --> D2[/device/command/take-snapshot]
    APP --> D3[/device/command/get-recent-clip]
    APP --> I1[/device/ingest/event]
    APP --> I2[/device/heartbeat]
    APP --> O1[/ocr/quick-read]
    APP --> O2[/ocr/extract-fields]
```

---

## 25）MCP 结构图

```text
flowchart TB
    MCP[MCP Server Layer]

    MCP --> T[Tools]
    MCP --> R[Resources]
    MCP --> P[Prompts]

    T --> T1[take_snapshot]
    T --> T2[get_recent_clip]
    T --> T3[describe_scene]
    T --> T4[last_seen_object]
    T --> T5[get_object_state]
    T --> T6[get_zone_state]
    T --> T7[get_world_state]
    T --> T8[query_recent_events]
    T --> T9[evaluate_staleness]
    T --> T10[ocr_quick_read]
    T --> T11[ocr_extract_fields]
    T --> T12[device_status]

    R --> R1[resource://memory/observations]
    R --> R2[resource://memory/events]
    R --> R3[resource://memory/object_states]
    R --> R4[resource://memory/zone_states]
    R --> R5[resource://policy/freshness]
    R --> R6[resource://security/access_scope]
    R --> R7[resource://devices/status]

    P --> P1[scene_query]
    P --> P2[history_query]
    P --> P3[last_seen_query]
    P --> P4[object_state_query]
    P --> P5[zone_state_query]
    P --> P6[ocr_query]
```

---

## 26）配置加载图

```text
flowchart TB
    A[启动 backend]
    B[加载 settings.yaml]
    C[加载 policies.yaml]
    D[加载 access.yaml]
    E[加载 devices.yaml]
    F[加载 cameras.yaml]
    G[构建 Settings 对象]
    H[初始化服务]
    I[启动 API / MCP]

    A --> B --> C --> D --> E --> F --> G --> H --> I
```

---

## 27）测试矩阵图

```text
flowchart TB
    TESTS[Tests]

    TESTS --> U[Unit]
    TESTS --> I[Integration]
    TESTS --> E[E2E]

    U --> U1[test_state_service]
    U --> U2[test_policy_service]
    U --> U3[test_security_guard]
    U --> U4[test_memory_tiering]
    U --> U5[test_ocr_routing]

    I --> I1[test_device_event_flow]
    I --> I2[test_object_state_flow]
    I --> I3[test_zone_state_flow]
    I --> I4[test_stale_fallback_flow]
    I --> I5[test_access_control_flow]
    I --> I6[test_telegram_message_flow]

    E --> E1[telegram_current_scene]
    E --> E2[telegram_last_seen]
    E --> E3[telegram_object_state]
    E --> E4[telegram_ocr]
    E --> E5[telegram_take_snapshot]
    E --> E6[device_offline_alert]
```

---

## 28）开发里程碑图

```text
gantt
    title 视觉管家系统 v5 研发里程碑
    dateFormat  YYYY-MM-DD

    section 入口与宿主
    Telegram Bot 接入           :a1, 2026-03-15, 5d
    nanobot 配置与联调          :a2, after a1, 5d
    Qwen3.5 模型接入            :a3, after a2, 4d

    section 能力层
    MCP Tools 实现              :b1, after a3, 8d
    Skills 编排                 :b2, after b1, 6d

    section 前端
    RK3566 事件采集             :c1, 2026-03-20, 8d
    snapshot / clip             :c2, after c1, 5d
    heartbeat / device status   :c3, after c1, 5d

    section 事实层
    observation / event         :d1, after b2, 6d
    state / policy              :d2, after d1, 6d
    OCR 双通道                  :d3, after d2, 5d

    section 验收
    集成测试                    :e1, after d3, 6d
    E2E 与部署                  :e2, after e1, 5d
```

---

## 29）项目边界图

```text
flowchart TB
    P[视觉管家系统 v5]

    P --> IN[纳入范围]
    P --> OUT[明确不做]

    IN --> IN1[Telegram 正式入口]
    IN --> IN2[nanobot 主控宿主]
    IN --> IN3[Qwen3.5 多模态]
    IN --> IN4[MCP + Skill]
    IN --> IN5[RK3566 单目前端]
    IN --> IN6[状态/时效/记忆/安全]
    IN --> IN7[简单 OCR + 工具 OCR]
    IN --> IN8[设备监控与主动通知]

    OUT --> O1[运动控制]
    OUT --> O2[ROS/ROS2]
    OUT --> O3[3D 建图]
    OUT --> O4[多机器人协同]
    OUT --> O5[云端多租户]
    OUT --> O6[复杂空间图谱]
    OUT --> O7[单目前端精确 3D 定位]
```

---

## 30）一页版“从用户到设备再回用户”的总流程图

```text
flowchart LR
    U[用户 Telegram] --> NB[nanobot]
    NB --> QW[Qwen3.5]
    QW --> SK[Skill]
    SK --> MCP[MCP Tools]
    MCP --> APP[Backend Services]
    APP --> DB[(SQLite / Media)]
    APP --> EDGE[RK3566]
    EDGE --> APP
    APP --> MCP
    MCP --> QW
    QW --> NB
    NB --> U
```

如果你要，我下一条可以继续给你补两类内容：
第一类是**“每张图对应的简短图注/说明文字”**，方便你直接粘到计划书里；第二类是**“每张数据库表的字段清单”**，我可以按 Markdown 表格继续单独补齐。

[1]: https://mermaid.js.org/intro/syntax-reference.html?trk=public_post_comment-text&utm_source=chatgpt.com "Diagram Syntax | Mermaid"

可以，下面就是**第一类：每张图对应的简短图注 / 说明文字**。我按上一条给你的图顺序一一对应，你可以直接复制到图下面用。
这些图注的写法保持“项目书正式说明”风格，尽量短、稳、可直接贴正文；其中涉及 Telegram、nanobot、MCP、Qwen 工具调用关系的表述，与官方公开能力边界一致：Telegram 是 Bot HTTP 入口，nanobot 可挂 MCP，MCP 的 tools/resources/prompts 是正式能力面，Qwen 的函数调用是“模型决定是否调工具，应用执行工具并回灌结果”的模式。([core.telegram.org](https://core.telegram.org/bots/api?utm_source=chatgpt.com)) ([Telegram][1])

---

### 1）系统总体架构图图注

本图展示系统的完整总体架构。用户通过 Telegram 与系统交互，nanobot 作为唯一主控宿主承接会话与模型调用，Qwen3.5 负责理解问题与整合结果，MCP 负责把视觉、记忆、状态、OCR 与设备能力标准化暴露给模型，后端 sidecar 服务负责事实层，RK3566 单目前端负责边缘感知与事件上报。([github.com](https://github.com/HKUDS/nanobot/blob/main/README.md?utm_source=chatgpt.com)) ([GitHub][2])

### 2）正式部署拓扑图图注

本图展示系统在实际部署时的物理与逻辑拓扑关系。Telegram Bot API 位于外部消息入口，x86 主机运行 nanobot、MCP 服务与后端业务服务，RK3566 前端连接单目摄像头并向主机回传事件、快照与设备状态。([core.telegram.org](https://core.telegram.org/bots/api?utm_source=chatgpt.com)) ([Telegram][1])

### 3）nanobot 运行时组件图图注

本图展示 nanobot 在本项目中的运行时组成。配置文件决定 Telegram channel、模型、Skill、MCP servers 与 workspace 的组织方式，nanobot 负责在会话上下文中协调模型推理、工具调用与最终回复生成。([github.com](https://github.com/HKUDS/nanobot/tree/main/?utm_source=chatgpt.com)) ([GitHub][3])

### 4）完整产品能力地图图注

本图用于总览本项目首发即纳入范围的正式能力，包括当前观察、历史事件、last_seen、状态推定、主动取证、OCR、设备状态与主动通知。它体现了本项目不是单一“看图问答”工具，而是一个完整的视觉管家系统。

### 5）Telegram 用户查询主流程图图注

本图描述用户从 Telegram 发起请求到收到最终回复的标准处理链路。系统先完成权限检查与意图理解，再由模型结合 Skill 决定是否调用 MCP tool；若调用工具，则以“模型判断、应用执行、结果回灌、模型整合”的方式完成最终回答。([core.telegram.org](https://core.telegram.org/bots/api?utm_source=chatgpt.com)) ([Telegram][1])

### 6）当前观察查询时序图图注

本图展示“现在门口什么情况”这类实时观察问题的处理顺序。系统通过 `take_snapshot` 从前端拉取最新画面，再由模型结合场景理解能力生成当前观察结果，并通过 Telegram 回传给用户。

### 7）历史事件查询时序图图注

本图展示“最近发生了什么”类问题的处理过程。系统通过 memory 层检索 observation 与 event，并在需要时结合状态层输出当前摘要，使回答既有时间序列回顾，也有当前上下文说明。

### 8）last_seen / object_state 查询时序图图注

本图展示“某物最后在哪里看到”与“某物现在大概率还在不在”两类问题的核心处理流程。系统先读取 state 结果，再由 policy 层评估 stale 与 freshness，最后给出带可信度和时效说明的回答。

### 9）OCR 查询时序图图注

本图展示本项目 OCR 的双通道机制。简单文字读取可由 Qwen3.5 直接完成；对于字段提取、长文本或需结构化存档的场景，则通过独立 OCR tool 完成识别与解析，再由模型整合成用户可读答案。([help.aliyun.com](https://help.aliyun.com/zh/model-studio/qwen-function-calling?utm_source=chatgpt.com)) ([阿里云帮助中心][4])

### 10）主动通知流程图图注

本图展示系统从前端事件发生到主动通知用户的内部流程。事件先进入 perception 层，经 observation、event、state 更新后，再依据通知规则决定是否通过 Telegram 向用户发送主动提醒。

### 11）前端事件上报流程图图注

本图展示 RK3566 前端从相机采集到事件上报的完整链路。前端负责图像采集、检测、跟踪、事件压缩和本地缓存，其职责是生产“可供后端理解和聚合的事件”，而不是承载完整业务真相层。

### 12）状态刷新流程图图注

本图展示 state_service 如何利用新的 observation 或 event 刷新 object_state 与 zone_state。状态层的本质不是原始记录，而是基于最近证据、时效与冲突情况生成的当前推定结果。

### 13）freshness / stale 判定流程图图注

本图展示 policy_service 的核心职责。系统根据 query 的实时性要求、对象或区域的 freshness policy 以及设备当前健康状况，判定结果是否 stale，并决定是否需要 fallback。([help.aliyun.com](https://help.aliyun.com/zh/model-studio/qwen-function-calling?utm_source=chatgpt.com)) ([阿里云帮助中心][4])

### 14）Skill / Tool 决策流程图图注

本图展示 Skill 与 Tool 的关系。Skill 用来定义某类问题的标准执行模板、允许调用的工具与回退顺序，模型在 Skill 约束下决定是否需要调用工具，再由 Reply Builder 构造最终输出。([modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-06-18/server/tools?utm_source=chatgpt.com)) ([Model Context Protocol][5])

### 15）权限校验链路图图注

本图展示系统从用户请求进入到工具执行前的完整安全校验顺序。权限控制不仅校验 Telegram 用户是否允许访问，还校验所选 Skill 是否允许调用对应 tool、读取对应 resource，并将全过程写入审计日志。

### 16）OCR 双通道选择流程图图注

本图专门说明 OCR 能力的分流策略。系统优先用模型直接完成低频、轻量的读字任务；当请求进入结构化抽取、高价值识别或需入库留痕的场景时，则转入专用 OCR tool 处理。

### 17）设备状态与告警流程图图注

本图展示前端设备心跳与设备告警的逻辑。设备 heartbeat 进入系统后先更新状态表，再判断是否发生上线/离线变化；若命中告警规则，则通过 Telegram 主动通知用户。

### 18）系统状态机图图注

本图从运行态角度描述系统的主循环。系统在空闲、接收消息、权限校验、规划、工具调用、结果整合与回消息之间切换，体现出这是一个受控的 Agent 工作流，而不是单轮静态问答。([help.aliyun.com](https://help.aliyun.com/zh/model-studio/qwen-function-calling?utm_source=chatgpt.com)) ([阿里云帮助中心][4])

### 19）对象状态机图图注

本图展示 object_state 的生命周期。对象状态会在 `present`、`likely_absent`、`absent` 与 `unknown` 之间变化，变化依据不是单次识别结果，而是近期证据、时效衰减、设备状态与反证情况。

### 20）数据库 ER 图（总图）图注

本图展示系统数据库的核心实体关系。`observations` 是原始感知记录，`events` 是显著变化，`object_states` 与 `zone_states` 是当前推定层，`devices`、`media_items` 与 `audit_logs` 分别承担设备、媒体与治理能力。

### 21）数据库表分层图图注

本图从逻辑层面说明数据如何分层组织。原始层保存 observation、media 与设备信息，事件层保存显著性升级记录，状态层保存当前推定结果，治理层保存用户、审计与策略信息。

### 22）核心数据模型类图图注

本图展示最核心的数据模型及其关联关系。它用于说明 Observation、Event、ObjectState、ZoneState 与 DeviceStatus 在代码层和领域层中的职责划分，是后续 schema、repository 与 API 设计的基础。

### 23）服务关系类图图注

本图展示后端主要服务之间的调用关系。perception_service 负责接入前端事件，memory_service 负责持久化与查询，state_service 负责状态推理，policy_service 负责 stale 判定，device_service 与 ocr_service 负责外部能力执行，security_guard 负责统一权限与审计。

### 24）API 路由图图注

本图展示后端正式暴露的主要 HTTP 路由。它把 memory、state、policy、device 与 OCR 能力拆分为清晰接口，既便于 MCP tools 封装，也便于单独测试与回归验证。

### 25）MCP 结构图图注

本图展示 MCP 层在本项目中的组织方式。Tools 提供可执行动作，Resources 提供上下文与状态视图，Prompts 提供标准模板；这种分层方式与 MCP 官方规范保持一致，也最适合挂载到 nanobot 中供模型发现和调用。([modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-03-26?utm_source=chatgpt.com)) ([Model Context Protocol][6])

### 26）配置加载图图注

本图展示系统启动时的配置装配顺序。系统会依次加载 settings、policies、access、devices、cameras 等配置，构造统一的 Settings 对象，再初始化服务与 API，从而保证运行参数、权限策略和设备清单统一受控。

### 27）测试矩阵图图注

本图展示完整测试体系的分层设计。单元测试验证 state、policy、security 等局部逻辑，集成测试覆盖设备流、状态流与权限流，E2E 测试则以 Telegram 为正式入口验证真实用户链路。

### 28）开发里程碑图图注

本图展示项目的建议实施节奏。它强调先打通 Telegram、nanobot 与模型入口，再完成 MCP 与前端事件链，随后补齐状态、策略与 OCR，最后进入集成测试与正式部署阶段。

### 29）项目边界图图注

本图用于明确本项目的正式边界。纳入范围包括 Telegram 正式入口、nanobot 主控、Qwen3.5、多模态视觉、MCP/Skill、RK3566 单目前端和状态/时效/OCR/安全体系；排除范围包括 ROS、3D 建图、多机器人与单目前端精确 3D 定位。

### 30）一页版总流程图图注

本图是一张一页式总览图，用于快速说明整个系统如何从用户请求出发，经由 nanobot、Qwen3.5、Skill、MCP、后端服务与 RK3566 前端，最终再回到用户。它适合放在项目书开头，作为读者理解全局结构的第一张图。

如果你要，我下一条就继续给你第二类：**各数据库表的字段清单说明**。

[1]: https://core.telegram.org/bots/api?utm_source=chatgpt.com "Telegram Bot API"
[2]: https://github.com/HKUDS/nanobot/blob/main/README.md?utm_source=chatgpt.com "nanobot/README.md at main · HKUDS/nanobot · GitHub"
[3]: https://github.com/HKUDS/nanobot/tree/main/?utm_source=chatgpt.com "GitHub - HKUDS/nanobot: \" nanobot: The Ultra-Lightweight OpenClaw\""
[4]: https://help.aliyun.com/zh/model-studio/qwen-function-calling?utm_source=chatgpt.com "如何通过Function Calling 实现工具调用-大模型服务平台百炼 ..."
[5]: https://modelcontextprotocol.io/specification/2025-06-18/server/tools?utm_source=chatgpt.com "Tools - Model Context Protocol"
[6]: https://modelcontextprotocol.io/specification/2025-03-26?utm_source=chatgpt.com "Specification - Model Context Protocol"


可以。下面这部分就是你要的**第二类内容：各数据库表的字段清单说明**。
我按“**可直接贴进项目书 / 设计文档**”的方式写，统一给出：

* 表名
* 表用途
* 推荐字段
* 类型建议
* 是否必填
* 说明

先说两个总原则，方便你放在这部分前面当总说明：

本项目的数据层以 **SQLite + FTS5** 为正式方案，原因是它天然适合单机、嵌入式、轻量部署场景，而 FTS5 又能直接提供全文检索能力，适合做 observation、event、OCR 文本和历史摘要的搜索。SQLite 官方文档明确说明 FTS5 是内置全文检索扩展，可以通过虚拟表方式建立全文索引。([sqlite.org][1])

另外，由于 Telegram Bot API 的更新只会在服务器上保留 **最长 24 小时**，而且 `getUpdates` / webhook 是两种互斥方式，所以如果你走 polling，建议单独保留 `telegram_updates` 去重与追踪表，避免重启、补拉和重复消费时出现混乱。([Telegram][2])

---

# 一、核心正式表

## 1. `users`

**用途**：保存允许访问系统的 Telegram 用户及其权限基础信息。

| 字段名                | 类型建议      | 必填 | 说明                                |
| ------------------ | --------- | -: | --------------------------------- |
| `id`               | `TEXT`    |  是 | 内部用户主键，建议使用 UUID                  |
| `telegram_user_id` | `TEXT`    |  是 | Telegram 用户 ID，唯一                 |
| `telegram_chat_id` | `TEXT`    |  否 | 默认私聊 chat_id，便于主动通知               |
| `display_name`     | `TEXT`    |  否 | 用户显示名称                            |
| `username`         | `TEXT`    |  否 | Telegram username                 |
| `role`             | `TEXT`    |  是 | 角色，如 `owner` / `admin` / `viewer` |
| `is_allowed`       | `INTEGER` |  是 | 是否允许访问，0/1                        |
| `media_scope`      | `TEXT`    |  否 | 可访问媒体范围，如 `all` / `own` / `none`  |
| `note`             | `TEXT`    |  否 | 备注                                |
| `created_at`       | `TEXT`    |  是 | 创建时间，ISO8601                      |
| `updated_at`       | `TEXT`    |  是 | 更新时间                              |

**说明**：
这张表是业务权限的用户事实表，不等同于 nanobot 的 `allowFrom`。`allowFrom` 解决的是入口级访问限制；`users` 表解决的是系统内细粒度授权与审计。

---

## 2. `devices`

**用途**：保存 RK3566 前端设备与摄像头的注册信息、认证信息和健康状态。

| 字段名                | 类型建议      | 必填 | 说明                                |
| ------------------ | --------- | -: | --------------------------------- |
| `id`               | `TEXT`    |  是 | 内部设备主键                            |
| `device_id`        | `TEXT`    |  是 | 设备逻辑 ID，唯一                        |
| `camera_id`        | `TEXT`    |  是 | 摄像头 ID，唯一或与 device_id 组成唯一键       |
| `device_name`      | `TEXT`    |  否 | 设备名称                              |
| `api_key_hash`     | `TEXT`    |  是 | 设备 API Key 的哈希值                   |
| `status`           | `TEXT`    |  是 | `online` / `offline` / `degraded` |
| `ip_addr`          | `TEXT`    |  否 | 最近一次上报的 IP                        |
| `firmware_version` | `TEXT`    |  否 | 前端代码/固件版本                         |
| `model_version`    | `TEXT`    |  否 | 当前板端检测模型版本                        |
| `temperature`      | `REAL`    |  否 | 当前温度                              |
| `cpu_load`         | `REAL`    |  否 | CPU 负载                            |
| `npu_load`         | `REAL`    |  否 | NPU 负载                            |
| `free_mem_mb`      | `INTEGER` |  否 | 可用内存                              |
| `camera_fps`       | `INTEGER` |  否 | 当前采集帧率                            |
| `last_seen`        | `TEXT`    |  是 | 最近心跳时间                            |
| `created_at`       | `TEXT`    |  是 | 创建时间                              |
| `updated_at`       | `TEXT`    |  是 | 更新时间                              |

**说明**：
`devices` 表既是设备认证表，也是设备状态表。后端所有 `/device/*` 能力都应该先查这张表。

---

## 3. `observations`

**用途**：保存所有原始或半结构化观察记录，是全系统的第一事实层。

| 字段名                | 类型建议   | 必填 | 说明                                  |
| ------------------ | ------ | -: | ----------------------------------- |
| `id`               | `TEXT` |  是 | observation 主键                      |
| `device_id`        | `TEXT` |  是 | 来源设备 ID                             |
| `camera_id`        | `TEXT` |  是 | 来源摄像头 ID                            |
| `zone_id`          | `TEXT` |  否 | 所属区域 ID                             |
| `object_name`      | `TEXT` |  否 | 目标名称，如 `cup`                        |
| `object_class`     | `TEXT` |  否 | 类别名称，如 `person` / `package`         |
| `track_id`         | `TEXT` |  否 | 跟踪 ID                               |
| `confidence`       | `REAL` |  否 | 置信度                                 |
| `state_hint`       | `TEXT` |  否 | 可选状态提示，如 `appeared` / `disappeared` |
| `observed_at`      | `TEXT` |  是 | 观察发生时间                              |
| `fresh_until`      | `TEXT` |  否 | 该 observation 的时效截止时间               |
| `source_event_id`  | `TEXT` |  否 | 来源事件 ID，用于关联压缩链路                    |
| `snapshot_uri`     | `TEXT` |  否 | 快照 URI                              |
| `clip_uri`         | `TEXT` |  否 | 视频 URI                              |
| `ocr_text`         | `TEXT` |  否 | 如本条观察包含 OCR 结果，可存摘要文本               |
| `visibility_scope` | `TEXT` |  否 | 可见范围                                |
| `raw_payload_json` | `TEXT` |  否 | 原始前端载荷 JSON                         |
| `created_at`       | `TEXT` |  是 | 写入时间                                |

**说明**：
这张表一定要“宁多勿少”。系统是否能回溯历史、重建状态、修正推理，很大程度取决于 observation 是否保真。

---

## 4. `events`

**用途**：保存从 observation 中升级出来的显著性变化记录。

| 字段名              | 类型建议      | 必填 | 说明                                                       |
| ---------------- | --------- | -: | -------------------------------------------------------- |
| `id`             | `TEXT`    |  是 | event 主键                                                 |
| `observation_id` | `TEXT`    |  否 | 来源 observation                                           |
| `event_type`     | `TEXT`    |  是 | 如 `person_entered` / `object_missing` / `device_offline` |
| `category`       | `TEXT`    |  是 | `event` / `episode`                                      |
| `importance`     | `INTEGER` |  是 | 重要性等级，建议 1-5                                             |
| `camera_id`      | `TEXT`    |  否 | 摄像头 ID                                                   |
| `zone_id`        | `TEXT`    |  否 | 区域 ID                                                    |
| `object_name`    | `TEXT`    |  否 | 关联对象                                                     |
| `summary`        | `TEXT`    |  是 | 事件摘要                                                     |
| `payload_json`   | `TEXT`    |  否 | 详细载荷                                                     |
| `event_at`       | `TEXT`    |  是 | 事件发生时间                                                   |
| `created_at`     | `TEXT`    |  是 | 写入时间                                                     |

**说明**：
不是所有 observation 都应升级成 event。event 应当专门服务于“最近发生了什么”“是否命中通知规则”这两类需求。

---

## 5. `object_states`

**用途**：保存对象当前推定状态。

| 字段名                 | 类型建议      | 必填 | 说明                                |
| ------------------- | --------- | -: | --------------------------------- |
| `id`                | `TEXT`    |  是 | state 主键                          |
| `object_name`       | `TEXT`    |  是 | 对象名称                              |
| `camera_id`         | `TEXT`    |  否 | 摄像头 ID                            |
| `zone_id`           | `TEXT`    |  否 | 区域 ID                             |
| `state_value`       | `TEXT`    |  是 | `present` / `absent` / `unknown`  |
| `state_confidence`  | `REAL`    |  是 | 当前状态置信度                           |
| `observed_at`       | `TEXT`    |  否 | 最近证据时间                            |
| `last_confirmed_at` | `TEXT`    |  否 | 最近确认时间                            |
| `last_changed_at`   | `TEXT`    |  否 | 状态最近变更时间                          |
| `fresh_until`       | `TEXT`    |  否 | 状态有效时间                            |
| `is_stale`          | `INTEGER` |  是 | 0/1                               |
| `evidence_count`    | `INTEGER` |  否 | 使用了多少条证据                          |
| `source_layer`      | `TEXT`    |  否 | `observation` / `event` / `state` |
| `summary`           | `TEXT`    |  否 | 当前状态摘要                            |
| `updated_at`        | `TEXT`    |  是 | 更新时间                              |

**说明**：
这张表是回答“现在大概率还在不在”的核心表。查询时应优先查它，再回退 `observations`。

---

## 6. `zone_states`

**用途**：保存区域当前推定状态。

| 字段名                | 类型建议      | 必填 | 说明                                                   |
| ------------------ | --------- | -: | ---------------------------------------------------- |
| `id`               | `TEXT`    |  是 | zone_state 主键                                        |
| `camera_id`        | `TEXT`    |  是 | 摄像头 ID                                               |
| `zone_id`          | `TEXT`    |  是 | 区域 ID                                                |
| `state_value`      | `TEXT`    |  是 | `occupied` / `empty` / `likely_occupied` / `unknown` |
| `state_confidence` | `REAL`    |  是 | 置信度                                                  |
| `observed_at`      | `TEXT`    |  否 | 最近证据时间                                               |
| `fresh_until`      | `TEXT`    |  否 | 时效截止时间                                               |
| `is_stale`         | `INTEGER` |  是 | 0/1                                                  |
| `evidence_count`   | `INTEGER` |  否 | 证据数量                                                 |
| `source_layer`     | `TEXT`    |  否 | 来源层                                                  |
| `summary`          | `TEXT`    |  否 | 区域摘要                                                 |
| `updated_at`       | `TEXT`    |  是 | 更新时间                                                 |

**说明**：
这张表是回答“客厅现在像不像有人”“门口区域当前是不是像有快递”的核心表。

---

## 7. `media_items`

**用途**：保存系统中图片、视频片段等媒体的统一索引。

| 字段名                | 类型建议      | 必填 | 说明                                         |
| ------------------ | --------- | -: | ------------------------------------------ |
| `id`               | `TEXT`    |  是 | media 主键                                   |
| `owner_type`       | `TEXT`    |  是 | `observation` / `event` / `ocr` / `manual` |
| `owner_id`         | `TEXT`    |  是 | 归属记录 ID                                    |
| `media_type`       | `TEXT`    |  是 | `image` / `video` / `crop`                 |
| `uri`              | `TEXT`    |  是 | 对外 URI 或逻辑 URI                             |
| `local_path`       | `TEXT`    |  是 | 本地路径                                       |
| `mime_type`        | `TEXT`    |  否 | MIME 类型                                    |
| `duration_sec`     | `INTEGER` |  否 | 视频时长                                       |
| `width`            | `INTEGER` |  否 | 宽度                                         |
| `height`           | `INTEGER` |  否 | 高度                                         |
| `visibility_scope` | `TEXT`    |  否 | 访问范围                                       |
| `sha256`           | `TEXT`    |  否 | 去重校验                                       |
| `created_at`       | `TEXT`    |  是 | 创建时间                                       |

**说明**：
媒体一定要独立建表，不要只把路径散落在 observation/event 里。这样后续做权限控制、回放、清理与去重才有基础。

---

## 8. `audit_logs`

**用途**：保存用户访问、工具调用、设备命令、权限拒绝等审计信息。

| 字段名           | 类型建议   | 必填 | 说明                                     |
| ------------- | ------ | -: | -------------------------------------- |
| `id`          | `TEXT` |  是 | audit 主键                               |
| `user_id`     | `TEXT` |  否 | 关联 users.id                            |
| `device_id`   | `TEXT` |  否 | 关联设备                                   |
| `action`      | `TEXT` |  是 | 行为，如 `read_state` / `take_snapshot`    |
| `target_type` | `TEXT` |  否 | `object` / `zone` / `media` / `device` |
| `target_id`   | `TEXT` |  否 | 目标 ID                                  |
| `decision`    | `TEXT` |  是 | `allow` / `deny`                       |
| `reason`      | `TEXT` |  否 | 原因说明                                   |
| `trace_id`    | `TEXT` |  否 | 全链路追踪 ID                               |
| `meta_json`   | `TEXT` |  否 | 扩展字段                                   |
| `created_at`  | `TEXT` |  是 | 时间                                     |

**说明**：
所有拒绝、越权、敏感媒体读取、设备命令都建议打到这张表。它是后期定位问题和做安全追踪的基础。

---

# 二、推荐辅助表

## 9. `telegram_updates`

**用途**：记录 Telegram update 的消费与去重状态。

| 字段名             | 类型建议   | 必填 | 说明                                     |
| --------------- | ------ | -: | -------------------------------------- |
| `id`            | `TEXT` |  是 | 内部主键                                   |
| `update_id`     | `TEXT` |  是 | Telegram update_id，唯一                  |
| `chat_id`       | `TEXT` |  否 | 来源 chat                                |
| `from_user_id`  | `TEXT` |  否 | 来源用户                                   |
| `message_type`  | `TEXT` |  否 | `text` / `photo` / `video` / `command` |
| `message_text`  | `TEXT` |  否 | 原始文本                                   |
| `received_at`   | `TEXT` |  是 | 收到时间                                   |
| `processed_at`  | `TEXT` |  否 | 处理完成时间                                 |
| `status`        | `TEXT` |  是 | `received` / `processed` / `failed`    |
| `error_message` | `TEXT` |  否 | 错误信息                                   |
| `trace_id`      | `TEXT` |  否 | 追踪 ID                                  |

**说明**：
Telegram 官方说明，更新不会在服务器保留超过 24 小时，因此本地如果不记录 `update_id` 与处理状态，重启、补拉和重复消费时会很难排查。([Telegram][2])

---

## 10. `notification_rules`

**用途**：保存主动通知规则。

| 字段名                 | 类型建议      | 必填 | 说明                                         |
| ------------------- | --------- | -: | ------------------------------------------ |
| `id`                | `TEXT`    |  是 | 规则主键                                       |
| `user_id`           | `TEXT`    |  是 | 归属用户                                       |
| `rule_name`         | `TEXT`    |  是 | 规则名称                                       |
| `trigger_type`      | `TEXT`    |  是 | `event` / `state_change` / `device_status` |
| `target_scope`      | `TEXT`    |  否 | 目标范围，如 `door` / `living_room` / `package`  |
| `condition_json`    | `TEXT`    |  是 | 触发条件                                       |
| `is_enabled`        | `INTEGER` |  是 | 0/1                                        |
| `cooldown_sec`      | `INTEGER` |  否 | 冷却时间                                       |
| `last_triggered_at` | `TEXT`    |  否 | 最近触发时间                                     |
| `created_at`        | `TEXT`    |  是 | 创建时间                                       |
| `updated_at`        | `TEXT`    |  是 | 更新时间                                       |

**说明**：
如果你要把“有人出现提醒我”“设备离线提醒我”做成正式能力，这张表很有必要。

---

## 11. `facts`

**用途**：保存长期稳定信息，而不是短期观察。

| 字段名          | 类型建议   | 必填 | 说明                           |
| ------------ | ------ | -: | ---------------------------- |
| `id`         | `TEXT` |  是 | fact 主键                      |
| `fact_key`   | `TEXT` |  是 | 键，如 `camera.door.location`   |
| `fact_value` | `TEXT` |  是 | 值                            |
| `fact_type`  | `TEXT` |  是 | `string` / `json` / `number` |
| `scope`      | `TEXT` |  否 | `global` / `device` / `zone` |
| `source`     | `TEXT` |  否 | 来源                           |
| `confidence` | `REAL` |  否 | 置信度                          |
| `created_at` | `TEXT` |  是 | 创建时间                         |
| `updated_at` | `TEXT` |  是 | 更新时间                         |

**说明**：
`facts` 只保存稳定事实，比如设备位置、区域别名、默认策略，不应该塞进临时观察结果。

---

## 12. `ocr_results`

**用途**：保存结构化 OCR 结果，便于回查和二次利用。

| 字段名                     | 类型建议   | 必填 | 说明                                 |
| ----------------------- | ------ | -: | ---------------------------------- |
| `id`                    | `TEXT` |  是 | OCR 主键                             |
| `source_media_id`       | `TEXT` |  是 | 来源媒体 ID                            |
| `source_observation_id` | `TEXT` |  否 | 来源 observation                     |
| `ocr_mode`              | `TEXT` |  是 | `model_direct` / `tool_structured` |
| `raw_text`              | `TEXT` |  否 | 原始全文                               |
| `fields_json`           | `TEXT` |  否 | 结构化字段                              |
| `boxes_json`            | `TEXT` |  否 | 文本框                                |
| `language`              | `TEXT` |  否 | 语言                                 |
| `confidence`            | `REAL` |  否 | 平均置信度                              |
| `created_at`            | `TEXT` |  是 | 时间                                 |

**说明**：
如果你打算把 OCR 当正式能力，而不只是临时模型输出，这张表很值得建。

---

# 三、推荐索引

下面这些索引建议你在项目书里一起写上，方便后续实现时不漏掉：

### `users`

* `UNIQUE(telegram_user_id)`

### `devices`

* `UNIQUE(device_id)`
* `UNIQUE(camera_id)`
* `INDEX(last_seen)`

### `observations`

* `INDEX(camera_id, observed_at DESC)`
* `INDEX(zone_id, observed_at DESC)`
* `INDEX(object_name, observed_at DESC)`
* `INDEX(track_id)`
* `INDEX(source_event_id)`

### `events`

* `INDEX(event_type, event_at DESC)`
* `INDEX(zone_id, event_at DESC)`
* `INDEX(object_name, event_at DESC)`

### `object_states`

* `UNIQUE(object_name, camera_id, zone_id)`

### `zone_states`

* `UNIQUE(camera_id, zone_id)`

### `media_items`

* `INDEX(owner_type, owner_id)`
* `INDEX(created_at DESC)`

### `audit_logs`

* `INDEX(user_id, created_at DESC)`
* `INDEX(device_id, created_at DESC)`
* `INDEX(trace_id)`

### `telegram_updates`

* `UNIQUE(update_id)`
* `INDEX(status, received_at DESC)`

---

# 四、FTS5 建议

因为你前面已经确定是 SQLite + FTS5，这里我建议额外建 3 张 FTS5 虚拟表，用来服务全文搜索：

### 1. `observations_fts`

索引字段建议：

* `object_name`
* `object_class`
* `ocr_text`
* `raw_payload_json`

### 2. `events_fts`

索引字段建议：

* `event_type`
* `summary`
* `payload_json`

### 3. `ocr_results_fts`

索引字段建议：

* `raw_text`
* `fields_json`

SQLite 官方文档说明，FTS5 通过虚拟表工作，适合对文档类文本做高效全文检索；这和你系统里的 OCR 文本、事件摘要、历史搜索需求非常契合。([sqlite.org][3])

---

# 五、我建议你在项目书里直接加的一段总说明

你可以直接复制下面这段：

> 本项目数据层采用 SQLite + FTS5。关系表负责保存 observation、event、state、device、media、audit 等结构化事实；FTS5 虚拟表负责保存 observation 文本、event 摘要、OCR 结果等全文检索内容。Telegram 作为正式入口时，额外保留 `telegram_updates` 表用于 update 去重、处理状态追踪和故障恢复。该设计既满足单机部署的一致性与可维护性，又为后续状态推理、OCR 搜索、历史检索与审计留出统一的数据基础。([sqlite.org][1])

如果你要，我下一条可以继续把这些表**补成 SQL 建表草案**，还是同样按“纯文本代码块，不触发渲染”的方式给你。

[1]: https://sqlite.org/index.html?utm_source=chatgpt.com "SQLite Home Page"
[2]: https://core.telegram.org/bots/api?utm_source=chatgpt.com "Telegram Bot API"
[3]: https://sqlite.org/fts5.html?utm_source=chatgpt.com "SQLite FTS5 Extension"


可以，下面我直接给你一版**可直接复制的 SQLite 建表草案**。
我按“**初始化 PRAGMA → 主表 → 索引 → FTS5 → 触发器/视图**”来排，尽量做到你复制后就能作为第一版 schema 使用。

先说明 3 个和 SQLite 直接相关的前提，方便你放在这节前面：

* SQLite 支持常规 `CREATE TABLE`、主键、默认值和复合约束，这套草案就是按 SQLite 原生语法写的。([sqlite.org][1])
* SQLite 的外键约束**默认不是自动开启**，应用启动后应执行 `PRAGMA foreign_keys = ON;`。([sqlite.org][2])
* FTS5 通过虚拟表实现全文检索；虚拟表不是普通表，不能像普通表那样再单独创建索引或触发器，所以常见做法是在普通内容表上建触发器，同步到 FTS5 表。([sqlite.org][3])

---

## 1）数据库初始化与基础 PRAGMA

```text id="x95sxm"
-- =========================================
-- Vision Butler v5 - SQLite Bootstrap
-- =========================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
PRAGMA busy_timeout = 5000;

-- 可选：如果你明确需要大小写不敏感的 LIKE
-- PRAGMA case_sensitive_like = OFF;
```

**说明文字**：
这部分用于数据库启动初始化。`foreign_keys=ON` 是必须项，因为 SQLite 的外键约束默认关闭；`journal_mode=WAL` 与 `busy_timeout` 则用于提高单机并发读写的可用性。([sqlite.org][2])

---

## 2）主表建表草案

### 2.1 users

```text id="ak0tn8"
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
```

### 2.2 devices

```text id="0bcb2q"
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
```

### 2.3 observations

```text id="a4fhbm"
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
```

### 2.4 events

```text id="jlwmcx"
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
```

### 2.5 object_states

```text id="vixu6w"
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
```

### 2.6 zone_states

```text id="24vfml"
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
```

### 2.7 media_items

```text id="rb4dh7"
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
```

### 2.8 audit_logs

```text id="03mdmo"
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
```

### 2.9 telegram_updates

```text id="ak9vo9"
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
```

### 2.10 notification_rules

```text id="qmtfdz"
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
```

### 2.11 facts

```text id="8g7rk9"
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
```

### 2.12 ocr_results

```text id="i1mp1b"
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
```

---

## 3）推荐索引草案

SQLite 普通表可以正常创建索引；这也是这部分单独写索引的原因。([sqlite.org][1])

```text id="j9m56h"
-- users
CREATE INDEX IF NOT EXISTS idx_users_role
ON users(role);

CREATE INDEX IF NOT EXISTS idx_users_allowed
ON users(is_allowed);

-- devices
CREATE INDEX IF NOT EXISTS idx_devices_status
ON devices(status);

CREATE INDEX IF NOT EXISTS idx_devices_last_seen
ON devices(last_seen DESC);

-- observations
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

-- events
CREATE INDEX IF NOT EXISTS idx_events_time
ON events(event_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_type_time
ON events(event_type, event_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_zone_time
ON events(zone_id, event_at DESC);

CREATE INDEX IF NOT EXISTS idx_events_object_time
ON events(object_name, event_at DESC);

-- object_states
CREATE UNIQUE INDEX IF NOT EXISTS idx_object_states_unique_key
ON object_states(object_name, camera_id, zone_id);

CREATE INDEX IF NOT EXISTS idx_object_states_stale
ON object_states(is_stale, updated_at DESC);

-- zone_states
CREATE UNIQUE INDEX IF NOT EXISTS idx_zone_states_unique_key
ON zone_states(camera_id, zone_id);

CREATE INDEX IF NOT EXISTS idx_zone_states_stale
ON zone_states(is_stale, updated_at DESC);

-- media_items
CREATE INDEX IF NOT EXISTS idx_media_owner
ON media_items(owner_type, owner_id);

CREATE INDEX IF NOT EXISTS idx_media_created_at
ON media_items(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_media_sha256
ON media_items(sha256);

-- audit_logs
CREATE INDEX IF NOT EXISTS idx_audit_user_time
ON audit_logs(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_device_time
ON audit_logs(device_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_trace
ON audit_logs(trace_id);

-- telegram_updates
CREATE INDEX IF NOT EXISTS idx_tg_updates_status_time
ON telegram_updates(status, received_at DESC);

CREATE INDEX IF NOT EXISTS idx_tg_updates_chat_time
ON telegram_updates(chat_id, received_at DESC);

-- notification_rules
CREATE INDEX IF NOT EXISTS idx_notification_rules_user_enabled
ON notification_rules(user_id, is_enabled);

-- facts
CREATE INDEX IF NOT EXISTS idx_facts_scope
ON facts(scope);

-- ocr_results
CREATE INDEX IF NOT EXISTS idx_ocr_results_media
ON ocr_results(source_media_id);

CREATE INDEX IF NOT EXISTS idx_ocr_results_observation
ON ocr_results(source_observation_id);
```

---

## 4）FTS5 草案

FTS5 是 SQLite 的全文检索扩展，通过 `CREATE VIRTUAL TABLE ... USING fts5(...)` 建立。虚拟表属于 SQLite 的 virtual table 机制，因此它和普通表的约束、索引方式不同。([sqlite.org][3])

### 4.1 observations_fts

```text id="vpsqne"
CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts
USING fts5(
    object_name,
    object_class,
    ocr_text,
    raw_payload_json,
    content='observations',
    content_rowid='rowid'
);
```

### 4.2 events_fts

```text id="nq6wq1"
CREATE VIRTUAL TABLE IF NOT EXISTS events_fts
USING fts5(
    event_type,
    summary,
    payload_json,
    content='events',
    content_rowid='rowid'
);
```

### 4.3 ocr_results_fts

```text id="3y4qay"
CREATE VIRTUAL TABLE IF NOT EXISTS ocr_results_fts
USING fts5(
    raw_text,
    fields_json,
    content='ocr_results',
    content_rowid='rowid'
);
```

---

## 5）FTS5 同步触发器草案

因为 FTS5 虚拟表通常需要和普通内容表同步，下面这些触发器可以作为第一版同步方案。这里的做法是在**普通表**上建触发器，把变更同步到 FTS 表；不是在虚拟表上建触发器。([sqlite.org][3])

### 5.1 observations_fts 触发器

```text id="blmm02"
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
```

### 5.2 events_fts 触发器

```text id="kx0j02"
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
```

### 5.3 ocr_results_fts 触发器

```text id="jtgys0"
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
```

---

## 6）更新时间触发器草案

如果你想让 `updated_at` 自动刷新，可以补这组触发器。SQLite 的 `CREATE TABLE` 和触发器语法都原生支持这种用法。([sqlite.org][1])

```text id="0at2yq"
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
```

> 注意：这类触发器在 SQLite 中可用，但如果你后续担心“UPDATE 触发 UPDATE”的维护成本，也可以改成由应用层统一写 `updated_at`。这里先给你的是最省心的数据库侧版本。([sqlite.org][1])

---

## 7）推荐视图草案

### 7.1 world_state_view

```text id="3zw9yo"
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
```

### 7.2 active_notification_rules_view

```text id="hdz4vv"
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
```

### 7.3 recent_device_health_view

```text id="0f5p42"
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

## 8）初始化回填 FTS 的 SQL

如果你先建普通表、后建 FTS 表和触发器，建议跑一次回填：

```text id="fk9nbh"
INSERT INTO observations_fts(rowid, object_name, object_class, ocr_text, raw_payload_json)
SELECT rowid, object_name, object_class, ocr_text, raw_payload_json
FROM observations;

INSERT INTO events_fts(rowid, event_type, summary, payload_json)
SELECT rowid, event_type, summary, payload_json
FROM events;

INSERT INTO ocr_results_fts(rowid, raw_text, fields_json)
SELECT rowid, raw_text, fields_json
FROM ocr_results;
```

---

## 9）我建议你放在项目书里的“建表说明总段落”

你可以直接复制这段：

> 本项目数据库采用 SQLite 作为正式单机数据层，使用常规关系表保存用户、设备、观察、事件、状态、媒体、审计和通知规则，使用 FTS5 虚拟表为 observation、event 和 OCR 结果提供全文检索能力。系统启动时必须显式开启 `PRAGMA foreign_keys = ON`；所有业务表使用应用层生成的文本主键，避免与 SQLite 内部 `rowid` 语义混淆；FTS5 通过普通表触发器同步内容，不直接在虚拟表上定义索引或触发器。该方案兼顾单机部署、全文检索、状态推理和审计追踪需求。([sqlite.org][1])

如果你要，我下一条可以继续补两种内容里的任意一种：
一种是**示例查询 SQL**，比如“查 last_seen”“查当前 state”“查最近事件”“查 stale 对象”；另一种是**Alembic/迁移版本草案**，按 `001_init.sql`、`002_fts.sql` 这种结构给你。

[1]: https://sqlite.org/lang_createtable.html?utm_source=chatgpt.com "CREATE TABLE - SQLite"
[2]: https://sqlite.org/foreignkeys.html?utm_source=chatgpt.com "SQLite Foreign Key Support"
[3]: https://sqlite.org/fts5.html?utm_source=chatgpt.com "SQLite FTS5 Extension"


可以，下面我一次性把两部分都给你：

1. **高频示例查询 SQL**
2. **迁移版本草案**（同时给你 **纯 SQL 版本** 和 **Alembic 版本骨架**）

先给两句你可以直接写进项目书的总说明：

* SQLite 适合你现在这套单机、单节点、SQLite + FTS5 的架构；FTS5 通过虚拟表提供全文检索。([sqlite.org](https://sqlite.org/fts5.html?utm_source=chatgpt.com))
* 如果后续用 Alembic 管迁移，Alembic 的标准模式就是每个 revision 文件里写 `upgrade()` / `downgrade()`；同时它支持 `--sql` 生成离线 SQL 脚本。([alembic.sqlalchemy.org](https://alembic.sqlalchemy.org/en/latest/tutorial.html?utm_source=chatgpt.com)) ([alembic.sqlalchemy.org](https://alembic.sqlalchemy.org/en/latest/offline.html?utm_source=chatgpt.com))

另外有一个很重要的实现提醒：
**SQLite 的复杂表结构变更**，很多时候不能像 PostgreSQL 那样直接 `ALTER TABLE` 完成，官方推荐的安全做法是：**建新表 → 拷贝数据 → 删除旧表 → 重命名新表 → 重建索引/触发器/视图**。所以你的迁移设计最好一开始就接受“重建表是常规手段”这件事。([sqlite.org](https://sqlite.org/lang_altertable.html?utm_source=chatgpt.com))

---

# 第一部分：高频示例查询 SQL

下面这些 SQL 我按“可直接拿去做 repository 方法”的方式写。

---

## 1）查某对象的 last_seen

```text id="lv7w21"
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

---

## 2）优先查 object_state，再回退到 last_seen

```text id="wksgcg"
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

```text id="6s5whu"
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

---

## 3）查某区域最近事件

```text id="l3p2c8"
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

---

## 4）查某对象最近事件

```text id="ci7m1p"
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

---

## 5）查当前 zone_state

```text id="cqqr6v"
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

---

## 6）查 world_state 视图

```text id="3ycjuz"
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

---

## 7）查所有 stale 的对象状态

```text id="sa77dd"
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

---

## 8）按 freshness 规则判断“现在是否 stale”（SQL 侧简版）

```text id="4r7m9d"
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

> 这条 SQL 适合做最基础判断；更完整的 stale 逻辑还是建议放在 `policy_service`，把设备离线、query 实时等级、fallback 需求一起算。

---

## 9）查最近快照或视频

```text id="lxde54"
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

---

## 10）查 observation 对应的媒体

```text id="n4f0nx"
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

---

## 11）查设备最近状态

```text id="h1v0rp"
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

---

## 12）找疑似离线设备

```text id="krn67v"
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

---

## 13）查启用中的通知规则

```text id="yi4lq7"
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

---

## 14）查最近审计日志

```text id="h8o3zn"
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

---

## 15）按 trace_id 查全链路

```text id="6hligd"
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

---

## 16）Telegram update 去重写入

```text id="m4k7ih"
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

---

## 17）标记 Telegram update 处理成功

```text id="qck9jk"
UPDATE telegram_updates
SET
    status = 'processed',
    processed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
    error_message = NULL
WHERE update_id = :update_id;
```

---

## 18）标记 Telegram update 处理失败

```text id="h6blmi"
UPDATE telegram_updates
SET
    status = 'failed',
    processed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
    error_message = :error_message
WHERE update_id = :update_id;
```

---

## 19）OCR 结果查询

```text id="8slgd7"
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

---

## 20）全文检索：按 OCR 文本搜 observation

FTS5 是 SQLite 的全文检索扩展，适合你这里的 OCR 文本、事件摘要、历史搜索。([sqlite.org](https://sqlite.org/fts5.html?utm_source=chatgpt.com))

```text id="p1bw2y"
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

---

## 21）全文检索：按事件摘要搜 recent events

```text id="n4mz3r"
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

---

## 22）查需要发送通知的规则（带冷却窗口）

```text id="y0db6q"
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

