<!-- source: 提示词.md | id: l80rk5 -->
你正在为 Vision Butler v5 实现最关键的“当前状态推定 + stale/freshness”能力。

任务目标：
实现以下服务与对应路由：
- src/services/state_service.py
- src/services/policy_service.py
- /memory/object-state
- /memory/zone-state
- /memory/world-state
- /policy/evaluate-staleness

项目背景（必须遵守）：
1. Telegram 是正式唯一用户入口，但本任务不直接实现 Telegram 交互。
2. nanobot 是唯一主控宿主，但不是业务真相层。
3. 当前状态必须落在数据库和服务层，不能只靠模型临时回答。
4. object_state 用于回答“某物现在大概率还在不在”。
5. zone_state 用于回答“某区域现在像不像有人 / 有物”。
6. world_state 只做摘要视图，不做复杂图谱。
7. policy_service 负责 freshness、stale、fallback_required、reason_code，不负责数据库写入。

必须实现的能力：
- get_object_state(object_name, camera_id?, zone_id?)
- get_zone_state(camera_id, zone_id)
- get_world_state()
- refresh_object_state(...)
- refresh_zone_state(...)
- evaluate_staleness(query_recency_class, fresh_until, device_status, now)
- classify_query_recency(query_text or query_type)

最小行为要求：
- object_state.state_value 支持：present / absent / unknown
- zone_state.state_value 支持：occupied / empty / likely_occupied / unknown
- policy 输出至少包括：
  - fresh_until
  - is_stale
  - fallback_required
  - reason_code
  - recency_class

必须遵守：
1. state_service 依赖 repository 和 memory/perception 结果，不要绕过 repository 直接写散 SQL。
2. policy_service 不做拍照、不做回复、不做 observation 写入。
3. 对缺失数据要返回“unknown + reason_code”，不要抛出模糊异常。
4. world_state 只做聚合摘要，不要设计成复杂知识图谱。
5. 路由层只负责参数解析和调用 service，不写业务逻辑。

建议输出文件：
- src/services/state_service.py
- src/services/policy_service.py
- src/routes_state.py
- src/routes_policy.py
- tests/unit/test_state_service.py
- tests/unit/test_policy_service.py

验收标准：
- object_state 查询可运行
- zone_state 查询可运行
- stale 逻辑可运行
- fallback_required 能正确输出
- reason_code 始终有值
- pytest 至少覆盖 present/absent/unknown 和 stale/non-stale 分支

完成后请：
1. 说明 object_state 的最小推定逻辑
2. 说明 zone_state 的最小推定逻辑
3. 列出 reason_code 的集合
4. 给出 3 个可直接运行的请求示例
