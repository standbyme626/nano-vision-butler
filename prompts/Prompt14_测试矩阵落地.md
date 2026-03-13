<!-- source: 提示词.md | id: fhgj4o -->
你正在为 Vision Butler v5 把项目书中的测试矩阵落成真实测试。

任务目标：
实现 unit / integration / e2e 三层测试，并补齐 smoke test 脚本。

需要创建或补齐：
- tests/unit/
- tests/integration/
- tests/e2e/
- scripts/smoke_test.sh

项目背景（必须遵守）：
1. 本项目必须测试，不允许“功能先写，测试以后补”。
2. 测试矩阵已在项目书中定义，必须尽量落地。
3. Telegram 是正式入口，因此必须至少有 Telegram 相关集成或 e2e 测试。
4. 核心风险区在：state / policy / OCR / access control / device flow / Telegram flow。

至少需要覆盖的测试：
### Unit
- test_state_service.py
- test_policy_service.py
- test_security_guard.py
- test_memory_service.py
- test_ocr_service.py

### Integration
- test_device_event_flow.py
- test_object_state_flow.py
- test_zone_state_flow.py
- test_stale_fallback_flow.py
- test_access_control_flow.py
- test_telegram_message_flow.py

### E2E
- test_current_scene_query.py
- test_last_seen_query.py
- test_object_state_query.py
- test_ocr_query.py
- test_take_snapshot_command.py
- test_device_offline_alert.py

必须遵守：
1. 测试文件命名清晰。
2. 尽量避免真实外部依赖，优先 mock / fake adapter。
3. 测试要围绕正式行为，不要只测 trivial getter。
4. smoke_test.sh 至少验证：
   - 数据库初始化
   - /healthz
   - 一个核心查询路由
5. 如果暂时无法做完整 e2e，可先用 stub / fake nanobot/Telegram 层，但目录和意图必须完整。

验收标准：
- pytest -q 可运行
- 三层测试目录完整
- 至少核心路径有可运行测试
- smoke_test.sh 可执行
- 测试名称和项目书一致

完成后请：
1. 列出已创建测试文件
2. 标注哪些是真单测，哪些是假集成
3. 说明当前尚未 fully-real 的测试点
4. 给出推荐的 CI 执行顺序
