from flask import Blueprint, current_app, render_template, request
from sqlalchemy import or_, select

from .models import Food, FoodCategory, Simulant

pages_bp = Blueprint("pages", __name__)


def _get_session():
    return current_app.session


@pages_bp.route("/")
def index():
    return render_template("index.html")


@pages_bp.route("/search")
def search():
    q = request.args.get("q", "").strip()
    session = _get_session()

    foods = []
    if q:
        stmt = (
            select(Food)
            .join(FoodCategory)
            .where(
                or_(
                    Food.name.ilike(f"%{q}%"),
                    FoodCategory.description.ilike(f"%{q}%"),
                    FoodCategory.ref_no.ilike(f"%{q}%"),
                )
            )
            .order_by(Food.name)
        )
        foods = session.execute(stmt).scalars().all()

    categories = session.execute(select(FoodCategory).order_by(FoodCategory.ref_no)).scalars().all()

    return render_template(
        "search.html",
        query=q,
        foods=foods,
        categories=categories,
    )


@pages_bp.route("/charts")
def charts():
    session = _get_session()
    category_counts = (
        session.execute(
            select(FoodCategory.ref_no, FoodCategory.description, FoodCategory.id, FoodCategory.frf)
        )
        .all()
    )
    simulant_counts = (
        session.execute(
            select(Simulant.name, Simulant.abbreviation, Simulant.id)
        )
        .all()
    )

    foods_per_category = []
    for ref_no, description, cat_id, frf in category_counts:
        total = session.query(Food).filter(Food.food_category_id == cat_id).count()
        foods_per_category.append((ref_no, description, total, frf))

    simulants_per_category = []
    for sim_name, sim_abbr, sim_id in simulant_counts:
        join_count = (
            session.query(FoodCategory)
            .join(FoodCategory.simulants)
            .filter(Simulant.id == sim_id)
            .count()
        )
        simulants_per_category.append((sim_abbr, sim_name, join_count))

    return render_template(
        "charts.html",
        foods_per_category=foods_per_category,
        simulants_per_category=simulants_per_category,
    )
