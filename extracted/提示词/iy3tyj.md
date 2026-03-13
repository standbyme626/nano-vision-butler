<!-- source: 提示词.md | id: iy3tyj -->
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
