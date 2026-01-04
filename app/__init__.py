import os
from pathlib import Path

from flask import Flask, abort, send_from_directory

from . import admin, api, pages
from .db import ensure_bootstrapped, init_app, ensure_plan_favorites_table


def create_app() -> Flask:
    base_dir = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(base_dir / "templates"),
        static_folder=str(base_dir / "static"),
    )
    docs_dir = base_dir / "docs"

    # Prefer DATABASE_URL env; fallback stays MariaDB default, last resort SQLite in repo.
    app.config.setdefault("DATABASE_URL", os.getenv("DATABASE_URL"))
    if not app.config["DATABASE_URL"]:
        app.config["DATABASE_URL"] = "mysql+pymysql://legidb:legidb@127.0.0.1:3307/legidb"

    init_app(app)
    with app.app_context():
        ensure_bootstrapped()
        ensure_plan_favorites_table()

    @app.route("/docs/<path:filename>")
    def docs_static(filename: str):
        target = docs_dir / filename
        if not target.exists():
            abort(404)
        return send_from_directory(docs_dir, filename)

    app.register_blueprint(pages.bp)
    app.register_blueprint(api.bp, url_prefix="/api")
    app.register_blueprint(admin.bp, url_prefix="/admin")

    return app
