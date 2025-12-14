from flask import Blueprint, current_app, jsonify
from sqlalchemy import select

from .models import Food, FoodCategory, Simulant, Substance

api_bp = Blueprint("api", __name__)


def _get_session():
    return current_app.session


@api_bp.route("/foods")
def foods():
    session = _get_session()
    rows = (
        session.execute(
            select(Food, FoodCategory).join(FoodCategory, Food.food_category_id == FoodCategory.id)
        )
        .all()
    )
    payload = []
    for food, category in rows:
        simulants = [
            {"id": sim.id, "name": sim.name, "abbreviation": sim.abbreviation}
            for sim in category.simulants
        ]
        payload.append(
            {
                "id": food.id,
                "name": food.name,
                "category": {
                    "id": category.id,
                    "ref_no": category.ref_no,
                    "description": category.description,
                },
                "simulants": simulants,
            }
        )
    return jsonify(payload)


@api_bp.route("/foods/<int:food_id>")
def food_detail(food_id: int):
    session = _get_session()
    food = session.get(Food, food_id)
    if not food:
        return jsonify({"error": "not found"}), 404

    category = session.get(FoodCategory, food.food_category_id)
    simulants = [
        {"id": sim.id, "name": sim.name, "abbreviation": sim.abbreviation}
        for sim in category.simulants
    ]
    return jsonify(
        {
            "id": food.id,
            "name": food.name,
            "category": {
                "id": category.id,
                "ref_no": category.ref_no,
                "description": category.description,
            },
            "simulants": simulants,
        }
    )


@api_bp.route("/substances")
def substances():
    session = _get_session()
    rows = session.execute(select(Substance)).scalars().all()
    payload = [
        {
            "id": sub.id,
            "smiles": sub.smiles,
            "cas_no": sub.cas_no,
            "fcm_no": sub.fcm_no,
            "ec_ref_no": sub.ec_ref_no,
        }
        for sub in rows
    ]
    return jsonify(payload)
