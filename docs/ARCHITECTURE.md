# Architecture (T0 Skeleton)

## 设计原则
- 模型负责理解与决策；工具负责事实与动作
- 业务真相落在后端服务与数据库，不落在聊天上下文
- 业务能力优先通过 MCP 对 nanobot 暴露

## 分层架构
1. 入口层（Telegram）
- 接收用户消息、媒体与回执

2. 主控层（nanobot）
- 会话管理
- 模型调用
- Skill/MCP 调度

3. 能力层（MCP + Skills）
- tools/resources/prompts 标准暴露
- 调用策略、fallback、时效约束

4. 业务事实层（src/services）
- perception_service
- memory_service
- state_service
- policy_service
- security_guard
- device_service

5. 边缘感知层（edge_device）
- RK3566 采集/检测/跟踪/压缩/缓存/健康上报

6. 数据层（src/db + storage）
- SQLite + FTS5
- 媒体文件索引
- 审计日志

## 关键边界
- Telegram 是正式唯一入口
- nanobot 是主控宿主，但不是业务真相层
- RK3566 前端不承载长期记忆与复杂编排
- object_state / zone_state / freshness / stale / fallback 必须在后端事实层实现
