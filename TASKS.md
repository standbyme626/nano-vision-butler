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
状态：DONE
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
状态：DONE
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
状态：DONE
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
状态：DONE
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
状态：DONE
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
状态：DONE
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
状态：DONE
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
状态：DONE
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

## T7-Hotfix 摄像头可用性修复（SQLite 线程 + runtime 配置）
状态：DONE
优先级：P1
依赖：T7

### 目标
修复摄像头“看起来在线但命令不可用”的关键问题，恢复心跳与命令链路可用性。

### 输出
- src/db/session.py（SQLite 线程切换兼容）
- src/services/perception_service.py（ingest_event 刷新设备在线状态）
- config/runtime/cameras.yaml（修复 RTSP 地址）
- scripts/start_edge.sh（修复默认后端地址并支持位置参数 action）
- tests/unit/test_db_session.py（线程回归测试）
- tests/integration/test_device_event_flow.py（事件刷新在线状态回归测试）

### 验收
- /device/status 返回 `effective_status=online`（心跳后）
- /device/command/take-snapshot 可成功
- /device/command/get-recent-clip 可成功
- pytest 全量通过

---

## T8 OCR 双通道
状态：DONE
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
状态：DONE
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
状态：DONE
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
状态：DONE
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

## T11-Hotfix 模型与密钥切换指引 + 默认模型更新
状态：DONE
优先级：P1
依赖：T11

### 目标
将运行默认模型切换到 `qwen3.5-35b-a3b`，并在 README 明确说明模型与密钥的修改位置和步骤。

### 输出
- `config/runtime/nanobot.config.json`（prod 模型更新）
- `config/runtime/nanobot.dev.config.json`（dev 模型更新）
- `scripts/switch_ollama_ctx.sh`（dashscope 档位默认模型更新）
- `scripts/apply_runtime_config.sh`（runtime 渲染默认模型更新）
- `README.md`（新增模型/密钥更换说明）

### 验收
- prod/dev runtime 默认模型均为 `qwen3.5-35b-a3b`
- README 可直接指引用户定位并替换 `model/apiBase/apiKey`
- 相关脚本切换/渲染默认值不再回落到旧模型

---

## T12 Telegram 正式交互链路
状态：DONE
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

## T12-Hotfix Telegram 重复消费防护
状态：DONE
优先级：P1
依赖：T12

### 目标
避免同一个 Telegram bot token 被多 gateway 进程同时消费，导致会话重复执行与重复回复。

### 输出
- `scripts/start_gateway.sh` 增加“同 token 单实例”启动前检查
- `scripts/apply_runtime_config.sh` 的 dev token 回退逻辑改为独立默认值
- `README.md` 增加重复回复排查说明

### 验收
- 当已有 gateway 使用同 token 运行时，第二个 gateway 启动会被拒绝
- `TELEGRAM_BOT_TOKEN_DEV` 缺省时不再自动复用 `TELEGRAM_BOT_TOKEN`
- 相关集成测试不回归

---

## T12-Hotfix MCP kwargs 参数兼容
状态：DONE
优先级：P1
依赖：T12

### 目标
兼容 nanobot 通过 `kwargs`（对象或 JSON 字符串）封装的 MCP 工具入参，避免 `camera_id/device_id` 丢失导致工具误报必填缺失。

### 输出
- `src/mcp_server/http_server.py` 增加 `kwargs` 解包与合并逻辑
- `tests/unit/test_mcp_http_server.py` 新增 `kwargs` 字符串/对象兼容用例

### 验收
- `kwargs='{\"camera_id\":\"...\"}'` 能被正确传入工具
- `kwargs={...}` 能被正确传入工具
- MCP 相关单测与集成测试通过

---

## T13 RK3566 前端最小正式实现
状态：DONE
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

## T13A 板级 bring-up 与基线测量
状态：DONE（2026-03-14）
优先级：P1
依赖：T13

### 目标
在真实 RK3566 板端建立可复现的采集与负载基线，作为后续模型与媒体链路的前置条件。

### 输出
- docs/edge/baseline_report.md
- scripts/edge_baseline_capture.sh
- scripts/edge_baseline_metrics.sh

