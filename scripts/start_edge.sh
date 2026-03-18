#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_EDGE_RKNN_LABELS='person,bicycle,car,motorcycle,airplane,bus,train,truck,boat,traffic light,fire hydrant,stop sign,parking meter,bench,bird,cat,dog,horse,sheep,cow,elephant,bear,zebra,giraffe,backpack,umbrella,handbag,tie,suitcase,frisbee,skis,snowboard,sports ball,kite,baseball bat,baseball glove,skateboard,surfboard,tennis racket,bottle,wine glass,cup,fork,knife,spoon,bowl,banana,apple,sandwich,orange,broccoli,carrot,hot dog,pizza,donut,cake,chair,couch,potted plant,bed,dining table,toilet,tv,laptop,mouse,remote,keyboard,cell phone,microwave,oven,toaster,sink,refrigerator,book,clock,vase,scissors,teddy bear,hair drier,toothbrush'

: "${EDGE_ACTION:=run-once}"
: "${EDGE_LOOP:=0}"
: "${EDGE_INTERVAL_SEC:=5}"
: "${EDGE_DEVICE_ID:=rk3566-dev-01}"
: "${EDGE_CAMERA_ID:=cam-entry-01}"
: "${EDGE_BACKEND_BASE_URL:=http://100.92.134.46:8000}"
: "${EDGE_CAPTURE_SOURCE:=}"
: "${EDGE_CAPTURE_RESOLUTION:=1280x720}"
: "${EDGE_CAPTURE_FPS:=30}"
: "${EDGE_CAPTURE_PIXEL_FORMAT:=MJPG}"
: "${EDGE_CAPTURE_BACKEND:=auto}"
: "${EDGE_CAPTURE_APPLY_V4L2_TUNING:=1}"
: "${EDGE_CAPTURE_DISABLE_DYNAMIC_FRAMERATE:=0}"
: "${EDGE_CAPTURE_PARALLEL:=1}"
: "${EDGE_CAPTURE_PARALLEL_WAIT_SEC:=0.4}"
: "${EDGE_CAPTURE_RETRY_COUNT:=3}"
: "${EDGE_CAPTURE_RETRY_DELAY_SEC:=1.0}"
: "${EDGE_BACKEND_POST_MODE:=sync}"
: "${EDGE_BACKEND_POST_QUEUE_MAX:=64}"
: "${EDGE_RUN_ONCE_SNAPSHOT_MODE:=sync}"
: "${EDGE_DETECTOR_BACKEND:=auto}"
: "${EDGE_DETECT_MIN_CONFIDENCE:=0.20}"
: "${EDGE_DETECT_MODEL_VERSION:=stub-detector-v1}"
: "${EDGE_RKNN_MODEL_PATH:=./models/rknn/yolov8n_oiv7_nosigmoid_i8_rk3566.rknn}"
: "${EDGE_RKNN_MODEL_VERSION:=}"
: "${EDGE_RKNN_INPUT_SIZE:=640x640}"
: "${EDGE_RKNN_NMS_THRESHOLD:=0.45}"
: "${EDGE_RKNN_MAX_CANDIDATES:=64}"
: "${EDGE_RKNN_LABELS_PATH:=}"
: "${EDGE_RKNN_LABELS:=${DEFAULT_EDGE_RKNN_LABELS}}"
: "${EDGE_DETECT_CLASS_ALLOWLIST_PATH:=}"
: "${EDGE_DETECT_CLASS_ALLOWLIST:=}"
: "${EDGE_TRACK_ZONE_SWITCH_MARGIN:=0.03}"
: "${EDGE_ANALYSIS_ENABLE:=1}"
: "${EDGE_ANALYSIS_OCR_ENABLE:=1}"
: "${EDGE_ANALYSIS_MIN_IMPORTANCE_OCR:=4}"
: "${EDGE_ANALYSIS_Q8_ENABLE:=1}"
: "${EDGE_ANALYSIS_MIN_IMPORTANCE_Q8:=3}"
: "${EDGE_ANALYSIS_Q8_INTERVAL_SEC:=30}"
: "${EDGE_ANALYSIS_PROFILE:=backend_heavy_v1}"
: "${EDGE_ANALYSIS_OCR_CLASSES:=package,document,label,screen}"
: "${EDGE_ANALYSIS_Q8_CLASSES:=person}"
: "${EDGE_SNAPSHOT_DIR:=${ROOT_DIR}/data/edge_device/snapshots}"
: "${EDGE_CLIP_DIR:=${ROOT_DIR}/data/edge_device/clips}"
: "${EDGE_SNAPSHOT_BUFFER_SIZE:=32}"
: "${EDGE_CLIP_BUFFER_SIZE:=16}"
: "${EDGE_PENDING_EVENT_DIR:=${ROOT_DIR}/data/edge_device/pending_events}"
: "${EDGE_PENDING_EVENT_MAX:=256}"
: "${EDGE_PENDING_FLUSH_BATCH:=32}"
: "${PYTHON_BIN:=}"
: "${VISION_BUTLER_TIME_MODE:=local}"
: "${TZ:=Asia/Shanghai}"

