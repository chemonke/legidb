import os
from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .models import (
    Base,
    Annex1GroupRestriction,
    Food,
    FoodCategory,
    FoodCategorySimulant,
    Simulant,
    SmEntry,
    SmEntryGroupRestriction,
    SmEntryLimit,
    SmCondition,
    Substance,
    SmlKind,
)
from .routes import pages_bp
from .api import api_bp


def create_app():
    # Templates/static live at repo root, not inside the app package.
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    # Needed for Flask-Admin flash/session handling. Override via FLASK_SECRET_KEY.
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

    app.config["DATABASE_URL"] = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://legidb:legidb@localhost:3306/legidb",
    )

    engine = create_engine(app.config["DATABASE_URL"], future=True)
    SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False))

    Base.metadata.create_all(engine)

    _seed_if_empty(SessionLocal)

    app.session = SessionLocal

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    _register_admin(app, SessionLocal)

    @app.teardown_appcontext
    def shutdown_session(response_or_exc):
        SessionLocal.remove()
        return response_or_exc

    return app


def _register_admin(app, SessionLocal):
    """Expose a relational-aware editor via Flask-Admin."""
    admin = Admin(app, name="LegiDB admin", template_mode="bootstrap4", url="/admin")

    class BaseView(ModelView):
        can_view_details = True
        page_size = 50

    def view(model, category, excluded=None):
        attrs = {}
        if excluded:
            attrs["form_excluded_columns"] = excluded
        cls = type(f"{model.__name__}Admin", (BaseView,), attrs)
        return cls(model, SessionLocal, category=category)

    admin.add_view(view(FoodCategory, "Foods", excluded=["foods", "simulants"]))
    admin.add_view(view(Food, "Foods"))
    admin.add_view(view(Simulant, "Foods", excluded=["food_categories"]))
    admin.add_view(view(FoodCategorySimulant, "Foods"))

    admin.add_view(view(Substance, "Substances", excluded=["sm_entries"]))
    admin.add_view(view(SmEntry, "Substances", excluded=["limits", "group_restrictions"]))
    admin.add_view(view(SmEntryLimit, "Substances"))
    admin.add_view(view(Annex1GroupRestriction, "Substances", excluded=["sm_entries"]))
    admin.add_view(view(SmEntryGroupRestriction, "Substances"))
    admin.add_view(view(SmCondition, "Substances"))


def _seed_if_empty(SessionLocal):
    """Populate sample data if the database is empty to keep the demo API usable."""
    session = SessionLocal()
    try:
        has_foods = session.query(Food).count() > 0
        has_substances = session.query(Substance).count() > 0
        if has_foods or has_substances:
            return

        categories = [
            FoodCategory(ref_no="01.01", description="Non-processed food for infants and young children", acidic=False, frf=3),
            FoodCategory(ref_no="01.02", description="Processed cereal-based food for infants and young children", acidic=False, frf=3),
            FoodCategory(ref_no="02.01", description="Fruit juices and nectars", acidic=True, frf=1),
            FoodCategory(ref_no="03.01", description="Milk and dairy products", acidic=False, frf=1),
        ]
        session.add_all(categories)

        simulants = [
            Simulant(name="Simulant A - Ethanol 10%", abbreviation="A"),
            Simulant(name="Simulant B - Acetic acid 3%", abbreviation="B"),
            Simulant(name="Simulant D1 - Ethanol 50%", abbreviation="D1"),
            Simulant(name="Simulant D2 - Sunflower oil", abbreviation="D2"),
        ]
        session.add_all(simulants)
        session.flush()

        junctions = [
            FoodCategorySimulant(food_category_id=1, simulant_id=1),
            FoodCategorySimulant(food_category_id=1, simulant_id=2),
            FoodCategorySimulant(food_category_id=2, simulant_id=1),
            FoodCategorySimulant(food_category_id=2, simulant_id=2),
            FoodCategorySimulant(food_category_id=2, simulant_id=3),
            FoodCategorySimulant(food_category_id=3, simulant_id=1),
            FoodCategorySimulant(food_category_id=3, simulant_id=2),
            FoodCategorySimulant(food_category_id=3, simulant_id=4),
            FoodCategorySimulant(food_category_id=4, simulant_id=1),
            FoodCategorySimulant(food_category_id=4, simulant_id=4),
        ]
        session.add_all(junctions)

        foods = [
            Food(name="Infant formula", food_category_id=1),
            Food(name="Baby cereal", food_category_id=2),
            Food(name="Apple juice", food_category_id=3),
            Food(name="Whole milk", food_category_id=4),
        ]
        session.add_all(foods)

        substances = [
            Substance(smiles="C2H4", cas_no="74-85-1", fcm_no=100, ec_ref_no=200),
            Substance(smiles="C3H6O", cas_no="67-64-1", fcm_no=101, ec_ref_no=201),
        ]
        session.add_all(substances)
        session.flush()

        entries = [
            SmEntry(
                substance_id=substances[0].id,
                fcm_no=100,
                use_as_additive_or_ppa=False,
                use_as_monomer_or_starting_substance=True,
                frf_applicable=True,
                restrictions_and_specifications="Use as monomer; FRF applies",
            ),
            SmEntry(
                substance_id=substances[1].id,
                fcm_no=101,
                use_as_additive_or_ppa=True,
                use_as_monomer_or_starting_substance=False,
                frf_applicable=False,
                restrictions_and_specifications="Additive; no FRF",
            ),
        ]
        session.add_all(entries)
        session.flush()

        limits = [
            SmEntryLimit(sm_entry_id=entries[0].id, kind=SmlKind.SML, value=5.0, raw_expression="5"),
            SmEntryLimit(sm_entry_id=entries[1].id, kind=SmlKind.ND, value=None, raw_expression="ND"),
        ]
        session.add_all(limits)

        group = Annex1GroupRestriction(
            group_restriction_no=1,
            total_limit_value=60.0,
            specification="Group 1 example",
        )
        session.add(group)
        session.flush()
        session.add(SmEntryGroupRestriction(sm_id=entries[0].id, group_restriction_id=group.id))

        session.commit()
        print("Database was empty; inserted sample data.")
    finally:
        session.close()
