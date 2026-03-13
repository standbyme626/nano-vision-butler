<!-- source: 提示词.md | id: p5vt6x -->
你正在为 Vision Butler v5 实现 FastAPI 后端骨架。

任务目标：
建立正式可运行的后端入口、依赖注入和基础路由结构。

必须创建或补齐：
- src/app.py
- src/dependencies.py
- src/routes_memory.py
- src/routes_state.py
- src/routes_policy.py
- src/routes_device.py
- src/routes_ocr.py

最低要求：
- /healthz
- 路由注册清晰
- 基础异常处理
- 统一 JSON 响应格式
- 配置加载与数据库连接初始化

必须遵守：
1. 路由层不直接写复杂业务逻辑。
2. service 层与 repository 层解耦。
3. healthz 必须可用于 smoke test。
4. 不要提前写 nanobot 集成逻辑。
5. 不要引入无关中间件或复杂认证框架。

希望实现的正式路由占位：
- /memory/recent-events
- /memory/last-seen
- /memory/object-state
- /memory/zone-state
- /memory/world-state
- /policy/evaluate-staleness
- /device/status
- /device/command/take-snapshot
- /device/command/get-recent-clip
- /device/ingest/event
- /device/heartbeat
- /ocr/quick-read
- /ocr/extract-fields

完成后请：
1. 说明应用启动入口
2. 列出路由清单
3. 说明哪些路由目前只是骨架，哪些已经可用
