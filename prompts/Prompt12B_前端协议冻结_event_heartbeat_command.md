# Prompt12B：前端协议冻结（event/heartbeat/command）

## 对应任务
- T13B

## 目标
冻结 edge -> backend 协议字段，避免后续实现阶段反复改 payload。

## 输出
- docs/edge/protocol.md
- schemas/edge_event_envelope.schema.json
- schemas/edge_heartbeat.schema.json
- schemas/edge_command_response.schema.json

## 验收
- event/heartbeat/command response 与计划书字段一致
- 示例 payload 可通过 schema 校验
- 后端入站校验可识别 schema_version 与关键必填字段
