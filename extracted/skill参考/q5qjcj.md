<!-- source: skill参考.md | id: q5qjcj -->
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${EDGE_DEVICE_ID:=rk3566-01}"
: "${EDGE_CAMERA_ID:=camera-door-01}"
: "${EDGE_API_KEY:=CHANGE_ME}"
: "${EDGE_BACKEND_BASE:=http://127.0.0.1:8100}"
: "${EDGE_SNAPSHOT_DIR:=${ROOT_DIR}/edge_runtime/snapshots}"
: "${EDGE_CLIP_DIR:=${ROOT_DIR}/edge_runtime/clips}"
: "${EDGE_MODEL_NAME:=yolov6n}"
: "${PYTHON_BIN:=python}"

mkdir -p "${EDGE_SNAPSHOT_DIR}"
mkdir -p "${EDGE_CLIP_DIR}"
mkdir -p "${ROOT_DIR}/logs"

export EDGE_DEVICE_ID
export EDGE_CAMERA_ID
export EDGE_API_KEY
export EDGE_BACKEND_BASE
export EDGE_SNAPSHOT_DIR
export EDGE_CLIP_DIR
export EDGE_MODEL_NAME

echo "[INFO] Starting edge service"
echo "[INFO] Device: ${EDGE_DEVICE_ID}"
echo "[INFO] Camera: ${EDGE_CAMERA_ID}"
echo "[INFO] Backend: ${EDGE_BACKEND_BASE}"
echo "[INFO] Snapshot dir: ${EDGE_SNAPSHOT_DIR}"
echo "[INFO] Clip dir: ${EDGE_CLIP_DIR}"

# 这里默认 edge 入口为 edge_device.api.server
# 你后续可以让 Codex 把真实入口补到这个路径
exec "${PYTHON_BIN}" -m edge_device.api.server
