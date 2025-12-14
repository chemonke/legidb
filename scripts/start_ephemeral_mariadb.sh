#!/usr/bin/env bash
# Start an isolated MariaDB instance under /tmp so nothing is installed system-wide.

set -euo pipefail

BASE_DIR="${LEGIDB_BASE_DIR:-/tmp/legidb-mariadb}"
DATA_DIR="$BASE_DIR/data"
SOCKET="$BASE_DIR/mysql.sock"
PID_FILE="$BASE_DIR/mariadb.pid"
LOG_FILE="$BASE_DIR/mariadb.log"
PORT="${PORT:-3307}"

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

cat <<EOF
MariaDB ready on 127.0.0.1:${PORT}
Socket: $SOCKET
PID file: $PID_FILE
Log: $LOG_FILE
Data dir: $DATA_DIR (override with LEGIDB_BASE_DIR if needed)
Suggested export:
  export DATABASE_URL="mysql+pymysql://legidb:legidb@127.0.0.1:${PORT}/legidb"
EOF
