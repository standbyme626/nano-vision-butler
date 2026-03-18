# 主动通知闭环（V1）

更新时间：2026-03-18

## 1. 本次范围（source-verified）

1. 触发入口：`/device/ingest/event` 中 `promoted_event` 路径。  
2. 规则来源：`active_notification_rules_view`。  
3. 规则匹配字段：`event_type/object_name/zone_id/min_importance`。  
4. 去重节流：`cooldown_sec` + `policies.notifications.max_per_hour`。  
5. 审计：`audit_logs.action = notification_dispatch`，记录 allow/deny 与原因。

## 2. 代码位置

- `src/db/repositories/notification_rule_repo.py`
- `src/services/notification_service.py`
- `src/services/perception_service.py`
- `src/dependencies.py`
- `tests/integration/test_device_event_flow.py`

## 3. 返回结构（ingest_event）

`/device/ingest/event` 响应新增 `notifications`：

- `requested`：本次评估规则数
- `triggered`：触发数
- `skipped`：跳过数
- `deliveries`：触发通知清单（含 `telegram_chat_id` 和消息）
- `skipped_reasons`：未触发原因（如 `cooldown_active`）

## 4. 验收命令

1. `pytest -q tests/integration/test_device_event_flow.py`
2. `pytest -q tests/integration/test_access_control_flow.py tests/integration/test_mcp_tools.py`

## 5. 已知边界（summary-inference）

1. 当前是“事件触发最小闭环”，还未覆盖 `state_change/device_status`。  
2. 当前输出的是“通知决策结果 + 审计”，真正 Telegram 投递执行仍需接入 nanobot/gateway 发送路径。  
