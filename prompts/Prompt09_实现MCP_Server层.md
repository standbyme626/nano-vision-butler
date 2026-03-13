<!-- source: 提示词.md | id: s59gkl -->
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
