<!-- source: 提示词.md | id: s3f1ka -->
你正在为 Vision Butler v5 实现 observation / event / heartbeat 的正式写入链路。

任务目标：
实现：
- src/services/memory_service.py
- src/services/perception_service.py

并打通：
- /device/ingest/event
- /device/heartbeat

必须实现的能力：
1. 接收前端事件 payload
2. 基础设备校验
3. 写入 observations
4. 根据规则选择是否升级为 events
5. 写入 audit_logs
6. heartbeat 刷新 devices 表中的 last_seen、status、温度、负载等字段

必须遵守：
1. perception_service 只负责接入、校验、写 observation、触发后续动作。
2. event 升级规则先做保守版本，不要过度复杂化。
3. state 刷新只预留调用点，不要在此任务里实现完整 state_service。
4. 所有敏感动作必须写 audit。
5. 设备无权限或缺失时返回明确错误。

输入假设：
- schema.sql 已存在
- repository 层已完成
- FastAPI 骨架已存在

输出要求：
- 代码可运行
- 至少补一个最小设备事件 JSON 样例
- 至少补 heartbeat JSON 样例
- 给出集成测试建议

完成后请：
1. 说明事件上报流程
2. 说明 observation 升 event 的当前规则
3. 列出后续 state_service 将接入的钩子点
