#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
: "${PYTHON_BIN:=python3}"
: "${RKNN_DO_QUANTIZATION:=1}"
: "${RKNN_DATASET_PATH:=}"

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <onnx_model_path> <output_rknn_path> [target_platform]"
  echo "Example: $0 ./models/onnx/yolov8n_rockchip_opt.onnx ./models/rknn/yolov8n_rockchip_opt_i8_rk3566.rknn rk3566"
  exit 1
fi

ONNX_MODEL="$1"
OUTPUT_RKNN="$2"
TARGET_PLATFORM="${3:-rk3566}"

if [[ ! -f "${ONNX_MODEL}" ]]; then
  echo "[ERROR] ONNX model not found: ${ONNX_MODEL}"
  exit 2
fi

mkdir -p "$(dirname "${OUTPUT_RKNN}")"

echo "[INFO] Exporting ONNX -> RKNN"
echo "[INFO] ONNX   : ${ONNX_MODEL}"
echo "[INFO] RKNN   : ${OUTPUT_RKNN}"
echo "[INFO] Target : ${TARGET_PLATFORM}"
echo "[INFO] Quant  : ${RKNN_DO_QUANTIZATION}"
echo "[INFO] Dataset: ${RKNN_DATASET_PATH:-<none>}"

"${PYTHON_BIN}" - <<'PY' "${ONNX_MODEL}" "${OUTPUT_RKNN}" "${TARGET_PLATFORM}" "${RKNN_DO_QUANTIZATION}" "${RKNN_DATASET_PATH}"
import sys
import types
from pathlib import Path

onnx_path = Path(sys.argv[1])
rknn_path = Path(sys.argv[2])
target = sys.argv[3]
do_quant = sys.argv[4].strip().lower() in {"1", "true", "yes", "y", "on"}
dataset_raw = sys.argv[5].strip()
dataset_path = Path(dataset_raw) if dataset_raw else None

# RKNN Toolkit2 (2.3.x) still expects legacy onnx.mapping API.
import onnx
if not hasattr(onnx, "mapping") and hasattr(onnx, "_mapping"):
    tmap = onnx._mapping.TENSOR_TYPE_MAP
    mapping = types.SimpleNamespace()
    mapping.TENSOR_TYPE_TO_NP_TYPE = {k: v.np_dtype for k, v in tmap.items()}
    mapping.NP_TYPE_TO_TENSOR_TYPE = {v.np_dtype: k for k, v in tmap.items()}
    onnx.mapping = mapping

try:
    from rknn.api import RKNN
except Exception as exc:
    raise SystemExit(f"[ERROR] Failed to import rknn.api.RKNN: {exc}")

if do_quant and (dataset_path is None or not dataset_path.exists()):
    raise SystemExit("[ERROR] RKNN_DO_QUANTIZATION=1 requires RKNN_DATASET_PATH to point to an existing dataset txt file.")

rknn = RKNN(verbose=True)
ret = rknn.config(
    mean_values=[[0, 0, 0]],
    std_values=[[255, 255, 255]],
    target_platform=target,
)
if ret != 0:
    raise SystemExit(f"[ERROR] rknn.config failed: {ret}")

ret = rknn.load_onnx(model=str(onnx_path))
if ret != 0:
    raise SystemExit(f"[ERROR] rknn.load_onnx failed: {ret}")

ret = rknn.build(
    do_quantization=do_quant,
    dataset=str(dataset_path) if dataset_path else None,
)
if ret != 0:
    raise SystemExit(f"[ERROR] rknn.build failed: {ret}")

ret = rknn.export_rknn(str(rknn_path))
if ret != 0:
    raise SystemExit(f"[ERROR] rknn.export_rknn failed: {ret}")

rknn.release()
print(f"[OK] RKNN exported to {rknn_path}")
PY
