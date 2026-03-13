<!-- source: 提示词.md | id: w3fi7e -->
你正在为 Vision Butler v5 实现 RK3566 单目前端的最小正式版本。

任务目标：
建立 edge_device/ 下可运行的前端骨架，使其能够完成采集、轻量检测、事件压缩、心跳上报、拍照和最近视频片段回传。

必须创建或补齐：
- edge_device/capture/
- edge_device/inference/
- edge_device/tracking/
- edge_device/compression/
- edge_device/cache/
- edge_device/health/
- edge_device/api/

项目背景（必须遵守）：
1. 前端硬件是 2G+16G 的 RK3566 单目前端。
2. 前端定位是“边缘事件感知终端”，不是完整智能体。
3. 前端负责：
   - 图像采集
   - 轻量检测
   - 轻量跟踪
   - 事件压缩
   - 快照缓存
   - 最近片段缓存
   - 设备状态上报
4. 前端不负责：
   - 长期记忆
   - 状态推理
   - stale/freshness
   - Telegram 交互
   - MCP
   - 权限控制
5. 当前任务允许使用 adapter / stub 模拟模型调用，但结构必须为后续 RKNN 接入预留清晰边界。

必须实现的能力：
- capture latest frame
- run lightweight detection interface
- assign / pass through track_id
- compress detections into event envelope
- maintain ring buffer for recent snapshots / clips
- heartbeat payload assembly
- respond to take_snapshot command
- respond to get_recent_clip command

建议输出：
- edge_device/api/server.py 或等价入口
- edge_device/capture/camera.py
- edge_device/inference/detector.py
- edge_device/tracking/tracker.py
- edge_device/compression/event_compressor.py
- edge_device/cache/ring_buffer.py
- edge_device/health/heartbeat.py
- docs/EDGE_DEVICE.md

必须遵守：
1. 不要在前端写业务数据库逻辑。
2. 不要把后端 policy/state 逻辑挪到前端。
3. 所有对外输出都要走统一 event envelope / command response。
4. 拍照与 clip 返回必须可被后端 device_service 消费。
5. 代码要对后续接入 RKNN / GStreamer / V4L2 友好。

验收标准：
- 能构造 device heartbeat
- 能生成 observation 风格事件 envelope
- take_snapshot 可返回 snapshot uri/path
- get_recent_clip 可返回 clip uri/path
- ring buffer 行为可测试
- 至少有前端单元测试或模拟测试

完成后请：
1. 说明前端模块职责划分
2. 给出 event envelope 示例
3. 给出 heartbeat payload 示例
4. 标出哪些位置后续接真实 RKNN / 相机驱动
