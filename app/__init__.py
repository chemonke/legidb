import os
from pathlib import Path

from flask import Flask

from . import admin, api, pages
from .db import ensure_bootstrapped, init_app


def create_app() -> Flask:
    base_dir = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(base_dir / "templates"),
        static_folder=str(base_dir / "static"),
    )

    # Prefer DATABASE_URL env; fallback stays MariaDB default, last resort SQLite in repo.
    app.config.setdefault("DATABASE_URL", os.getenv("DATABASE_URL"))
    if not app.config["DATABASE_URL"]:
        app.config["DATABASE_URL"] = "mysql+pymysql://legidb:legidb@127.0.0.1:3307/legidb"

    init_app(app)
    with app.app_context():
        ensure_bootstrapped()

    app.register_blueprint(pages.bp)
    app.register_blueprint(api.bp, url_prefix="/api")
    app.register_blueprint(admin.bp, url_prefix="/admin")

    return app
