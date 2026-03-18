# 计划书 MCP 缺口补齐执行单（V1）

更新时间：2026-03-18

## 1. 目标

在不改 nanobot 核心、不改业务事实层边界的前提下，补齐计划书中 MCP 侧缺口，并给出“补齐后计划书贴合度”的统一口径。

## 2. 执行前基线（source-verified）

1. `refresh_object_state`、`refresh_zone_state`、`audit_recent_access` 未在 MCP tools 暴露。  
   证据：`README.md` 差异章节；`src/mcp_server/tools/registry.py`（原有工具列表无上述 3 项）。
2. `resource://security/access_scope` 未在 MCP resources 暴露。  
   证据：`README.md` 差异章节；`src/mcp_server/resources/registry.py`（原有资源列表无该 URI）。
3. 状态刷新能力和审计查询能力在服务层已存在，可直接包装。  
   证据：`src/services/state_service.py`（`refresh_object_state`/`refresh_zone_state`）；`src/db/repositories/audit_repo.py`（`list_recent`）。

## 3. 执行项（本次已落地）

- [x] MCP tools 新增 `refresh_object_state`
- [x] MCP tools 新增 `refresh_zone_state`
- [x] MCP tools 新增 `audit_recent_access`
- [x] MCP resource 新增 `resource://security/access_scope`
- [x] `config/access.yaml` 与 `config/runtime/access.yaml` 放通上述 tool/resource
- [x] 集成测试补充新能力枚举与调用断言（`tests/integration/test_mcp_tools.py`）

## 4. 补齐后完成度口径

### 4.1 source-verified

按 `docs/PLAN_CURRENT_AVAILABLE_V1.md` 的“当前未完全达标”口径，MCP 缺口已关闭，当前剩余主要项为：

1. 主动通知扩展到 `state_change/device_status` 与投递执行器
2. 室内全物品识别能力收敛

### 4.2 summary-inference

如果按上述 4 个缺口等权估算：缺口减少 50%。  
对应“计划书贴合度”可从“部分满足（中段）”提升到“部分满足（高段）”，可按约 `80%` 口径对外沟通。

## 5. 验收命令

1. `pytest -q tests/integration/test_mcp_tools.py`
2. `python -m src.mcp_server.server --config-dir config call-tool --name refresh_object_state --args-json '{"object_name":"package","camera_id":"cam-entry-01","zone_id":"entry_door"}'`
3. `python -m src.mcp_server.server --config-dir config call-tool --name refresh_zone_state --args-json '{"camera_id":"cam-entry-01","zone_id":"entry_door"}'`
4. `python -m src.mcp_server.server --config-dir config call-tool --name audit_recent_access --args-json '{"limit":10}'`
5. `python -m src.mcp_server.server --config-dir config read-resource --uri resource://security/access_scope --params-json '{"skill_name":"mcp_console","user_id":"7566115125"}'`
