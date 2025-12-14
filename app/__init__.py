import os
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .models import Base
from .routes import pages_bp
from .api import api_bp


def create_app():
    # Templates/static live at repo root, not inside the app package.
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    app.config["DATABASE_URL"] = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://legidb:legidb@localhost:3306/legidb",
    )

    engine = create_engine(app.config["DATABASE_URL"], future=True)
    SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False))

    Base.metadata.create_all(engine)

    app.session = SessionLocal

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.teardown_appcontext
    def shutdown_session(response_or_exc):
        SessionLocal.remove()
        return response_or_exc

    return app
