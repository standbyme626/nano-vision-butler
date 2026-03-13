# Prompt12G：跟踪 / Zone / 事件压缩质量提升

## 对应任务
- T13G

## 目标
提升 event 质量与稳定性，减少抖动与无效上报。

## 输出
- edge_device/tracking/tracker.py（真实策略）
- edge_device/compression/event_compressor.py（策略增强）
- tests/integration/test_edge_event_quality.py

## 验收
- track_id 在连续帧下稳定
- zone_id 映射正确
- 事件压缩策略可配置（阈值/去重/节流）
