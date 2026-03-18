# 计划书当前可用落地版（V1）

更新时间：2026-03-18（含 5s edge + 30s q8 链路）

## 1. 目标

把 `计划书.md` 的完整目标，收敛成“当前仓库与当前硬件可稳定交付”的版本，作为接下来迭代基线。

## 2. 当前可交付（source-verified）

1. Telegram 作为正式入口可用（通过 nanobot/gateway 接入），并有去重与审计链路。  
   证据：`README.md`、`src/routes_telegram.py`、`src/services/reply_service.py`。
2. nanobot + MCP + Skill 主链已打通，常用工具可稳定调用。  
   证据：`README.md`（Tools/Resources/Prompts 列表）、`src/mcp_server/tools/registry.py`、`skills/`。
3. RK3566 前端职责按计划书边界落地：采集/检测/跟踪/压缩/缓存/心跳/命令响应。  
   证据：`计划书.md` 第 11 章、`edge_device/`、`scripts/start_edge.sh`。
4. 事实层可查询：`object_state / zone_state / world_state`，并有 freshness/stale/fallback。  
   证据：`README.md` 路由清单、`src/services/state_service.py`、`src/services/policy_service.py`。
5. OCR 双通道接口已具备（模型侧 + 工具侧调用入口）。
   证据：`README.md`、`src/routes_ocr.py`、`src/services/ocr_service.py`。
6. 当前计划书“测试与验收”主链对应测试已存在并可执行。
   证据：`计划书.md` 第 19 章、`tests/unit`、`tests/integration`、`tests/e2e`。
7. 主动通知最小闭环已接入真实链路（事件触发 + cooldown + rate limit + 审计）。
   证据：`src/services/notification_service.py`、`src/services/perception_service.py`、`tests/integration/test_device_event_flow.py`。
8. “前端 5 秒检测 + 后端 30 秒 Q8 分析”已接入正式 analysis_requests 主链并可入库追踪。
   证据：`edge_device/compression/event_compressor.py`、`src/services/vision_analysis_service.py`、`src/services/perception_service.py`、`tests/unit/test_event_compressor.py`、`tests/integration/test_device_event_flow.py`。

## 3. MCP 补齐进展（source-verified）

1. 已补齐 `refresh_object_state`、`refresh_zone_state`、`audit_recent_access` MCP tools。  
   证据：`src/mcp_server/tools/registry.py`。
2. 已补齐 `resource://security/access_scope` MCP resource。  
   证据：`src/mcp_server/resources/registry.py`。

## 4. 当前未完全达标（source-verified）

1. 主动通知当前为“事件触发最小闭环”，`state_change/device_status` 规则模板与调度策略仍待扩展。
   证据：`src/services/notification_service.py`（当前仅 `evaluate_event_notifications`）。
2. 室内“全物品完整识别”不属于当前 YOLO 通用模型的保证能力，需数据集/模型继续收敛。
   证据：`docs/edge/model_selection_strategy.md`、`docs/edge/model_ab_test_matrix.md`。

## 5. 当前版本定义（可执行）

V1 定义为：

1. 前端板端稳定供数（事件/快照/clip/heartbeat）优先。
2. 后端负责状态真相层与时效策略。
3. Telegram 问答默认走固定工具链，不依赖“临场自由发挥”。
4. 不把重型多模态常驻放在 RK3566。

## 6. 最小验收清单（当前可用）

1. `./scripts/init_db.sh`
2. `./scripts/stack_ctl.sh start`
3. `EDGE_ACTION=run-once ./scripts/start_edge.sh`
4. `./scripts/smoke_test.sh`
5. `pytest -q tests/integration/test_device_event_flow.py tests/integration/test_object_state_flow.py tests/integration/test_zone_state_flow.py tests/integration/test_stale_fallback_flow.py tests/integration/test_mcp_tools.py`

通过口径：

1. snapshot/clip/heartbeat/event 链路可用。
2. `query_recent_events / get_object_state / evaluate_staleness` 返回结构稳定。
3. 关键动作可在审计或日志中追踪。

## 7. 下一步（V2）

1. 扩展主动通知到 `state_change/device_status` 并加回压策略。
2. 将通知投递从“后端决策结果”接入 Telegram 发送执行器（nanobot/gateway）。
3. 基于真实室内场景继续收敛检测模型（优先低成本数据收集+微调）。

## 8. 完成度评估（截至 2026-03-18）

1. 计划书当前可用版（V1）完成度：**约 90%**（source-verified）。
2. 已完成项：
   `Telegram 主入口`、`MCP 主链`、`state/policy 真相层`、`主动通知最小闭环`、`5s edge + 30s q8 分析链路`。
3. 剩余差距（影响“完整计划书 100%”）：
   `主动通知扩展到 state_change/device_status`、`室内全物品识别能力继续收敛`。
4. 本次回归证据：
   `pytest -q tests/unit/test_vision_analysis_service.py tests/integration/test_device_event_flow.py tests/unit/test_event_compressor.py tests/integration/test_edge_event_quality.py tests/unit/test_edge_protocol_schemas.py` -> `19 passed`。