if [[ $# -gt 0 ]]; then
  EDGE_ACTION="$1"
  shift
fi

mkdir -p "${EDGE_SNAPSHOT_DIR}" "${EDGE_CLIP_DIR}" "${EDGE_PENDING_EVENT_DIR}" "${ROOT_DIR}/logs"
cd "${ROOT_DIR}"

parse_capture_resolution() {
  local raw normalized
  raw="${EDGE_CAPTURE_RESOLUTION:-1280x720}"
  normalized="${raw,,}"
  if [[ "${normalized}" =~ ^([0-9]+)x([0-9]+)$ ]]; then
    echo "${BASH_REMATCH[1]} ${BASH_REMATCH[2]}"
    return 0
  fi
  echo "1280 720"
}

apply_v4l2_tuning() {
  local dims width height
  if [[ "${EDGE_CAPTURE_APPLY_V4L2_TUNING}" != "1" ]]; then
    return 0
  fi
  if [[ -z "${EDGE_CAPTURE_SOURCE}" || ! "${EDGE_CAPTURE_SOURCE}" =~ ^/dev/video[0-9]+$ ]]; then
    return 0
  fi
  if ! command -v v4l2-ctl >/dev/null 2>&1; then
    echo "[WARN] v4l2-ctl not found, skip camera tuning"
    return 0
  fi

  dims="$(parse_capture_resolution)"
  width="${dims%% *}"
  height="${dims##* }"

  if ! v4l2-ctl -d "${EDGE_CAPTURE_SOURCE}" \
    --set-fmt-video="width=${width},height=${height},pixelformat=${EDGE_CAPTURE_PIXEL_FORMAT}" >/dev/null 2>&1; then
    echo "[WARN] set-fmt-video failed for ${EDGE_CAPTURE_SOURCE}"
  fi
  if ! v4l2-ctl -d "${EDGE_CAPTURE_SOURCE}" --set-parm="${EDGE_CAPTURE_FPS}" >/dev/null 2>&1; then
    echo "[WARN] set-parm failed for ${EDGE_CAPTURE_SOURCE}"
  fi
  if [[ "${EDGE_CAPTURE_DISABLE_DYNAMIC_FRAMERATE}" == "1" ]]; then
    v4l2-ctl -d "${EDGE_CAPTURE_SOURCE}" --set-ctrl=exposure_dynamic_framerate=0 >/dev/null 2>&1 || true
  fi

  echo "[INFO] Applied v4l2 tuning: source=${EDGE_CAPTURE_SOURCE} resolution=${width}x${height} fps=${EDGE_CAPTURE_FPS} format=${EDGE_CAPTURE_PIXEL_FORMAT}"
  v4l2-ctl -d "${EDGE_CAPTURE_SOURCE}" --get-fmt-video 2>/dev/null | sed 's/^/[INFO] /'
  v4l2-ctl -d "${EDGE_CAPTURE_SOURCE}" --get-parm 2>/dev/null | sed 's/^/[INFO] /'
}

python_has_rknnlite() {
  local bin="$1"
  if [[ -z "${bin}" ]]; then
    return 1
  fi
  if [[ "${bin}" == */* ]]; then
    if [[ ! -x "${bin}" ]]; then
      return 1
    fi
  elif ! command -v "${bin}" >/dev/null 2>&1; then
    return 1
  fi
  "${bin}" - <<'PY' >/dev/null 2>&1
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("rknnlite") else 1)
PY
}

resolve_python_bin() {
  local backend normalized candidate
  backend="${EDGE_DETECTOR_BACKEND:-auto}"
  normalized="${backend,,}"

  if [[ -n "${PYTHON_BIN}" ]]; then
    if [[ "${normalized}" == "rknn" ]] && ! python_has_rknnlite "${PYTHON_BIN}"; then
      echo "[WARN] PYTHON_BIN=${PYTHON_BIN} has no rknnlite; RKNN may fallback"
    fi
    return 0
  fi

  if [[ "${normalized}" == "rknn" || "${normalized}" == "auto" ]]; then
    for candidate in "/root/.venv_rknn/bin/python" "${ROOT_DIR}/.venv_rknn/bin/python" "python3"; do
      if python_has_rknnlite "${candidate}"; then
        PYTHON_BIN="${candidate}"
        return 0
      fi
    done
  fi

  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
    return 0
  fi
  echo "[ERROR] No python interpreter found"
  exit 1
}

detect_rknnlite_status() {
  if python_has_rknnlite "${PYTHON_BIN}"; then
    echo "yes"
  else
    echo "no"
  fi
}

resolve_python_bin
RKNNLITE_STATUS="$(detect_rknnlite_status)"
if [[ "${EDGE_DETECTOR_BACKEND,,}" == "rknn" && "${RKNNLITE_STATUS}" != "yes" ]]; then
  echo "[WARN] EDGE_DETECTOR_BACKEND=rknn but interpreter has no rknnlite"
fi

if [[ -z "${EDGE_RKNN_LABELS_PATH}" ]]; then
  if [[ "${EDGE_RKNN_MODEL_PATH,,}" == *"oiv7"* ]]; then
    AUTO_OIV7_LABELS="${ROOT_DIR}/config/labels/openimages_v7_601.txt"
    if [[ -f "${AUTO_OIV7_LABELS}" ]]; then
      EDGE_RKNN_LABELS_PATH="${AUTO_OIV7_LABELS}"
      echo "[INFO] Auto labels path    : ${EDGE_RKNN_LABELS_PATH}"
    else
      echo "[WARN] OIV7 model detected but labels file missing: ${AUTO_OIV7_LABELS}"
    fi
  fi
fi

export EDGE_DEVICE_ID
export EDGE_CAMERA_ID
export EDGE_BACKEND_BASE_URL
export EDGE_CAPTURE_SOURCE
export EDGE_CAPTURE_RESOLUTION
export EDGE_CAPTURE_FPS
export EDGE_CAPTURE_PIXEL_FORMAT
export EDGE_CAPTURE_BACKEND
export EDGE_CAPTURE_APPLY_V4L2_TUNING
export EDGE_CAPTURE_DISABLE_DYNAMIC_FRAMERATE
export EDGE_CAPTURE_PARALLEL
export EDGE_CAPTURE_PARALLEL_WAIT_SEC
export EDGE_CAPTURE_RETRY_COUNT
export EDGE_CAPTURE_RETRY_DELAY_SEC
export EDGE_BACKEND_POST_MODE
export EDGE_BACKEND_POST_QUEUE_MAX
export EDGE_RUN_ONCE_SNAPSHOT_MODE
export EDGE_DETECTOR_BACKEND
export EDGE_DETECT_MIN_CONFIDENCE
export EDGE_DETECT_MODEL_VERSION
export EDGE_RKNN_MODEL_PATH
export EDGE_RKNN_MODEL_VERSION
export EDGE_RKNN_INPUT_SIZE
export EDGE_RKNN_NMS_THRESHOLD
export EDGE_RKNN_MAX_CANDIDATES
export EDGE_RKNN_LABELS_PATH
export EDGE_RKNN_LABELS
export EDGE_DETECT_CLASS_ALLOWLIST_PATH
export EDGE_DETECT_CLASS_ALLOWLIST
export EDGE_TRACK_ZONE_SWITCH_MARGIN
export EDGE_ANALYSIS_ENABLE
export EDGE_ANALYSIS_OCR_ENABLE
export EDGE_ANALYSIS_MIN_IMPORTANCE_OCR
export EDGE_ANALYSIS_Q8_ENABLE
export EDGE_ANALYSIS_MIN_IMPORTANCE_Q8
export EDGE_ANALYSIS_Q8_INTERVAL_SEC
export EDGE_ANALYSIS_PROFILE
export EDGE_ANALYSIS_OCR_CLASSES
export EDGE_ANALYSIS_Q8_CLASSES
export EDGE_SNAPSHOT_DIR
export EDGE_CLIP_DIR
export EDGE_SNAPSHOT_BUFFER_SIZE
export EDGE_CLIP_BUFFER_SIZE
export EDGE_PENDING_EVENT_DIR
export EDGE_PENDING_EVENT_MAX
export EDGE_PENDING_FLUSH_BATCH
export VISION_BUTLER_TIME_MODE
export TZ

echo "[INFO] Starting edge runtime"
echo "[INFO] Action             : ${EDGE_ACTION}"
echo "[INFO] Loop               : ${EDGE_LOOP}"
echo "[INFO] Device             : ${EDGE_DEVICE_ID}"
echo "[INFO] Camera             : ${EDGE_CAMERA_ID}"
echo "[INFO] Backend            : ${EDGE_BACKEND_BASE_URL}"
echo "[INFO] Capture source     : ${EDGE_CAPTURE_SOURCE:-stub://camera}"
echo "[INFO] Capture resolution : ${EDGE_CAPTURE_RESOLUTION}"
echo "[INFO] Capture fps        : ${EDGE_CAPTURE_FPS}"
echo "[INFO] Capture pixel fmt  : ${EDGE_CAPTURE_PIXEL_FORMAT}"
echo "[INFO] Capture backend    : ${EDGE_CAPTURE_BACKEND}"
echo "[INFO] Capture tuning     : ${EDGE_CAPTURE_APPLY_V4L2_TUNING} (disable_dynamic_framerate=${EDGE_CAPTURE_DISABLE_DYNAMIC_FRAMERATE})"
echo "[INFO] Capture parallel   : ${EDGE_CAPTURE_PARALLEL} (wait=${EDGE_CAPTURE_PARALLEL_WAIT_SEC}s)"
echo "[INFO] Capture retries    : ${EDGE_CAPTURE_RETRY_COUNT} (delay=${EDGE_CAPTURE_RETRY_DELAY_SEC}s)"
echo "[INFO] Backend post mode  : ${EDGE_BACKEND_POST_MODE} (queue_max=${EDGE_BACKEND_POST_QUEUE_MAX})"
echo "[INFO] Run-once snapshot  : ${EDGE_RUN_ONCE_SNAPSHOT_MODE}"
echo "[INFO] Detector backend   : ${EDGE_DETECTOR_BACKEND}"
echo "[INFO] Detector min conf  : ${EDGE_DETECT_MIN_CONFIDENCE}"
echo "[INFO] RKNN model path    : ${EDGE_RKNN_MODEL_PATH:-<auto>}"
echo "[INFO] RKNN model version : ${EDGE_RKNN_MODEL_VERSION:-<auto>}"
echo "[INFO] Python bin         : ${PYTHON_BIN}"
echo "[INFO] RKNN runtime ready : ${RKNNLITE_STATUS}"
echo "[INFO] RKNN input size    : ${EDGE_RKNN_INPUT_SIZE}"
echo "[INFO] RKNN nms threshold : ${EDGE_RKNN_NMS_THRESHOLD}"
echo "[INFO] RKNN max candidates: ${EDGE_RKNN_MAX_CANDIDATES}"
echo "[INFO] RKNN labels path   : ${EDGE_RKNN_LABELS_PATH:-<none>}"
echo "[INFO] RKNN labels        : ${EDGE_RKNN_LABELS}"
echo "[INFO] Detect allowlist path : ${EDGE_DETECT_CLASS_ALLOWLIST_PATH:-<none>}"
echo "[INFO] Detect allowlist csv  : ${EDGE_DETECT_CLASS_ALLOWLIST:-<none>}"
echo "[INFO] Track zone margin  : ${EDGE_TRACK_ZONE_SWITCH_MARGIN}"
echo "[INFO] Analysis enable    : ${EDGE_ANALYSIS_ENABLE}"
echo "[INFO] Analysis OCR       : ${EDGE_ANALYSIS_OCR_ENABLE}"
echo "[INFO] Analysis min imp   : ${EDGE_ANALYSIS_MIN_IMPORTANCE_OCR}"
echo "[INFO] Analysis Q8        : ${EDGE_ANALYSIS_Q8_ENABLE}"
echo "[INFO] Analysis Q8 min imp: ${EDGE_ANALYSIS_MIN_IMPORTANCE_Q8}"
echo "[INFO] Analysis Q8 every  : ${EDGE_ANALYSIS_Q8_INTERVAL_SEC}s"
echo "[INFO] Analysis profile   : ${EDGE_ANALYSIS_PROFILE}"
echo "[INFO] Analysis OCR class : ${EDGE_ANALYSIS_OCR_CLASSES}"
echo "[INFO] Analysis Q8 class  : ${EDGE_ANALYSIS_Q8_CLASSES}"
echo "[INFO] Snapshot dir       : ${EDGE_SNAPSHOT_DIR}"
echo "[INFO] Clip dir           : ${EDGE_CLIP_DIR}"
echo "[INFO] Snapshot buf size  : ${EDGE_SNAPSHOT_BUFFER_SIZE}"
echo "[INFO] Clip buf size      : ${EDGE_CLIP_BUFFER_SIZE}"
echo "[INFO] Pending event dir  : ${EDGE_PENDING_EVENT_DIR}"
echo "[INFO] Pending event max  : ${EDGE_PENDING_EVENT_MAX}"
echo "[INFO] Flush batch size   : ${EDGE_PENDING_FLUSH_BATCH}"
echo "[INFO] Time mode          : ${VISION_BUTLER_TIME_MODE} (TZ=${TZ})"

apply_v4l2_tuning

if [[ "${EDGE_LOOP}" == "1" ]]; then
  while true; do
    "${PYTHON_BIN}" -m edge_device.api.server "${EDGE_ACTION}"
    sleep "${EDGE_INTERVAL_SEC}"
  done
fi

exec "${PYTHON_BIN}" -m edge_device.api.server "${EDGE_ACTION}"
