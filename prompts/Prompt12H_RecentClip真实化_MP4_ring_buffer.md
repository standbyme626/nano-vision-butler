# Prompt12H：Recent Clip 真实化（MP4 + ring buffer）

## 对应任务
- T13H

## 目标
产出真实可播放 clip，并与 ring buffer 策略协同。

## 输出
- edge_device/api/server.py（_assemble_clip 真实编码）
- edge_device/cache/ring_buffer.py（策略增强）
- tests/integration/test_edge_recent_clip_real_media.py

## 验收
- clip 为真实 MP4，可播放
- 片段长度与请求时长匹配
- 缓存淘汰策略可观测、可复现
