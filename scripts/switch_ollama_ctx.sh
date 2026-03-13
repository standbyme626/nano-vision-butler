#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROD_CFG="${ROOT_DIR}/config/runtime/nanobot.config.json"
DEV_CFG="${ROOT_DIR}/config/runtime/nanobot.dev.config.json"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/switch_ollama_ctx.sh status
  ./scripts/switch_ollama_ctx.sh 32k [--restart]
  ./scripts/switch_ollama_ctx.sh 64k [--restart]

Behavior:
  - 32k -> model qwen3.5:4b-32k
  - 64k -> model qwen3.5:4b-64k
  - updates both runtime configs (prod/dev)
  - optional --restart runs ./scripts/stack_ctl.sh restart
EOF
}

MODE="${1:-status}"
RESTART="${2:-}"

case "${MODE}" in
  32k)
    TARGET_MODEL="qwen3.5:4b-32k"
    ;;
  64k)
    TARGET_MODEL="qwen3.5:4b-64k"
    ;;
  status)
    TARGET_MODEL=""
    ;;
  *)
    usage
    exit 1
    ;;
esac

if [[ "${MODE}" == "status" ]]; then
  python3 - "${PROD_CFG}" "${DEV_CFG}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

prod = Path(sys.argv[1])
dev = Path(sys.argv[2])

for label, path in [("prod", prod), ("dev", dev)]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    defaults = (payload.get("agents") or {}).get("defaults") or {}
    provider = defaults.get("provider")
    model = defaults.get("model")
    api_base = ((payload.get("providers") or {}).get("custom") or {}).get("apiBase")
    print(f"{label}: provider={provider} model={model} custom.apiBase={api_base}")
PY
  exit 0
fi

python3 - "${TARGET_MODEL}" "${PROD_CFG}" "${DEV_CFG}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

target_model = sys.argv[1]
files = [Path(p) for p in sys.argv[2:]]

for path in files:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.setdefault("agents", {}).setdefault("defaults", {})
    payload["agents"]["defaults"]["provider"] = "custom"
    payload["agents"]["defaults"]["model"] = target_model

    providers = payload.setdefault("providers", {})
    providers.setdefault("custom", {})
    providers["custom"]["apiBase"] = "http://100.90.236.32:11434/v1"
    providers["custom"]["apiKey"] = "no-key"

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"updated {path} -> {target_model}")
PY

if [[ "${RESTART}" == "--restart" ]]; then
  "${ROOT_DIR}/scripts/stack_ctl.sh" restart
fi

