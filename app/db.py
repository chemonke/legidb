import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from flask import current_app, g
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

SQLITE_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS food_categories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ref_no TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL,
  acidic INTEGER NOT NULL,
  frf INTEGER
);

CREATE TABLE IF NOT EXISTS foods (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  food_category_id INTEGER NOT NULL,
  FOREIGN KEY (food_category_id) REFERENCES food_categories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS simulants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  abbreviation TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS food_category_simulants (
  food_category_id INTEGER NOT NULL,
  simulant_id INTEGER NOT NULL,
  PRIMARY KEY (food_category_id, simulant_id),
  FOREIGN KEY (food_category_id) REFERENCES food_categories(id) ON DELETE CASCADE,
  FOREIGN KEY (simulant_id) REFERENCES simulants(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS substances (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cas_no TEXT NOT NULL UNIQUE,
  fcm_no INTEGER NOT NULL UNIQUE,
  ec_ref_no INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sm_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  substance_id INTEGER NOT NULL,
  fcm_no INTEGER,
  use_as_additive_or_ppa INTEGER NOT NULL,
  use_as_monomer_or_starting_substance INTEGER NOT NULL,
  frf_applicable INTEGER NOT NULL,
  sml REAL,
  restrictions_and_specifications TEXT,
  FOREIGN KEY (substance_id) REFERENCES substances(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS group_restrictions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  group_sml REAL NOT NULL,
  unit TEXT NOT NULL,
  specification TEXT
);

CREATE TABLE IF NOT EXISTS sm_entry_group_restrictions (
  sm_id INTEGER NOT NULL,
  group_restriction_id INTEGER NOT NULL,
  PRIMARY KEY (sm_id, group_restriction_id),
  FOREIGN KEY (sm_id) REFERENCES sm_entries(id) ON DELETE CASCADE,
  FOREIGN KEY (group_restriction_id) REFERENCES group_restrictions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sm_time_conditions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  worst_case_time_minutes INTEGER NOT NULL,
  testing_time_minutes INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sm_temp_conditions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  worst_case_temp_celsius INTEGER NOT NULL,
  testing_temp_celsius INTEGER NOT NULL,
  note TEXT
);
"""

_engine: Optional[Engine] = None


def init_app(app) -> None:
    app.teardown_appcontext(close_connection)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        dsn = current_app.config.get("DATABASE_URL") or os.getenv("DATABASE_URL")
        if not dsn:
            # Default to the same MariaDB DSN used in nix shell to keep behaviour aligned.
            dsn = "mysql+pymysql://legidb:legidb@127.0.0.1:3307/legidb"
        _engine = create_engine(dsn, future=True)
    return _engine


def get_connection():
    conn = g.get("_conn")
    if conn is None:
        conn = get_engine().connect()
        g._conn = conn
    return conn


def close_connection(_=None) -> None:
    conn = g.pop("_conn", None)
    if conn is not None:
        conn.close()


def ensure_bootstrapped() -> None:
    engine = get_engine()
    if engine.url.get_backend_name().startswith("sqlite"):
        db_path = Path(engine.url.database or "legidb.sqlite")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        first_time = not db_path.exists()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.executescript(SQLITE_SCHEMA)
        seed_needed = first_time
        if not seed_needed:
            existing = conn.execute("SELECT COUNT(*) as cnt FROM food_categories").fetchone()
            seed_needed = existing["cnt"] == 0 if existing else True
        if seed_needed:
            seed_from_sqlite(conn, Path(current_app.root_path).parent / "data" / "sample_data.sql")
        conn.commit()
        conn.close()


def seed_from_sqlite(conn: sqlite3.Connection, path: Path) -> None:
    if not path.exists():
        return
    statements: List[str] = []
    current = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--") or stripped.lower().startswith("use "):
            continue
        current.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(current))
            current = []
    for stmt in statements:
        conn.execute(stmt)


def query(sql: str, params: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    result = conn.execute(text(sql), params or {})
    return [dict(row) for row in result.mappings().all()]


def execute(sql: str, params: Dict[str, Any] | None = None) -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})


def get_columns(table: str) -> List[Dict[str, Any]]:
    inspector = inspect(get_engine())
    cols = []
    for col in inspector.get_columns(table):
        cols.append(
            {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
                "primary_key": col.get("primary_key", False),
            }
        )
    return cols
