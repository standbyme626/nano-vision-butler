#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

: "${PYTHON_BIN:=python3}"
: "${MCP_HOST:=0.0.0.0}"
: "${MCP_PORT:=8001}"
: "${MCP_PATH:=/mcp}"
: "${MCP_CONFIG_DIR:=${ROOT_DIR}/config}"

if [[ ! -d "${MCP_CONFIG_DIR}" ]]; then
  echo "[ERROR] MCP config dir not found: ${MCP_CONFIG_DIR}" >&2
  exit 1
fi

echo "[INFO] Starting MCP streamable-http server"
echo "[INFO] Root      : ${ROOT_DIR}"
echo "[INFO] Host      : ${MCP_HOST}"
echo "[INFO] Port      : ${MCP_PORT}"
echo "[INFO] Path      : ${MCP_PATH}"
echo "[INFO] Config dir: ${MCP_CONFIG_DIR}"
echo "[INFO] Endpoint  : http://<this-host>:${MCP_PORT}${MCP_PATH}"

cd "${ROOT_DIR}"
exec "${PYTHON_BIN}" -m src.mcp_server.http_server \
  --config-dir "${MCP_CONFIG_DIR}" \
  --host "${MCP_HOST}" \
  --port "${MCP_PORT}" \
  --path "${MCP_PATH}"