### 验收
- 摄像头节点可稳定枚举
- 分辨率/FPS/像素格式基线可复现
- 连续 30-60 分钟采集无崩溃/无持续掉流
- CPU/内存/NPU（若可读）指标有基线记录

---

## T13B 前端协议冻结（event/heartbeat/command）
状态：DONE（2026-03-14）
优先级：P1
依赖：T13A

### 目标
冻结 edge -> backend 协议，避免后续实现阶段反复改字段。

### 输出
- docs/edge/protocol.md
- schemas/edge_event_envelope.schema.json
- schemas/edge_heartbeat.schema.json
- schemas/edge_command_response.schema.json

### 验收
- event/heartbeat/command response 字段与计划书一致
- 示例 payload 可通过 schema 校验
- 后端入站校验可识别 schema_version 与关键必填字段

---

## T13C 真实采集层替换（V4L2/GStreamer）
状态：DONE（2026-03-14）
优先级：P1
依赖：T13B

### 目标
以真实采集管线替换 StubCamera，实现可恢复的板端采图能力。

### 输出
- edge_device/capture/camera.py（真实实现）
- edge_device/capture/v4l2_camera.py（或 gstreamer_camera.py）
- tests/unit/test_edge_capture.py

### 验收
- 支持 source/fps/resolution/pixel_format 配置
- 采集失败可重试并输出可观测错误
- 连续采集稳定运行

---

## T13D 真实 Snapshot 落地（JPEG）
状态：DONE（2026-03-14）
优先级：P1
依赖：T13C

### 目标
把占位 snapshot 文件替换为真实 JPEG，先打通“可验图”的最短路径。

### 输出
- edge_device/api/server.py（_store_snapshot 真实编码）
- tests/integration/test_edge_snapshot_real_media.py
- docs/edge/snapshot_contract.md

### 验收
- snapshot 文件为真实 JPEG，可被标准图像工具读取
- 宽高与实际帧一致
- snapshot URI 回传后端并可落库索引

---

## T13D-Hotfix 快照黑屏修复（真实帧优先 + 低依赖抓拍）
状态：DONE（2026-03-14）
优先级：P1
依赖：T13D

### 目标
修复 RK3566 端快照黑屏，确保 `take-snapshot` 输出真实相机画面，而不是占位黑底图。

### 输出
- edge_device/capture/camera.py（`CapturedFrame` 增加 `image_path`）
- edge_device/capture/v4l2_camera.py（优先抓取真实 JPEG；无 ffmpeg 时支持 v4l2 MJPG 直出）
- edge_device/api/server.py（写快照优先使用真实帧文件，避免依赖缺失时退化黑底）
- edge_device/inference/rknn_detector.py（修复空 `EDGE_RKNN_MODEL_PATH` 被解析为 `.`）
- tests/unit/test_edge_capture.py
- tests/unit/test_edge_runtime.py
- tests/unit/test_rknn_detector.py

### 验收
- RK3566 实机 `take-snapshot` 成功返回且图像非黑屏
- `run-once` 能产出有效 `snapshot_uri` 且链路不中断
- 相关单测通过

---

## T13E 命令闭环最小打通（替换后端 StubEdgeDeviceAdapter）
状态：DONE（2026-03-14）
优先级：P1
依赖：T13D

### 目标
让 /device/command/take-snapshot 与 /device/command/get-recent-clip 触发真实 edge 执行器，而非后端 stub。

### 输出
- src/services/device_service.py（接入真实 edge command client）
- src/services/edge_command_client.py
- tests/integration/test_device_command_edge_bridge.py

### 验收
- 后端命令可远程触发 edge 执行
- command_id/trace_id 可全链路追踪
- 不再依赖 StubEdgeDeviceAdapter 生成媒体结果

---

## T13F RKNN 检测模型部署（主检测）
状态：DONE（2026-03-14）
优先级：P1
依赖：T13E

### 目标
接入 RKNN 主检测模型，替换 LightweightDetector stub。

### 输出
- edge_device/inference/rknn_detector.py
- scripts/rknn/export_to_rknn.sh
- scripts/rknn/run_infer_benchmark.sh
- docs/edge/model_deploy.md

### 验收
- 板端可输出真实 bbox/class/confidence
- model_version 与实际模型一致
- 推理失败可降级并记录错误

