<!-- source: 提示词.md | id: twt9xh -->
你正在为 Vision Butler v5 实现 Telegram 正式交互链路。

任务目标：
把 Telegram 作为正式唯一用户入口完整打通，并与 nanobot / Qwen3.5 / MCP tools 对接。

需要创建或补齐：
- src/services/reply_service.py 或 src/services/reply_builder.py
- Telegram update 去重处理逻辑
- 长消息分片逻辑
- sendChatAction 调用逻辑
- 基础命令式入口规范
- 与 telegram_updates 表的状态联动

项目背景（必须遵守）：
1. Telegram 是正式唯一用户入口，不是临时入口。
2. Telegram Bot API 的 getUpdates 与 setWebhook 是互斥方式，未消费更新在服务器端最长只保留 24 小时。
3. Telegram 文本消息单条有长度限制，因此系统必须支持长回复分片。
4. 长耗时视觉任务必须有 processing / typing / upload_photo 等状态提示。
5. 入口层不能承载状态真相层逻辑，业务事实必须继续由后端 services + MCP 提供。

必须实现的能力：
- save incoming update with dedup
- route text / photo / video / command
- send processing status
- split long text replies
- persist processed / failed update status
- 将 MCP tool 返回结果格式化为 Telegram 友好回复
- 支持至少这些命令：
  - /snapshot
  - /clip
  - /lastseen
  - /state
  - /ocr
  - /device
  - /help

必须遵守：
1. 不要在 Telegram 处理层直接写 state / policy / OCR 业务逻辑。
2. 不要把 nanobot 核心协议重写成自定义机器人框架。
3. 不要跳过 update_id 去重。
4. 对失败 update 必须写 telegram_updates.status = failed。
5. 回复要考虑文本和媒体混合场景。

建议输出：
- src/services/reply_service.py 或 reply_builder.py
- src/schemas/telegram.py
- tests/integration/test_telegram_message_flow.py
- tests/e2e/test_telegram_commands.py
- docs/TELEGRAM_FLOW.md

验收标准：
- 文本问答可用
- 图片输入可转发给模型 / OCR 流程
- 命令入口可用
- 长消息自动分片
- 长任务有 sendChatAction
- telegram_updates 有 received / processed / failed 三种状态流转

完成后请：
1. 说明 Telegram update 生命周期
2. 说明长消息分片规则
3. 说明图片/视频/命令三类输入的处理分支
4. 给出 3 个 Telegram 请求示例和对应输出示例
