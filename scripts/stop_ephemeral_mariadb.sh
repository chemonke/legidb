#!/bin/bash
# Stop the ephemeral MariaDB instance and optionally clean its data dir.

set -euo pipefail

BASE_DIR="${LEGIDB_BASE_DIR:-/tmp/legidb-mariadb}"
SOCKET="$BASE_DIR/mysql.sock"
PID_FILE="$BASE_DIR/mariadb.pid"
DO_CLEAN="${1:-}"

if [[ -S "$SOCKET" ]]; then
  mysqladmin --socket="$SOCKET" -u root shutdown >/dev/null 2>&1 || true
elif [[ -f "$PID_FILE" ]]; then
  kill "$(cat "$PID_FILE")" >/dev/null 2>&1 || true
fi

if [[ "$DO_CLEAN" == "--clean" ]]; then
  rm -rf "$BASE_DIR"
  echo "Removed $BASE_DIR"
else
  echo "Left data dir intact at $BASE_DIR (pass --clean to remove it)."
fi