---

## T13F-Hotfix 默认模型切换为轻量 INT8 主检测
状态：DONE（2026-03-14）
优先级：P1
依赖：T13F

### 目标
将 edge 运行时默认 RKNN 模型切换为更快的 `main_detector_n_int8.rknn`，减少每次手工传参并提升默认性能。

### 输出
- edge_device/inference/rknn_detector.py（默认模型路径切换）
- scripts/start_edge.sh（默认 `EDGE_RKNN_MODEL_PATH` 切换）
- scripts/rknn/export_to_rknn.sh（示例更新）
- scripts/rknn/run_infer_benchmark.sh（示例更新）
- docs/edge/model_deploy.md（默认模型与命令示例更新）
- tests/unit/test_rknn_detector.py（默认路径断言更新）

### 验收
- 不传 `EDGE_RKNN_MODEL_PATH` 时默认加载 `./models/rknn/main_detector_n_int8.rknn`
- `run-once` 启动日志显示默认模型路径正确
- 相关单测通过，RK3566 实机可运行

---

## T13G 跟踪/Zone/事件压缩质量提升
状态：DONE（2026-03-14）
优先级：P1
依赖：T13F-Hotfix

### 目标
提升 event 质量与稳定性，减少抖动和无效上报。

### 输出
- edge_device/tracking/tracker.py（真实策略）
- edge_device/compression/event_compressor.py（策略增强）
- tests/integration/test_edge_event_quality.py

### 验收
- track_id 在连续帧下稳定
- zone_id 映射正确
- event 压缩策略可配置（阈值/去重/节流）

---

## T13H Recent Clip 真实化（MP4 + ring buffer）
状态：DONE（2026-03-14）
优先级：P1
依赖：T13G

### 目标
产出真实可播放 clip，并与 ring buffer 策略协同。

### 输出
- edge_device/api/server.py（_assemble_clip 真实编码）
- edge_device/cache/ring_buffer.py（策略增强）
- tests/integration/test_edge_recent_clip_real_media.py

### 验收
- clip 为真实 MP4，可播放
- 片段长度与请求时长匹配
- 缓存淘汰策略可观测、可复现

---

## T13I 可靠性/安全/压测验收
状态：DONE（2026-03-14）
优先级：P1
依赖：T13H

### 目标
固化回压与退化策略，完成可交付级稳定性与安全验收。

### 输出
- docs/edge/reliability_plan.md
- docs/edge/soak_test_report.md
- tests/integration/test_edge_reliability_flow.py
- scripts/edge_soak_test.sh

### 验收
- take_snapshot 成功率 >= 99%，P95 响应时间有明确阈值
- get_recent_clip 成功率 >= 98%，P95 生成时长有明确阈值
- event captured_at 到后端入库 P95 延迟有明确阈值
- heartbeat 连续 24h 无误报抖动
- 至少一次断网恢复演练通过并可补传关键事件
- 回压/退化策略生效：优先保 heartbeat 与关键事件

---

## T13-Hotfix 边缘地址与设备信息修正
状态：DONE（2026-03-14）
优先级：P2
依赖：T13I

### 目标
将边缘链路默认地址与设备信息更新为当前真实网络信息，避免测试和部署时使用错误地址。

### 输出
- AGENTS.md（新增本地地址备忘）
- scripts/start_edge.sh（默认 EDGE_BACKEND_BASE_URL）
- scripts/stack_ctl.sh（默认 EDGE_BACKEND_BASE_URL）
- edge_device/api/server.py（load_config_from_env 默认 backend_base_url）
- config/cameras.yaml / config/runtime/cameras.yaml（RTSP 地址）

### 验收
- 默认 backend 地址为 `http://100.92.134.46:8000`
- 默认 RTSP 地址为 `rtsp://100.103.105.108/live`
- AGENTS.md 含用户指定的 tailscale/SSH 备忘信息

---

## T14 安全与访问控制落地
状态：DONE
优先级：P1
依赖：T9, T10, T11, T12

### 目标
实现统一的 security_guard / access_policy，使用户、设备、tools、resources、media 访问都受控并可审计。

### 输出
- src/security/security_guard.py
- src/security/access_policy.py
- src/schemas/security.py
- tests/unit/test_security_guard.py
- tests/integration/test_access_control_flow.py

