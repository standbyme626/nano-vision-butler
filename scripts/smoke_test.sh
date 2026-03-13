#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TMP_DIR="$(mktemp -d -t vision_butler_smoke_XXXXXX)"
CONFIG_DIR="${TMP_DIR}/config"
DB_PATH="${TMP_DIR}/smoke_test.db"

cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

mkdir -p "${CONFIG_DIR}"

python3 - "${REPO_ROOT}" "${CONFIG_DIR}" "${DB_PATH}" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

import yaml

repo_root = Path(sys.argv[1])
config_dir = Path(sys.argv[2])
db_path = Path(sys.argv[3])

source_config = repo_root / "config"
for name in [
    "settings.yaml",
    "policies.yaml",
    "access.yaml",
    "devices.yaml",
    "cameras.yaml",
    "aliases.yaml",
]:
    content = yaml.safe_load((source_config / name).read_text(encoding="utf-8"))
    if name == "settings.yaml":
        content["database"]["path"] = str(db_path)
    if name == "access.yaml":
        content["telegram_allowlist"]["user_ids"] = ["42"]
        content["user_roles"] = {"42": "owner"}
    (config_dir / name).write_text(
        yaml.safe_dump(content, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
PY

echo "[SMOKE] 1/3 初始化数据库"
"${REPO_ROOT}/scripts/init_db.sh" "${DB_PATH}" >/dev/null

echo "[SMOKE] 2/3 校验 /healthz"
echo "[SMOKE] 3/3 校验核心查询路由 /memory/world-state"
python3 - "${CONFIG_DIR}" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

from src.app import create_app

config_dir = Path(sys.argv[1])
app = create_app(config_dir=config_dir)
client = TestClient(app)
client.__enter__()
try:
    health = client.get("/healthz")
    if health.status_code != 200 or not health.json().get("ok"):
        raise SystemExit(f"/healthz failed: status={health.status_code}, body={health.text}")

    world = client.get("/memory/world-state")
    if world.status_code != 200 or not world.json().get("ok"):
        raise SystemExit(f"/memory/world-state failed: status={world.status_code}, body={world.text}")
finally:
    client.__exit__(None, None, None)
PY

echo "[SMOKE] OK"
