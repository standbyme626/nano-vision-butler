#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
: "${PYTHON_BIN:=python3}"
: "${BENCH_LOOPS:=20}"
: "${EDGE_DEVICE_ID:=rk3566-dev-01}"
: "${EDGE_CAMERA_ID:=cam-entry-01}"
: "${EDGE_DETECTOR_BACKEND:=rknn}"
: "${EDGE_BACKEND_POST_MODE:=sync}"
: "${EDGE_RUN_ONCE_SNAPSHOT_MODE:=sync}"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <model_rknn_path> [loops]"
  echo "Example: $0 ./models/rknn/yolov8n_rockchip_opt_i8_rk3566.rknn 50"
  exit 1
fi

MODEL_PATH="$1"
if [[ ! -f "${MODEL_PATH}" ]]; then
  echo "[ERROR] RKNN model not found: ${MODEL_PATH}"
  exit 2
fi

if [[ $# -ge 2 ]]; then
  BENCH_LOOPS="$2"
fi

export EDGE_RKNN_MODEL_PATH="${MODEL_PATH}"
export EDGE_DETECTOR_BACKEND
export EDGE_DEVICE_ID
export EDGE_CAMERA_ID
export EDGE_BACKEND_POST_MODE
export EDGE_RUN_ONCE_SNAPSHOT_MODE

echo "[INFO] Running edge inference benchmark"
echo "[INFO] Model       : ${EDGE_RKNN_MODEL_PATH}"
echo "[INFO] Loops       : ${BENCH_LOOPS}"
echo "[INFO] Detector    : ${EDGE_DETECTOR_BACKEND}"
echo "[INFO] Device/Camera: ${EDGE_DEVICE_ID}/${EDGE_CAMERA_ID}"
echo "[INFO] Backend mode: ${EDGE_BACKEND_POST_MODE}"
echo "[INFO] Snapshot mode: ${EDGE_RUN_ONCE_SNAPSHOT_MODE}"

cd "${ROOT_DIR}"
"${PYTHON_BIN}" - "${BENCH_LOOPS}" <<'PY'
import json
import sys
import time

from edge_device.api.server import EdgeDeviceRuntime, load_config_from_env

loops = int(sys.argv[1])
runtime = EdgeDeviceRuntime(config=load_config_from_env())
rows: list[dict] = []
model_version = "unknown"
detector_error = None
try:
    for i in range(1, loops + 1):
        start = time.perf_counter()
        result = runtime.run_once(trace_id=f"trace-bench-{i}")
        wall_ms = (time.perf_counter() - start) * 1000.0
        data = result.get("data", {})
        timings = data.get("timings_ms", {}) if isinstance(data, dict) else {}
        model_version = str(data.get("model_version"))
        detector_error = data.get("detector_error")
        row = {
            "wall_ms": float(wall_ms),
            "capture_ms": float(timings.get("capture_ms", 0.0)),
            "detect_total_ms": float(timings.get("detect_total_ms", 0.0)),
            "detector_preprocess_ms": float(timings.get("detector_preprocess_ms", 0.0)),
            "detector_infer_ms": float(timings.get("detector_infer_ms", 0.0)),
            "detector_postprocess_ms": float(timings.get("detector_postprocess_ms", 0.0)),
            "snapshot_ms": float(timings.get("snapshot_ms", 0.0)),
            "compress_ms": float(timings.get("compress_ms", 0.0)),
            "upload_ms": float(timings.get("upload_ms", 0.0)),
            "total_ms": float(timings.get("total_ms", 0.0)),
            "detections": float(data.get("detections", 0.0)),
        }
        rows.append(row)
        print(
            "[RUN {idx}] wall={wall:.1f}ms total={total:.1f}ms infer={infer:.1f}ms capture={capture:.1f}ms detect={det:.0f} | model={model} | detector_error={error}".format(
                idx=i,
                wall=row["wall_ms"],
                total=row["total_ms"],
                infer=row["detector_infer_ms"],
                capture=row["capture_ms"],
                det=row["detections"],
                model=model_version,
                error=detector_error,
            )
        )
finally:
    runtime.close()

if not rows:
    print("[RESULT] benchmark_parse_failed=1")
    raise SystemExit(0)


def avg(key: str) -> float:
    return sum(item[key] for item in rows) / len(rows)


avg_wall_ms = avg("wall_ms")
avg_capture_ms = avg("capture_ms")
avg_detect_total_ms = avg("detect_total_ms")
avg_detector_preprocess_ms = avg("detector_preprocess_ms")
avg_detector_infer_ms = avg("detector_infer_ms")
avg_detector_postprocess_ms = avg("detector_postprocess_ms")
avg_snapshot_ms = avg("snapshot_ms")
avg_compress_ms = avg("compress_ms")
avg_upload_ms = avg("upload_ms")
avg_total_ms = avg("total_ms")
avg_detections = avg("detections")
fps = (1000.0 / avg_total_ms) if avg_total_ms > 0 else 0.0

print(f"[RESULT] model_version={model_version}")
print(f"[RESULT] detector_error={detector_error}")
print(f"[RESULT] avg_wall_ms={avg_wall_ms:.2f}")
print(f"[RESULT] avg_capture_ms={avg_capture_ms:.2f}")
print(f"[RESULT] avg_detect_total_ms={avg_detect_total_ms:.2f}")
print(f"[RESULT] avg_detector_preprocess_ms={avg_detector_preprocess_ms:.2f}")
print(f"[RESULT] avg_detector_infer_ms={avg_detector_infer_ms:.2f}")
print(f"[RESULT] avg_detector_postprocess_ms={avg_detector_postprocess_ms:.2f}")
print(f"[RESULT] avg_snapshot_ms={avg_snapshot_ms:.2f}")
print(f"[RESULT] avg_compress_ms={avg_compress_ms:.2f}")
print(f"[RESULT] avg_upload_ms={avg_upload_ms:.2f}")
print(f"[RESULT] avg_total_ms={avg_total_ms:.2f}")
print(f"[RESULT] avg_detections={avg_detections:.2f}")
print(f"[RESULT] approx_fps={fps:.2f}")
PY