### 验收
- 非 allowlist 用户会被拒绝
- 非 allowlist 设备会被拒绝
- Skill 调未授权 tool 会被拒绝
- 读取未授权 resource/media 会被拒绝
- 所有拒绝行为有 audit 记录

---

## T15 测试矩阵落地
状态：DONE
优先级：P1
依赖：T6, T7, T8, T9, T11, T12, T14

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

## T15-Hotfix 测试文档拆分与必要性分析
状态：DONE
优先级：P2
依赖：T15

### 目标
在不修改源文档的前提下，把 `测试.md` 拆成可执行、可复盘的边缘测试文档，并完成最小回归验证。

### 输出
- docs/edge/testing_index.md
- docs/edge/model_selection_strategy.md
- docs/edge/model_ab_test_matrix.md
- docs/edge/test_necessity_analysis.md
- PROGRESS_CHECKLIST.md（A/B 对应项打勾）

### 验收
- `测试.md` 保留原文，不做覆盖修改
- 拆分后文档满足“一文一职责”，可直接按步骤执行
- 至少完成一组 edge 相关回归测试并记录结果
- TASKS 与 PROGRESS_CHECKLIST 状态同步

---

## T16 最终联调收尾与交付
状态：DONE
优先级：P1
依赖：T15

### 目标
在不重构核心边界的前提下完成最终交付检查，确保仓库可运行、可验收、可交接。

### 输出
- 交付检查清单（目录/文档/脚本/测试）
- 运行与启动说明补齐
- 当前可运行范围与 stub 范围说明

### 验收
- 仓库结构完整
- 启动脚本存在并可说明启动顺序
- smoke test 可运行
- 文档可指导首次启动
- 未完成部分有诚实标注

---

## T17 轻前端重后端改造第一阶段
状态：DONE（2026-03-14）
优先级：P1
依赖：T16

### 目标
将 RK3566 收敛为轻实时感知端，把 OCR 重分析迁移到后端触发执行，形成“事件提示 + 后端执行”的第一阶段闭环。

### 输出
- docs/edge/light_edge_heavy_backend_refactor.md
- edge_device/compression/event_compressor.py（analysis_requests 输出）
- src/services/perception_service.py（backend OCR analysis hook）
- src/dependencies.py（OCRService 注入 perception）
- schemas/edge_event_envelope.schema.json（analysis 字段扩展）
- docs/edge/protocol.md（协议说明同步）
- tests/integration/test_device_event_flow.py（后端 OCR 触发集成测试）
- tests/integration/test_edge_event_quality.py（edge analysis 请求测试）
- tests/unit/test_edge_protocol_schemas.py（schema 扩展校验）

### 验收
- edge event payload 可携带 analysis_requests 并通过 schema 校验
- ingest_event 收到分析请求后可触发 OCR 并写入 ocr_results
- 审计日志存在 perception_backend_analysis 记录
- 现有 heartbeat/event 主链路兼容

---

## T17-Hotfix 日志时间统一为本地时区
状态：DONE（2026-03-14）
优先级：P2
依赖：T17

### 目标
将运行日志与运行时时间字段统一为本地时间显示，减少 UTC 与本地时间换算成本。

### 输出
- `src/db/session.py`（时间格式支持 `VISION_BUTLER_TIME_MODE=local|utc`）
- `edge_device/capture/camera.py`（edge 统一时间函数 + 本地文件名时间戳）
- `edge_device/health/heartbeat.py`（复用 edge 统一时间函数）
- `edge_device/compression/event_compressor.py`（复用 edge 统一时间函数）
- `edge_device/api/server.py`（clip/pending 文件名时间戳与配置保持一致）
- `scripts/start_backend.sh`（默认 `VISION_BUTLER_TIME_MODE=local` + `TZ=Asia/Shanghai`）
- `scripts/start_edge.sh`（默认 `VISION_BUTLER_TIME_MODE=local` + `TZ=Asia/Shanghai`）
- `scripts/stack_ctl.sh`（补充时间相关环境变量说明）

