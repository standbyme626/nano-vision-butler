# Prompt12C：真实采集层替换（V4L2/GStreamer）

## 对应任务
- T13C

## 目标
以真实采集管线替换 StubCamera，实现可恢复的板端采图能力。

## 输出
- edge_device/capture/camera.py（真实实现）
- edge_device/capture/v4l2_camera.py（或 gstreamer_camera.py）
- tests/unit/test_edge_capture.py

## 验收
- 支持 source/fps/resolution/pixel_format 配置
- 采集失败可重试并输出可观测错误
- 连续采集稳定运行
