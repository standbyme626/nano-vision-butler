# Prompt12F：RKNN 检测模型部署（主检测）

## 对应任务
- T13F

## 目标
接入 RKNN 主检测模型，替换 LightweightDetector stub。

## 输出
- edge_device/inference/rknn_detector.py
- scripts/rknn/export_to_rknn.sh
- scripts/rknn/run_infer_benchmark.sh
- docs/edge/model_deploy.md

## 验收
- 板端输出真实 bbox/class/confidence
- model_version 与实际模型一致
- 推理失败可降级并记录错误
