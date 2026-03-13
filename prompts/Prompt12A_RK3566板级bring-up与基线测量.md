# Prompt12A：RK3566 板级 bring-up 与基线测量

## 对应任务
- T13A

## 目标
在真实 RK3566 板端建立可复现的摄像头与资源基线，为后续模型部署和媒体链路提供前置条件。

## 输出
- docs/edge/baseline_report.md
- scripts/edge_baseline_capture.sh
- scripts/edge_baseline_metrics.sh

## 验收
- 摄像头节点稳定枚举
- 分辨率/FPS/像素格式基线可复现
- 连续 30-60 分钟采集无崩溃/无持续掉流
- CPU/内存/NPU（若可读）指标有记录