### 验收
- 通过启动脚本运行时，日志时间按本地时区输出（`+08:00`）
- 可通过 `VISION_BUTLER_TIME_MODE=utc` 切回 UTC 兼容模式
- 相关回归测试通过

---

## T17-Hotfix 摄像头 capture 限制解除（强制 MJPG 防回落）
状态：DONE（2026-03-15）
优先级：P1
依赖：T17-Hotfix

### 目标
消除 RK3566 实机采集链路因像素格式回落导致的低帧率瓶颈，避免 `1280x720` 在 `YUYV` 下被锁到低采集速率。

### 输出
- `scripts/start_edge.sh`（新增启动时 `v4l2-ctl` 自动调优）
- `docs/EDGE_DEVICE.md`（新增采集调优参数说明）
- `docs/edge/model_ab_test_matrix.md`（公共环境改为 `MJPG + 30fps`）

### 验收
- RK3566 实机 `v4l2-ctl --list-formats-ext` 可确认 `1280x720@30fps` 的 MJPG 能力
- 启动 edge 时可自动执行 `set-fmt-video + set-parm`，日志可见调优结果
- 实测 `capture` 从 `~200ms (YUYV@720p)` 降到 `~33ms (MJPG@720p)`

---

## T17-Hotfix 默认模型切换 YOLOv8n INT8 + 采集推理并行流水线
状态：DONE（2026-03-15）
优先级：P1
依赖：T17-Hotfix 摄像头 capture 限制解除（强制 MJPG 防回落）

### 目标
将 RK3566 上线默认模型切换为 `YOLOv8n INT8`，并在 edge 端启用“采集预取 + 推理消费”的并行流水线，减少串行等待。

### 输出
- `edge_device/inference/rknn_detector.py`（默认模型改为 `yolov8n_official_i8_rk3566.rknn`）
- `scripts/start_edge.sh`（默认模型路径 + 并行参数 `EDGE_CAPTURE_PARALLEL*`）
- `edge_device/api/server.py`（并行采集配置注入）
- `edge_device/capture/camera.py`（`LatestFramePrefetchCamera`）
- `tests/unit/test_edge_capture.py` / `tests/unit/test_rknn_detector.py`（回归测试）

### 验收
- 不传 `EDGE_RKNN_MODEL_PATH` 时默认加载 `./models/rknn/yolov8n_official_i8_rk3566.rknn`
- `EDGE_CAPTURE_PARALLEL=1` 时，runtime 启动日志可见并行采集启用
- 相关单测通过，RK3566 实机启动链路可运行

---

## T17-Hotfix 切换 Rockchip 优化版 YOLOv8n INT8 并完成实机复测
状态：DONE（2026-03-15）
优先级：P1
依赖：T17-Hotfix 默认模型切换 YOLOv8n INT8 + 采集推理并行流水线

### 目标
将 RK3566 默认检测模型从通用导出版本切换为 `airockchip/ultralytics_yolov8 + rknn_model_zoo` 链路的优化版 `YOLOv8n INT8`，并完成 RK3566 实机跑通验证。

### 输出
- `edge_device/inference/rknn_detector.py`（默认模型改为 `yolov8n_rockchip_opt_i8_rk3566.rknn`）
- `scripts/start_edge.sh`（默认 `EDGE_RKNN_MODEL_PATH` 切换到 Rockchip 优化模型）
- `scripts/rknn/export_to_rknn.sh`（支持 INT8 量化、`RKNN_DATASET_PATH`、onnx 1.20 兼容补丁）
- `tests/unit/test_rknn_detector.py`（默认路径与模型版本断言同步）
- `docs/edge/model_deploy.md`（导出与板端基准命令切换为 Rockchip 优化模型）

### 验收
- 不传 `EDGE_RKNN_MODEL_PATH` 时默认加载 `./models/rknn/yolov8n_rockchip_opt_i8_rk3566.rknn`
- `scripts/start_edge.sh run-once` 在 RK3566 实机可成功加载并返回 `model_version=yolov8n_rockchip_opt_i8_rk3566`
- 相关单测通过，导出脚本可执行 INT8 导出流程

---

## T17-Hotfix 分段性能优化与横向对比口径统一
状态：DONE（2026-03-15）
优先级：P1
依赖：T17-Hotfix 切换 Rockchip 优化版 YOLOv8n INT8 并完成实机复测

