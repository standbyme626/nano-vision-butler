#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${BACKEND_HOST:=0.0.0.0}"
: "${BACKEND_PORT:=8000}"
: "${BACKEND_RELOAD:=0}"
: "${BACKEND_CONFIG_DIR:=${ROOT_DIR}/config}"
: "${PYTHON_BIN:=python3}"

mkdir -p "${ROOT_DIR}/data" "${ROOT_DIR}/logs"
cd "${ROOT_DIR}"
export VISION_BUTLER_CONFIG_DIR="${BACKEND_CONFIG_DIR}"

echo "[INFO] Starting backend service"
echo "[INFO] Root      : ${ROOT_DIR}"
echo "[INFO] Host      : ${BACKEND_HOST}"
echo "[INFO] Port      : ${BACKEND_PORT}"
echo "[INFO] Reload    : ${BACKEND_RELOAD}"
echo "[INFO] Config dir: ${BACKEND_CONFIG_DIR}"

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
