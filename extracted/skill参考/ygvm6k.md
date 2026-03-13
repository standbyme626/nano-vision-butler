<!-- source: skill参考.md | id: ygvm6k -->
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${BACKEND_HOST:=0.0.0.0}"
: "${BACKEND_PORT:=8100}"
: "${SQLITE_DB_PATH:=${ROOT_DIR}/data/vision_butler.db}"
: "${MEDIA_ROOT:=${ROOT_DIR}/media}"
: "${PYTHON_BIN:=python}"

mkdir -p "${ROOT_DIR}/data"
mkdir -p "${MEDIA_ROOT}"
mkdir -p "${ROOT_DIR}/logs"

export SQLITE_DB_PATH
export MEDIA_ROOT

echo "[INFO] Starting backend API"
echo "[INFO] DB: ${SQLITE_DB_PATH}"
echo "[INFO] Media root: ${MEDIA_ROOT}"
echo "[INFO] Host: ${BACKEND_HOST}"
echo "[INFO] Port: ${BACKEND_PORT}"

# 如果你最终采用 uvicorn + FastAPI
exec "${PYTHON_BIN}" -m uvicorn src.app:app \
  --host "${BACKEND_HOST}" \
  --port "${BACKEND_PORT}" \
  --reload