### 目标
把 `run_once` 的性能拆成可稳定对比的分段指标，并支持“上传异步化 + 快照可关闭”的压测模式，保证横向对比同口径。

### 输出
- `edge_device/api/server.py`（新增 `timings_ms` 分段字段，支持 `EDGE_BACKEND_POST_MODE`、`EDGE_BACKEND_POST_QUEUE_MAX`、`EDGE_RUN_ONCE_SNAPSHOT_MODE`）
- `scripts/start_edge.sh`（新增上述开关与日志打印）
- `scripts/rknn/run_infer_benchmark.sh`（改为单进程循环，输出 `avg_capture_ms`、`avg_detector_infer_ms`、`avg_total_ms` 等均值）
- `edge_device/capture/v4l2_camera.py`（`v4l2` 路径改为单次 snapshot，去除重复预抓拍开销）
- `tests/unit/test_edge_runtime.py`（异步上传与 run_once 分段字段回归）
- `tests/unit/test_rknn_detector.py`（RKOPT 9 路输出解码回归，`cv2` 缺失时 PIL 兜底）
- `logs/rk3566_bench_20260315/*.log`（RK3566 实机横向对比留档）

### 验收
- `run_once` 响应包含 `timings_ms.capture_ms/detector_infer_ms/total_ms`
- `EDGE_BACKEND_POST_MODE=async` 下 `run_once` 可返回 `event_queued=true`
- 基准脚本输出包含 `avg_capture_ms` 与 `avg_total_ms`
- RK3566 实机端到端性能较优化前（~2.4 FPS）有明确提升（~4.6~4.8 FPS）
- 单测通过：`pytest -q tests/unit/test_edge_capture.py tests/unit/test_rknn_detector.py tests/unit/test_edge_runtime.py`

---

## T17-Hotfix 当前环境分析链路改造（抓拍→场景描述→结构化结论）
状态：DONE（2026-03-15）
优先级：P1
依赖：T17-Hotfix 分段性能优化与横向对比口径统一

### 目标
将 Telegram 文本“当前环境”查询从“仅历史事件拼接”升级为“实时抓拍 + 场景工具描述 + 结构化结论”，并保留抓拍失败时的历史回退路径。

### 输出
- `src/services/reply_service.py`（新增 scene intent 分流；文本场景链路改为 `take_snapshot -> describe_scene -> structured response`；失败回退 `get_world_state + query_recent_events`）
- `config/access.yaml`（`mcp_tool_allowlist` 与 `tool_allowlist_per_skill.telegram` 增加 `describe_scene`）
- `config/runtime/access.yaml`（同上）
- `tests/e2e/test_current_scene_query.py`（断言更新为结构化结论格式）

### 验收
- 发送“现在门口什么情况/分析当前环境”等文本时，返回内容包含结构化结论、快照信息、场景状态与最近事件
- `take_snapshot` 失败时不会整条请求失败，返回历史证据回退结果
- 回归通过：`pytest -q tests/e2e/test_current_scene_query.py tests/integration/test_telegram_message_flow.py tests/e2e/test_take_snapshot_command.py`

---

## T17-Hotfix 修复 take_snapshot 外键失败（camera_id/device_id 兼容 + 审计防 FK）
状态：DONE（2026-03-15）
优先级：P1
依赖：T17-Hotfix 当前环境分析链路改造（抓拍→场景描述→结构化结论）

### 目标
修复“当前环境”链路中 `take_snapshot` 在设备标识混用时触发的 `FOREIGN KEY constraint failed`，保证抓拍可成功，且拒绝审计日志不再因非法 `device_id` 失败。

### 输出
- `src/services/device_service.py`
  - `_resolve_device` 兼容 `device_id` 误传 `camera_id`（按 camera 反查设备）
  - 失败审计前执行 `device_hint -> device_id` 归一化，未知设备写 `null`
  - `take_snapshot/get_recent_clip` deny 审计 `meta` 增加 `device_hint`
- `tests/unit/test_device_service.py`
  - 新增 camera_id/device_id 混用成功抓拍测试
  - 新增未知设备拒绝审计不触发 FK 测试

