# Telegram Flow

## Update 生命周期
1. 接收 `/telegram/update` 请求并解析 `update_id/message`。
2. 将 update 写入 `telegram_updates`，初始状态 `received`，按 `update_id` 去重。
3. 重复 update 直接返回 `ignored_duplicate`，不重复处理。
4. 非重复 update 执行路由（command/photo/video/text），通过 MCP tools 调用后端能力。
5. 成功则标记 `processed`；异常或权限拒绝则标记 `failed` 并写 `error_message`。

## 长消息分片规则
- 单条 Telegram 回复按 `3500` 字符分片（保守低于 Telegram 上限）。
- 分片优先在换行处分割，其次空格，最后硬切。
- 每片生成一条 `sendMessage`，顺序发送。

## 输入分支
- `command`：`/snapshot /clip /lastseen /state /ocr /device /help`。
- `photo`：提取 `file_id`，走 `ocr_quick_read`。
- `video`：提取 `file_id`，走 `ocr_quick_read`（视频帧 OCR 占位流程）。
- `text`：走 `get_world_state + query_recent_events` 生成友好回复。

## Chat Action
- 文本/命令默认 `typing`。
- 图片流程使用 `upload_photo`。
- 视频流程使用 `upload_video`。
- `/clip` 使用 `record_video`。

## 示例
### 示例 1：命令 `/snapshot`
请求（节选）：
```json
{
  "update_id": 9001,
  "message": {
    "chat": {"id": 1001},
    "from": {"id": 42},
    "text": "/snapshot rk3566-dev-01"
  }
}
```
响应（节选）：
```json
{
  "ok": true,
  "data": {
    "status": "processed",
    "actions": [{"method": "sendChatAction", "action": "upload_photo"}],
    "outbound_messages": [{"method": "sendMessage", "text": "拍照完成..."}]
  }
}
```

### 示例 2：图片输入
请求（节选）：
```json
{
  "update_id": 9002,
  "message": {
    "chat": {"id": 1001},
    "from": {"id": 42},
    "photo": [{"file_id": "small"}, {"file_id": "large"}]
  }
}
```
响应（节选）：
```json
{
  "ok": true,
  "data": {
    "status": "processed",
    "actions": [{"method": "sendChatAction", "action": "upload_photo"}],
    "outbound_messages": [{"method": "sendMessage", "text": "图片已转入 OCR 流程..."}]
  }
}
```

### 示例 3：失败命令 `/lastseen` 缺少参数
请求（节选）：
```json
{
  "update_id": 9003,
  "message": {
    "chat": {"id": 1001},
    "from": {"id": 42},
    "text": "/lastseen"
  }
}
```
响应（节选）：
```json
{
  "ok": true,
  "data": {
    "status": "failed",
    "error": "object_name is required for /lastseen"
  }
}
```
