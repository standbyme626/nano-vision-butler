#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${BACKEND_HOST:=0.0.0.0}"
: "${BACKEND_PORT:=8000}"
: "${BACKEND_RELOAD:=0}"
: "${BACKEND_CONFIG_DIR:=${ROOT_DIR}/config}"
: "${PYTHON_BIN:=python3}"
: "${VISION_BUTLER_TIME_MODE:=local}"
: "${TZ:=Asia/Shanghai}"
: "${VISION_Q8_PROVIDER:=ollama}"
: "${VISION_Q8_OLLAMA_BASE_URL:=http://127.0.0.1:11434}"
: "${VISION_Q8_OLLAMA_MODEL:=qwen3.5:0.8b}"
: "${VISION_Q8_TIMEOUT_SEC:=30}"
: "${VISION_Q8_KEEP_ALIVE:=5m}"
: "${VISION_Q8_TEMPERATURE:=0.1}"
: "${VISION_Q8_NUM_PREDICT:=160}"

mkdir -p "${ROOT_DIR}/data" "${ROOT_DIR}/logs"
cd "${ROOT_DIR}"
export VISION_BUTLER_CONFIG_DIR="${BACKEND_CONFIG_DIR}"
export VISION_BUTLER_TIME_MODE
export TZ
export VISION_Q8_PROVIDER
export VISION_Q8_OLLAMA_BASE_URL
export VISION_Q8_OLLAMA_MODEL
export VISION_Q8_TIMEOUT_SEC
export VISION_Q8_KEEP_ALIVE
export VISION_Q8_TEMPERATURE
export VISION_Q8_NUM_PREDICT

echo "[INFO] Starting backend service"
echo "[INFO] Root      : ${ROOT_DIR}"
echo "[INFO] Host      : ${BACKEND_HOST}"
echo "[INFO] Port      : ${BACKEND_PORT}"
echo "[INFO] Reload    : ${BACKEND_RELOAD}"
echo "[INFO] Config dir: ${BACKEND_CONFIG_DIR}"
echo "[INFO] Time mode : ${VISION_BUTLER_TIME_MODE} (TZ=${TZ})"
echo "[INFO] Q8 provider: ${VISION_Q8_PROVIDER}"
echo "[INFO] Q8 base url: ${VISION_Q8_OLLAMA_BASE_URL}"
echo "[INFO] Q8 model   : ${VISION_Q8_OLLAMA_MODEL}"
echo "[INFO] Q8 timeout : ${VISION_Q8_TIMEOUT_SEC}s"

CMD=(
  "${PYTHON_BIN}"
  -m
  uvicorn
  src.app:app
  --host
  "${BACKEND_HOST}"
  --port
  "${BACKEND_PORT}"
)

if [[ "${BACKEND_RELOAD}" == "1" ]]; then
  CMD+=(--reload)
fi

exec "${CMD[@]}"