### 验收
- `POST /device/command/take-snapshot` 传 `{"device_id":"cam-entry-01"}` 返回成功
- 不存在设备标识时返回 `DEVICE_NOT_FOUND`，且不再抛出 `FOREIGN KEY constraint failed`
- 通过：`pytest -q tests/unit/test_device_service.py`
- 通过：`pytest -q tests/e2e/test_current_scene_query.py tests/e2e/test_take_snapshot_command.py tests/integration/test_telegram_message_flow.py`
- 实链路复测：`nanobot agent` 触发 `take_snapshot({"device_id":"cam-entry-01"})` 成功（会话 `cli_env-now-fix`）

---

## T17-Hotfix RKNN 标签对齐 COCO80（模型分类映射修正）
状态：DONE（2026-03-15）
优先级：P1
依赖：T17-Hotfix 修复 take_snapshot 外键失败（camera_id/device_id 兼容 + 审计防 FK）

### 目标
修复 RKNN 模型类别数（80 类）与默认标签（3 类）不一致的问题，避免类别名映射错误。

### 输出
- `scripts/start_edge.sh`
  - 默认 `EDGE_RKNN_LABELS` 从 `person,package,car` 改为 COCO80 顺序
- `edge_device/inference/rknn_detector.py`
  - 增加 `COCO80_LABELS` 常量
  - `RKNNDetectorConfig.labels` 默认值改为 COCO80
  - `create_rknn_detector_from_env` 默认标签改为 COCO80
  - `_parse_labels` 在空输入时回退 COCO80（不再回退单类 `person`）
- `tests/unit/test_rknn_detector.py`
  - 新增空标签环境变量回退 COCO80 断言（长度 80）
- `docs/edge/model_deploy.md` / `docs/edge/model_ab_test_matrix.md`
  - 默认标签说明与示例同步为 COCO80

### 验收
- `pytest -q tests/unit/test_rknn_detector.py` 通过
- `pytest -q tests/unit/test_edge_runtime.py tests/unit/test_edge_capture.py` 通过
- RK3566 实机（`/root/.venv_rknn/bin/python`）`run-once` 输出：
  - `model_version=yolov8n_rockchip_opt_i8_rk3566`
  - `detector_error=null`
  - `RKNN labels` 日志为 COCO80 列表

---

## T18 计划书当前可用版落地（文档与验收口径收敛）
状态：DONE（2026-03-18）
优先级：P1
依赖：T17-Hotfix RKNN 标签对齐 COCO80（模型分类映射修正）

### 目标
把 `计划书.md` 的完整目标收敛为“当前硬件 + 当前仓库可稳定交付”的执行基线，统一后续推进口径。

### 输出
- `docs/PLAN_CURRENT_AVAILABLE_V1.md`
  - 明确“当前可交付能力 / 当前缺口 / 最小验收清单 / V2 下一步”
- `README.md`
  - 新增“计划书当前可用版”入口说明
- `PROGRESS_CHECKLIST.md`
  - 同步 A/B 勾选记录，避免任务状态漂移

### 验收
- 可直接回答“当前计划书做到哪一层”并给出固定证据路径
- 研发、测试、部署按同一份 V1 清单执行，不再口径漂移
- 文档中明确区分“当前可交付”与“下一阶段补齐项”

---

## T19 MCP 计划书缺口补齐（tools/resources + 配置 + 验收文档）
状态：DONE（2026-03-18）
优先级：P1
依赖：T18

### 目标
补齐计划书中已识别的 MCP 缺口，并把“补齐后计划书贴合度”固化成可执行文档。

### 输出
- `src/mcp_server/tools/registry.py`
  - 新增 `refresh_object_state`
  - 新增 `refresh_zone_state`
  - 新增 `audit_recent_access`
- `src/mcp_server/resources/registry.py`
  - 新增 `resource://security/access_scope`
- `config/access.yaml` 与 `config/runtime/access.yaml`
  - 同步放通新 tool/resource
- `tests/integration/test_mcp_tools.py`
  - 新增工具/资源枚举与调用断言
- `docs/PLAN_MCP_GAP_EXECUTION_V1.md`
  - 固化“前后差异 + 完成度口径 + 验收命令”

