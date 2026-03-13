<!-- source: skill参考.md | id: doofy5 -->
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="${ROOT_DIR}/config/nanobot.config.json"
WORKSPACE_DIR="${ROOT_DIR}/gateway/nanobot_workspace"

: "${TELEGRAM_BOT_TOKEN:=YOUR_TELEGRAM_BOT_TOKEN}"
: "${TELEGRAM_ALLOWED_USER_ID:=YOUR_TELEGRAM_USER_ID}"
: "${QWEN_PROVIDER_NAME:=YOUR_PROVIDER_NAME}"
: "${QWEN_MODEL_NAME:=YOUR_QWEN_MODEL_NAME}"
: "${QWEN_API_BASE:=http://127.0.0.1:8000/v1}"
: "${QWEN_API_KEY:=DUMMY_OR_REAL_API_KEY}"

mkdir -p "${WORKSPACE_DIR}"

echo "[INFO] Starting nanobot gateway"
echo "[INFO] Root: ${ROOT_DIR}"
echo "[INFO] Config: ${CONFIG_FILE}"
echo "[INFO] Workspace: ${WORKSPACE_DIR}"

if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "[ERROR] Missing config file: ${CONFIG_FILE}"
  exit 1
fi

# 这里默认你已经安装了 nanobot CLI 或可执行入口
# 如果你本地命令不是 nanobot，请改成实际可执行命令
exec nanobot \
  --config "${CONFIG_FILE}" \
  --workspace "${WORKSPACE_DIR}"
