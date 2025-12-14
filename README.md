# LegiDB (EU 10/2011 helper)

Flask + MariaDB app that mirrors Annex I and Annex III structures from Commission Regulation (EU) 10/2011. It provides a title page, search UI, REST API, and Google Charts graphics.

## Repository layout
- `app/` Flask application factory, routes, API, and SQLAlchemy models.
- `templates/`, `static/` Frontend views, styles, and Google Charts integration.
- `data/schema.sql` MariaDB schema matching `schema.txt`.
- `data/sample_data.sql` Quick seed set for local testing.
- `scripts/seed_data.py` SQLAlchemy-based seeding helper using `DATABASE_URL`.
- `run.py` Entrypoint for local development.
- `flake.nix` Dev shell with Python dependencies.

## Setup
### Ephemeral MariaDB (recommended for reproducible local dev)
1) Option A (simplest): `nix run .#db-start` (nix provides `mysqld`/`mysql` and keeps everything under `/tmp/legidb-mariadb` by default).
2) Option B: `nix develop`, then run `scripts/start_ephemeral_mariadb.sh`.
This boots MariaDB on `127.0.0.1:3307` with socket under `/tmp/legidb-mariadb/mysql.sock` and user/db `legidb`/`legidb`. Nothing is installed globally; delete `/tmp/legidb-mariadb` or run `scripts/stop_ephemeral_mariadb.sh --clean` (or `nix run .#db-stop -- --clean`) to wipe it.
3) Load schema/data (with socket for speed):
```
mysql --socket=/tmp/legidb-mariadb/mysql.sock -u legidb -plegidb legidb < data/schema.sql
mysql --socket=/tmp/legidb-mariadb/mysql.sock -u legidb -plegidb legidb < data/sample_data.sql
```
4) Export the suggested URL from the start script:
```
export DATABASE_URL="mysql+pymysql://legidb:legidb@127.0.0.1:3307/legidb"
```
5) Run the app:
```
python run.py
# or: nix run .#app   (uses the flake-provided Python env; sets PYTHONPATH to repo root)
```
6) Stop and clean:
`nix run .#db-stop` or `scripts/stop_ephemeral_mariadb.sh [--clean]` (with `-- --clean` when using `nix run` to pass the flag through; `--clean` deletes `/tmp/legidb-mariadb`). Set `LEGIDB_BASE_DIR` to override the temp location (must match for start/stop/app).
7) Database admin UI: visit `/admin` for a relational editor (Flask-Admin) with search, filtering, and FK-aware forms.

### Persistent MariaDB (optional)
Provision MariaDB however you like, create the `legidb` user/database, apply `data/schema.sql` and `data/sample_data.sql` (or `DATABASE_URL=... python scripts/seed_data.py`), and set `DATABASE_URL` to point at your instance.

The server exposes:
- `/` title/overview (EU 10/2011 context)
- `/search` search UI for foods/categories
- `/charts` graphics tab using Google Charts
- `/api/foods`, `/api/foods/<id>`, `/api/substances` REST JSON

## Notes
- Models and SQL match `schema.txt` (Annex I & III tables, limits, and group restrictions).
- Google Charts loads from `https://www.gstatic.com/charts/loader.js`; allow outbound access when viewing charts.
