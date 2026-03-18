# Edge Model A/B Test Matrix (RK3566)

## 目标
- 在同一硬件、同一场景下对主检测候选做可复现对比。
- 给上线决策提供可量化证据，而不是只看单次 FPS。

## 先决条件（必须先满足）
- 已接入真实相机帧，不是 dummy 输入。
- 当前模型对应的后处理已对齐输出格式。
- 测试组统一使用同一摄像头、同一光照、同一采样窗口。

## 公共环境配置

```bash
export EDGE_ACTION=run-once
export EDGE_LOOP=0
export EDGE_INTERVAL_SEC=5
export EDGE_DEVICE_ID=rk3566-dev-01
export EDGE_CAMERA_ID=cam-entry-01
export EDGE_BACKEND_BASE_URL=http://100.92.134.46:8000

export EDGE_CAPTURE_SOURCE=/dev/video0
export EDGE_CAPTURE_BACKEND=v4l2
export EDGE_CAPTURE_RESOLUTION=1280x720
export EDGE_CAPTURE_FPS=30
export EDGE_CAPTURE_PIXEL_FORMAT=MJPG
export EDGE_CAPTURE_APPLY_V4L2_TUNING=1
export EDGE_CAPTURE_PARALLEL=1
export EDGE_CAPTURE_PARALLEL_WAIT_SEC=0.4
export EDGE_CAPTURE_RETRY_COUNT=3
export EDGE_CAPTURE_RETRY_DELAY_SEC=1.0

export EDGE_DETECTOR_BACKEND=rknn
export EDGE_DETECT_MIN_CONFIDENCE=0.35
export EDGE_RKNN_LABELS='person,bicycle,car,motorcycle,airplane,bus,train,truck,boat,traffic light,fire hydrant,stop sign,parking meter,bench,bird,cat,dog,horse,sheep,cow,elephant,bear,zebra,giraffe,backpack,umbrella,handbag,tie,suitcase,frisbee,skis,snowboard,sports ball,kite,baseball bat,baseball glove,skateboard,surfboard,tennis racket,bottle,wine glass,cup,fork,knife,spoon,bowl,banana,apple,sandwich,orange,broccoli,carrot,hot dog,pizza,donut,cake,chair,couch,potted plant,bed,dining table,toilet,tv,laptop,mouse,remote,keyboard,cell phone,microwave,oven,toaster,sink,refrigerator,book,clock,vase,scissors,teddy bear,hair drier,toothbrush'

export EDGE_SNAPSHOT_DIR=./data/edge_device/snapshots
export EDGE_CLIP_DIR=./data/edge_device/clips
export EDGE_SNAPSHOT_BUFFER_SIZE=32
export EDGE_CLIP_BUFFER_SIZE=16
export EDGE_PENDING_EVENT_DIR=./data/edge_device/pending_events
export EDGE_PENDING_EVENT_MAX=256
export EDGE_PENDING_FLUSH_BATCH=32
```

## 测试分组（第一轮）

| 组别 | 模型 | 输入 | 量化 | 角色 |
| --- | --- | --- | --- | --- |
| A1 | YOLOv5n | 416x416 | INT8 | 基线组 |
| A2 | YOLOv5n | 512x512 | INT8 | 小目标质量组 |
| B1 | YOLOv6n | 416x416 | INT8 | 轻量竞品组 |
| C1 | YOLOv8n | 416x416 | INT8 | 现代架构竞品组 |
| C2 | YOLOv8n | 512x512 | INT8 | 质量上限组 |

## 单组执行模板

```bash
# 以 A1 为例
export EDGE_DETECT_MODEL_VERSION=yolov5n-i8-416
export EDGE_RKNN_MODEL_VERSION=yolov5n-i8-416
export EDGE_RKNN_MODEL_PATH=./models/rknn/yolov5n_i8_416.rknn
export EDGE_RKNN_INPUT_SIZE=416x416

bash scripts/start_edge.sh run-once
```

## 循环测试模板（每组 30 次）

```bash
mkdir -p logs/abtest
for i in $(seq 1 30); do
  echo "===== RUN $i =====" | tee -a logs/abtest/${EDGE_RKNN_MODEL_VERSION}.log
  bash scripts/start_edge.sh run-once 2>&1 | tee -a logs/abtest/${EDGE_RKNN_MODEL_VERSION}.log
  sleep 1
done
```

## 指标与建议门槛

| 指标 | 建议门槛 | 用途 |
| --- | --- | --- |
| `infer_ms` | 越低越好 | 模型本体性能对比 |
| 端到端 FPS | >= 4（可用），>= 6（体验较好） | 实时体验判断 |
| CPU 平均占用 | < 180% | 留系统余量 |
| 内存峰值 | < 1.4GB | 2G 板卡安全边界 |
| 小目标召回 | >= 85% | 门口场景关键质量 |
| 误报率 | 越低越好 | 降低告警噪声 |
| 2 小时稳定性 | 无崩溃/无持续掉帧 | 常驻可行性 |

## 结果记录模板

| 组别 | infer_ms | e2e_fps | cpu_avg_pct | mem_peak_mb | recall_small | false_alarm | stability_2h | 结论 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 |  |  |  |  |  |  |  |  |
| A2 |  |  |  |  |  |  |  |  |
| B1 |  |  |  |  |  |  |  |  |
| C1 |  |  |  |  |  |  |  |  |
| C2 |  |  |  |  |  |  |  |  |

## 最新实机对比（2026-03-15，RK3566）

### 统一测试口径
- 设备：RK3566（NPU governor=`performance`，`cur_freq=900MHz`）
- 采集：`/dev/video0`，`1280x720`，`MJPG`，`30fps`
- 模型输入：`640x640`
- 运行参数：`EDGE_BACKEND_POST_MODE=async`、`EDGE_RUN_ONCE_SNAPSHOT_MODE=off`、`EDGE_CAPTURE_PARALLEL=1`
- 日志留档：`logs/rk3566_bench_20260315/*.log`

### 纯推理（不含采集/预处理/后处理）

| 模型 | avg_infer_ms | fps |
| --- | --- | --- |
| `main_detector_n_int8.rknn` | 127.21 | 7.86 |
| `yolov8n_official_i8_rk3566.rknn` | 53.26 | 18.78 |
| `yolov8n_rockchip_opt_i8_rk3566.rknn` | 52.94 | 18.89 |

### 端到端（优化前 vs 优化后）

说明：
- 优化前：分段改造已接入，但仍存在 `cv2` 缺失与采集双阶段开销。
- 优化后：`rknn` 环境补齐 `opencv-python-headless`，采集改为单次 snapshot 路径（去掉重复预抓拍）。

| 模型 | 优化前 avg_total_ms | 优化前 fps | 优化后 avg_total_ms | 优化后 fps | 提升 |
| --- | --- | --- | --- | --- | --- |
| `main_detector_n_int8.rknn` | 422.90 | 2.36 | 209.90 | 4.76 | +101.8% |
| `yolov8n_official_i8_rk3566.rknn` | 408.10 | 2.45 | 216.97 | 4.61 | +88.2% |
| `yolov8n_rockchip_opt_i8_rk3566.rknn` | 403.75 | 2.48 | 211.59 | 4.73 | +90.7% |

### 当前结论
- 在本项目 Python 端到端链路下，已从约 `2.4 FPS` 提升到约 `4.6~4.8 FPS`。
- `rockchip_opt` 与 `official` 在当前链路中的端到端差距很小（约 `0.12 FPS`）。
- 主瓶颈已从“纯推理”转为“预处理 + 后处理 + Python 链路”，不是 NPU 频率。
