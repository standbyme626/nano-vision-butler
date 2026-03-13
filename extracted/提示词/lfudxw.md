<!-- source: 提示词.md | id: lfudxw -->
你正在为 Vision Butler v5 实现设备控制与媒体链路。

任务目标：
实现以下服务与路由：
- src/services/device_service.py
- /device/status
- /device/command/take-snapshot
- /device/command/get-recent-clip

项目背景（必须遵守）：
1. RK3566 前端只负责边缘感知、拍照、短视频缓存、心跳，不负责长期记忆与状态真相层。
2. 设备命令由后端 service 发起，前端执行并回传 media URI 或错误。
3. 所有设备命令都必须写 audit_logs。
4. 设备离线时要返回明确错误，不允许静默失败。
5. media_items 是正式媒体索引表，不允许只返回临时路径而不入库。

必须实现的能力：
- get_device_status(device_id)
- take_snapshot(device_id or camera_id)
- get_recent_clip(device_id or camera_id, duration_sec)
- 设备在线/离线判定
- 媒体索引写入 media_items
- 审计写入 audit_logs

输出要求：
- src/services/device_service.py
- src/routes_device.py
- 可选：src/schemas/device.py 补齐命令/响应模型
- tests/unit/test_device_service.py
- tests/integration/test_device_command_flow.py

必须遵守：
1. 当前任务不要实现真实 RK3566 SDK 调用，可用 adapter / stub / interface 方式占位。
2. 但 service 层接口必须稳定，便于后续 edge_device 接入。
3. take_snapshot 和 get_recent_clip 必须返回结构化结果：
   - ok
   - summary
   - data
   - meta
4. data 中至少包含：
   - media_id
   - uri
   - media_type
5. 对设备不可用、参数错误、媒体写入失败分别返回不同错误原因。

建议路由：
- GET /device/status?device_id=...
- POST /device/command/take-snapshot
- POST /device/command/get-recent-clip

验收标准：
- 设备状态查询可用
- take_snapshot 可返回 media URI 并写入 media_items
- get_recent_clip 可返回 clip URI 并写入 media_items
- 所有命令写 audit_logs
- 至少有 1 个设备离线测试分支

完成后请：
1. 说明 device_service 的接口边界
2. 说明媒体索引写入流程
3. 列出设备错误码 / 错误原因集合
4. 给出 2 个请求示例和对应响应示例