### 验收
- `pytest -q tests/integration/test_mcp_tools.py` 通过
- `pytest -q tests/integration/test_access_control_flow.py` 通过
- `python -m src.mcp_server.server --config-dir config list` 可见新增 tool/resource
- `call-tool refresh_* / audit_recent_access` 与 `read-resource resource://security/access_scope` 可返回成功结构

---

## T20 主动通知最小闭环落地（规则触发 + 去重节流 + 审计）
状态：DONE（2026-03-18）
优先级：P1
依赖：T19

### 目标
把 `notification_rules` 从“仅有表结构”推进到“真实事件链路可执行的通知决策闭环”。

### 输出
- `src/db/repositories/notification_rule_repo.py`
  - 活跃规则读取（`active_notification_rules_view`）
  - `last_triggered_at` 更新
  - 每小时触发次数统计
- `src/services/notification_service.py`
  - 规则匹配（`event_type/object_name/zone_id/min_importance`）
  - cooldown 与 `max_per_hour` 节流
  - 通知决策审计（`notification_dispatch`）
- `src/services/perception_service.py`
  - `ingest_event` 返回 `notifications` 结果
- `tests/integration/test_device_event_flow.py`
  - 新增“首条触发 + 第二条 cooldown 抑制 + 审计落库”用例
- `docs/NOTIFICATION_LOOP_V1.md`
  - 本次闭环范围、返回结构、验收命令

### 验收
- `pytest -q tests/integration/test_device_event_flow.py` 通过
- `pytest -q tests/integration/test_access_control_flow.py tests/integration/test_mcp_tools.py` 通过
- `/device/ingest/event` 响应包含 `notifications` 字段并体现 `triggered/skipped` 结果
- `audit_logs` 中存在 `action='notification_dispatch'` 的 allow/deny 记录

---

## T21 5秒边端人体检测 + 30秒Q8后端分析链路落地
状态：DONE（2026-03-18）
优先级：P1
依赖：T20

### 目标
将“前端每 5 秒一次检测与上报”和“后端 Q8 图像分析每 30 秒一次”接入同一正式链路，并完成文档与测试验收。

### 输出
- `edge_device/compression/event_compressor.py`
  - 新增 `vision_q8_describe` analysis request 生成
  - 新增按 camera 维度 `EDGE_ANALYSIS_Q8_INTERVAL_SEC=30` 节流
  - 保持 edge 主循环 `EDGE_INTERVAL_SEC=5` 口径
- `src/services/vision_analysis_service.py`
  - 新增 Q8 后端分析服务（stub/ollama 双模式）
  - 结果写入 `events`，动作写入 `audit_logs`
- `src/services/perception_service.py` + `src/dependencies.py`
  - analysis dispatcher 接入 `vision_q8_describe`
- `schemas/edge_event_envelope.schema.json` + `docs/edge/protocol.md`
  - 协议枚举新增 `vision_q8_describe`
- `scripts/start_edge.sh` + `scripts/start_backend.sh`
  - 新增 Q8 相关环境变量并打印运行参数
- `tests/unit/test_event_compressor.py`
  - 新增 Q8 30s 节流单测
- `tests/unit/test_vision_analysis_service.py`
  - 新增 Q8 服务入库与审计单测
- `tests/integration/test_device_event_flow.py`
  - 新增 `vision_q8_describe` 端到端分发用例
- `tests/integration/test_edge_event_quality.py` / `tests/unit/test_edge_protocol_schemas.py`
  - 新增 Q8 request 协议与压缩行为用例

### 验收
- `pytest -q tests/unit/test_vision_analysis_service.py tests/integration/test_device_event_flow.py tests/unit/test_event_compressor.py tests/integration/test_edge_event_quality.py tests/unit/test_edge_protocol_schemas.py` 通过
- `analysis_requests` 中可见 `vision_q8_describe`
- 后端入库存在 `event_type='vision_q8_described'` 记录
- `audit_logs` 存在 `action='vision_q8_describe'` 记录

---

## 推荐并行方式

### A 线：数据与事实层
- T1
- T2
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
- T14

### D 线：边缘层
- T13A
- T13B
- T13C
- T13D
- T13E
- T13F
- T13F-Hotfix
- T13G
- T13H
- T13I

### 收尾线：测试与验收
- T15
- T16
