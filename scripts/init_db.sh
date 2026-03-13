#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DB_PATH="${1:-${REPO_ROOT}/data/vision_butler.db}"

SQLITE_BIN=""
if command -v sqlite3 >/dev/null 2>&1; then
  SQLITE_BIN="sqlite3"
elif command -v python3 >/dev/null 2>&1; then
  SQLITE_BIN="python3"
else
  echo "[ERROR] neither sqlite3 nor python3 found in PATH" >&2
  exit 1
fi

mkdir -p "$(dirname "${DB_PATH}")"

echo "[INFO] Initializing DB: ${DB_PATH}"
if [[ "${SQLITE_BIN}" == "sqlite3" ]]; then
  sqlite3 "${DB_PATH}" < "${REPO_ROOT}/schema.sql"
else
  python3 - "${DB_PATH}" "${REPO_ROOT}/schema.sql" <<'PY'
import sqlite3
import sys

db_path = sys.argv[1]
schema_path = sys.argv[2]

with open(schema_path, "r", encoding="utf-8") as f:
    schema = f.read()

con = sqlite3.connect(db_path)
try:
    con.executescript(schema)
    con.commit()
finally:
    con.close()
PY
fi

if [[ "${SQLITE_BIN}" == "sqlite3" ]]; then
  required_tables=(
    users devices observations events object_states zone_states
    media_items audit_logs telegram_updates notification_rules facts ocr_results
  )
  required_fts=(observations_fts events_fts ocr_results_fts)
  required_views=(world_state_view active_notification_rules_view recent_device_health_view)

  for table in "${required_tables[@]}"; do
    found="$(sqlite3 "${DB_PATH}" "SELECT name FROM sqlite_master WHERE type='table' AND name='${table}';")"
    [[ "${found}" == "${table}" ]] || { echo "[ERROR] missing table: ${table}" >&2; exit 1; }
  done

  for fts in "${required_fts[@]}"; do
    found="$(sqlite3 "${DB_PATH}" "SELECT name FROM sqlite_master WHERE type='table' AND name='${fts}';")"
    [[ "${found}" == "${fts}" ]] || { echo "[ERROR] missing fts table: ${fts}" >&2; exit 1; }
  done

  for view in "${required_views[@]}"; do
    found="$(sqlite3 "${DB_PATH}" "SELECT name FROM sqlite_master WHERE type='view' AND name='${view}';")"
    [[ "${found}" == "${view}" ]] || { echo "[ERROR] missing view: ${view}" >&2; exit 1; }
  done

  tg_unique="$(sqlite3 "${DB_PATH}" "PRAGMA index_list('telegram_updates');" | awk -F'|' '$3==1 {print $2}' | wc -l)"
  if [[ "${tg_unique}" -lt 1 ]]; then
    echo "[ERROR] telegram_updates has no UNIQUE index (dedup requirement)" >&2
    exit 1
  fi

  echo "[INFO] Smoke checks"
  sqlite3 "${DB_PATH}" <<'SQL'
SELECT 'tables', COUNT(*) FROM sqlite_master WHERE type='table';
SELECT 'indexes', COUNT(*) FROM sqlite_master WHERE type='index';
SELECT 'views', COUNT(*) FROM sqlite_master WHERE type='view';
SELECT 'fts', COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE '%_fts';
SELECT 'world_state_view', COUNT(*) FROM sqlite_master WHERE type='view' AND name='world_state_view';
SQL
else
  python3 - "${DB_PATH}" <<'PY'
import sqlite3
import sys

db_path = sys.argv[1]
con = sqlite3.connect(db_path)
cur = con.cursor()

required_tables = {
    "users", "devices", "observations", "events", "object_states", "zone_states",
    "media_items", "audit_logs", "telegram_updates", "notification_rules", "facts", "ocr_results",
}
required_fts = {"observations_fts", "events_fts", "ocr_results_fts"}
required_views = {"world_state_view", "active_notification_rules_view", "recent_device_health_view"}

tables = {row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
views = {row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='view'")}

missing_tables = sorted(required_tables - tables)
missing_fts = sorted(required_fts - tables)
missing_views = sorted(required_views - views)
if missing_tables:
    raise SystemExit(f"[ERROR] missing table(s): {', '.join(missing_tables)}")
if missing_fts:
    raise SystemExit(f"[ERROR] missing fts table(s): {', '.join(missing_fts)}")
if missing_views:
    raise SystemExit(f"[ERROR] missing view(s): {', '.join(missing_views)}")

unique_count = 0
for row in cur.execute("PRAGMA index_list('telegram_updates')"):
    if int(row[2]) == 1:
        unique_count += 1
if unique_count < 1:
    raise SystemExit("[ERROR] telegram_updates has no UNIQUE index (dedup requirement)")

print("[INFO] Smoke checks")
print("tables|", cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0], sep="")
print("indexes|", cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'").fetchone()[0], sep="")
print("views|", cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view'").fetchone()[0], sep="")
print("fts|", cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE '%_fts'").fetchone()[0], sep="")
print("world_state_view|", cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view' AND name='world_state_view'").fetchone()[0], sep="")

con.close()
PY
fi

echo "[OK] Database initialized successfully"
