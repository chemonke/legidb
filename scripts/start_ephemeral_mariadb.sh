#!/usr/bin/env bash
# Start an isolated MariaDB instance under /tmp so nothing is installed system-wide.

set -euo pipefail

BASE_DIR="${LEGIDB_BASE_DIR:-/tmp/legidb-mariadb}"
DATA_DIR="$BASE_DIR/data"
SOCKET="$BASE_DIR/mysql.sock"
PID_FILE="$BASE_DIR/mariadb.pid"
LOG_FILE="$BASE_DIR/mariadb.log"
PORT="${PORT:-3307}"
SCHEMA_ARG=""
SAMPLE_ARG=""
# Allow explicit schema/sample overrides (used by flake to pass store paths).
while [[ $# -gt 0 ]]; do
  case "$1" in
    --schema-sql)
      SCHEMA_ARG="$2"
      shift 2
      ;;
    --sample-sql)
      SAMPLE_ARG="$2"
      shift 2
      ;;
    *)
      break
      ;;
  esac
done
# Try to locate the repo root to find schema/sample files:
# 1) LEGIDB_ROOT override
# 2) Current working dir if it has data/schema.sql
# 3) git rev-parse (when available)
# 4) Script location fallback (works when running the script directly from the repo)
if [[ -n "${LEGIDB_ROOT:-}" ]]; then
  REPO_ROOT="$LEGIDB_ROOT"
elif [[ -f "$PWD/data/schema.sql" ]]; then
  REPO_ROOT="$PWD"
else
  REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  if [[ -z "$REPO_ROOT" ]]; then
    REPO_ROOT="$(cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  fi
fi
SCHEMA_SQL="$REPO_ROOT/data/schema.sql"
SAMPLE_SQL="$REPO_ROOT/data/sample_data.sql"
# Allow overrides (used by flake/env to point at store copies).
if [[ -n "$SCHEMA_ARG" ]]; then
  SCHEMA_SQL="$SCHEMA_ARG"
elif [[ -n "${LEGIDB_SCHEMA_SQL:-}" ]]; then
  SCHEMA_SQL="$LEGIDB_SCHEMA_SQL"
fi

if [[ -n "$SAMPLE_ARG" ]]; then
  SAMPLE_SQL="$SAMPLE_ARG"
elif [[ -n "${LEGIDB_SAMPLE_SQL:-}" ]]; then
  SAMPLE_SQL="$LEGIDB_SAMPLE_SQL"
fi

mkdir -p "$DATA_DIR"

INSTALL_DB_BIN="$(command -v mariadb-install-db || true)"
if [[ -z "$INSTALL_DB_BIN" ]]; then
  INSTALL_DB_BIN="$(command -v mysql_install_db || true)"
fi

if [[ -z "$INSTALL_DB_BIN" ]]; then
  echo "Could not find mariadb-install-db/mysql_install_db on PATH" >&2
  exit 1
fi

# Initialize data dir once; retry without auth flag if the first attempt fails.
if [[ ! -d "$DATA_DIR/mysql" ]]; then
  echo "Initializing MariaDB data dir at $DATA_DIR"
  set +e
  "$INSTALL_DB_BIN" --no-defaults --datadir="$DATA_DIR" --auth-root-authentication-method=normal >/dev/null 2>&1
  INIT_STATUS=$?
  if [[ $INIT_STATUS -ne 0 ]]; then
    echo "Retrying init without --auth-root-authentication-method flag"
    "$INSTALL_DB_BIN" --no-defaults --datadir="$DATA_DIR" >/dev/null
  fi
  set -e
fi

MYSQLD_BIN="$(command -v mariadbd || command -v mysqld)"

if [[ -z "$MYSQLD_BIN" ]]; then
  echo "Could not find mariadbd/mysqld on PATH" >&2
  exit 1
fi

# MariaDB 11.x drops --daemonize; run it in the background explicitly instead.
"$MYSQLD_BIN" \
  --no-defaults \
  --datadir="$DATA_DIR" \
  --socket="$SOCKET" \
  --port="$PORT" \
  --pid-file="$PID_FILE" \
  --bind-address=127.0.0.1 \
  --skip-name-resolve \
  --log-error="$LOG_FILE" \
  --skip-networking=0 \
  --symbolic-links=0 &
MYSQLD_PID=$!
echo "$MYSQLD_PID" >"$PID_FILE"

# Wait for mysqld to accept connections.
READY=0
for _ in {1..30}; do
  if mysqladmin --socket="$SOCKET" ping --silent >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 1
done

if [[ $READY -ne 1 ]]; then
  echo "MariaDB failed to start within timeout. See log: $LOG_FILE" >&2
  exit 1
fi

mysql --socket="$SOCKET" -u root <<'SQL'
CREATE DATABASE IF NOT EXISTS legidb;
CREATE USER IF NOT EXISTS 'legidb'@'localhost' IDENTIFIED BY 'legidb';
GRANT ALL ON legidb.* TO 'legidb'@'localhost';
CREATE USER IF NOT EXISTS 'legidb'@'127.0.0.1' IDENTIFIED BY 'legidb';
GRANT ALL ON legidb.* TO 'legidb'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL

# Apply schema every time (idempotent) and load sample data on an empty DB.
if [[ -f "$SCHEMA_SQL" ]]; then
  mysql --socket="$SOCKET" -u root <"$SCHEMA_SQL"
else
  echo "Warning: $SCHEMA_SQL not found; skipping schema load" >&2
fi

if [[ -f "$SAMPLE_SQL" ]]; then
  EXISTING_ROWS=$(mysql --socket="$SOCKET" -N -B -u root -e "SELECT COUNT(*) FROM legidb.food_categories;" 2>/dev/null || echo 0)
  if [[ "${EXISTING_ROWS:-0}" -eq 0 ]]; then
    mysql --socket="$SOCKET" -u root legidb <"$SAMPLE_SQL"
    echo "Loaded sample data from $SAMPLE_SQL"
  else
    echo "Skipping sample data load; legidb.food_categories already has $EXISTING_ROWS rows"
  fi
else
  echo "Warning: $SAMPLE_SQL not found; skipping sample data load" >&2
fi

cat <<EOF
MariaDB ready on 127.0.0.1:${PORT}
Socket: $SOCKET
PID file: $PID_FILE
Log: $LOG_FILE
Data dir: $DATA_DIR (override with LEGIDB_BASE_DIR if needed)
Suggested export:
  export DATABASE_URL="mysql+pymysql://legidb:legidb@127.0.0.1:${PORT}/legidb"
EOF
