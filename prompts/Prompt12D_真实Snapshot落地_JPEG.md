# Prompt12D：真实 Snapshot 落地（JPEG）

## 对应任务
- T13D

## 目标
把占位 snapshot 文件替换为真实 JPEG，先打通“可验图”最短路径。

## 输出
- edge_device/api/server.py（_store_snapshot 真实编码）
- tests/integration/test_edge_snapshot_real_media.py
- docs/edge/snapshot_contract.md

## 验收
- snapshot 为真实 JPEG，可被标准图像工具读取
- 宽高与实际帧一致
- snapshot URI 回传后端并可落库索引
