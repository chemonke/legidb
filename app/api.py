import json
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request

from .db import execute, query

bp = Blueprint("api", __name__)


@bp.route("/foods")
def foods():
    foods = query(
        """
        SELECT f.id, f.name, fc.id as category_id, fc.ref_no, fc.description, fc.frf, fc.acidic
        FROM foods f
        JOIN food_categories fc ON fc.id = f.food_category_id
        ORDER BY f.name
        """
    )
    payload: List[Dict[str, Any]] = []
    for row in foods:
        simulants = query(
            """
            SELECT s.name, s.abbreviation
            FROM simulants s
            JOIN food_category_simulants fcs ON fcs.simulant_id = s.id
            WHERE fcs.food_category_id = :cat_id
            """,
            {"cat_id": row["category_id"]},
        )
        payload.append(
            {
                "id": row["id"],
                "name": row["name"],
                "category_ref_no": row["ref_no"],
                "category_description": row["description"],
                "frf": row["frf"],
                "acidic": bool(row["acidic"]),
                "simulants": [dict(sim) for sim in simulants],
            }
        )
    return jsonify(payload)


@bp.route("/foods/<int:food_id>")
def food(food_id: int):
    rows = query(
        """
        SELECT f.id, f.name, fc.ref_no, fc.description, fc.frf, fc.acidic, fc.id as category_id
        FROM foods f
        JOIN food_categories fc ON fc.id = f.food_category_id
        WHERE f.id = :food_id
        """,
        {"food_id": food_id},
    )
    row = rows[0] if rows else None
    if not row:
        return jsonify({"error": "not found"}), 404
    simulants = query(
        """
        SELECT s.name, s.abbreviation
        FROM simulants s
        JOIN food_category_simulants fcs ON fcs.simulant_id = s.id
        WHERE fcs.food_category_id = :cat_id
        """,
        {"cat_id": row["category_id"]},
    )
    return jsonify(
        {
            "id": row["id"],
            "name": row["name"],
            "category_ref_no": row["ref_no"],
            "category_description": row["description"],
            "frf": row["frf"],
            "acidic": bool(row["acidic"]),
            "simulants": [dict(sim) for sim in simulants],
        }
    )


@bp.route("/substances")
def substances():
    rows = query("SELECT id, cas_no, fcm_no, ec_ref_no FROM substances ORDER BY cas_no")
    return jsonify([dict(r) for r in rows])


@bp.route("/suggest/foods")
def suggest_foods():
    q = (request.args.get("q") or "").strip()
    like = f"%{q}%"
    rows = query(
        """
        SELECT f.id, f.name, fc.ref_no, fc.description
        FROM foods f
        JOIN food_categories fc ON fc.id = f.food_category_id
        WHERE f.name LIKE :like OR fc.ref_no LIKE :like
        ORDER BY f.name
        LIMIT 8
        """,
        {"like": like},
    )
    return jsonify(
        [
            {
                "id": row["id"],
                "label": f"{row['name']} (Annex III {row['ref_no']})",
                "ref_no": row["ref_no"],
                "name": row["name"],
            }
            for row in rows
        ]
    )


@bp.route("/suggest/substances")
def suggest_substances():
    q = (request.args.get("q") or "").strip()
    like = f"%{q}%"
    rows = query(
        """
        SELECT id, cas_no, fcm_no, ec_ref_no
        FROM substances
        WHERE cas_no LIKE :like OR CAST(fcm_no AS CHAR) LIKE :like OR CAST(ec_ref_no AS CHAR) LIKE :like
        ORDER BY cas_no
        LIMIT 8
        """,
        {"like": like},
    )
    return jsonify(
        [
            {
                "id": row["id"],
                "label": f"CAS {row['cas_no']} · FCM {row['fcm_no']} · EC {row['ec_ref_no']}",
            }
            for row in rows
        ]
    )


@bp.route("/generate-plan", methods=["POST"])
def generate_plan():
    payload = request.get_json(silent=True) or {}
    food_ids = payload.get("food_ids") or []
    substance_ids = payload.get("substance_ids") or []
    worst_case_time_input = payload.get("worst_case_time_minutes")
    worst_case_temp_input = payload.get("worst_case_temp_celsius")
    condition_inputs = payload.get("conditions")

    def coerce_int(val):
        try:
            return int(val)
        except (TypeError, ValueError):
            return None

    foods = []
    if food_ids:
        placeholders = ", ".join(f":food_id_{i}" for i in range(len(food_ids)))
        rows = query(
            f"""
            SELECT f.id, f.name, fc.id as category_id, fc.ref_no, fc.description, fc.frf, fc.acidic
            FROM foods f
            JOIN food_categories fc ON fc.id = f.food_category_id
            WHERE f.id IN ({placeholders})
            """,
            {f"food_id_{i}": fid for i, fid in enumerate(food_ids)},
        )
        for row in rows:
            simulants = query(
                """
                SELECT s.name, s.abbreviation
                FROM simulants s
                JOIN food_category_simulants fcs ON fcs.simulant_id = s.id
                WHERE fcs.food_category_id = :cat_id
                """,
                {"cat_id": row["category_id"]},
            )
            foods.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "ref_no": row["ref_no"],
                    "description": row["description"],
                    "frf": row["frf"],
                    "acidic": bool(row["acidic"]),
                    "simulants": [dict(sim) for sim in simulants],
                }
            )

    substances_details = []
    if substance_ids:
        placeholders = ", ".join(f":sub_id_{i}" for i in range(len(substance_ids)))
        subs = query(
            f"""
            SELECT s.id, s.cas_no, s.fcm_no, s.ec_ref_no,
                   se.id AS sm_entry_id,
                   se.use_as_additive_or_ppa,
                   se.use_as_monomer_or_starting_substance,
                   se.frf_applicable,
                   se.sml,
                   se.restrictions_and_specifications
            FROM substances s
            LEFT JOIN sm_entries se ON se.substance_id = s.id
            WHERE s.id IN ({placeholders})
            """,
            {f"sub_id_{i}": sid for i, sid in enumerate(substance_ids)},
        )
        for row in subs:
            group_limits = []
            if row["sm_entry_id"]:
                group_limits = query(
                    """
                    SELECT gr.id AS group_restriction_id, gr.group_sml, gr.unit, gr.specification
                    FROM group_restrictions gr
                    JOIN sm_entry_group_restrictions sgr ON sgr.group_restriction_id = gr.id
                    WHERE sgr.sm_id = :sm_id
                    """,
                    {"sm_id": row["sm_entry_id"]},
                )
            substances_details.append(
                {
                    "id": row["id"],
                    "cas_no": row["cas_no"],
                    "fcm_no": row["fcm_no"],
                    "ec_ref_no": row["ec_ref_no"],
                    "use_as_additive_or_ppa": bool(row["use_as_additive_or_ppa"]) if row["use_as_additive_or_ppa"] is not None else None,
                    "use_as_monomer_or_starting_substance": bool(row["use_as_monomer_or_starting_substance"]) if row["use_as_monomer_or_starting_substance"] is not None else None,
                    "frf_applicable": bool(row["frf_applicable"]) if row["frf_applicable"] is not None else None,
                    "sml": row["sml"],
                    "restrictions_and_specifications": row["restrictions_and_specifications"],
                    "group_limits": [dict(gl) for gl in group_limits],
                }
            )

    time_conditions = [dict(row) for row in query("SELECT * FROM sm_time_conditions ORDER BY worst_case_time_minutes")]
    temp_conditions = [dict(row) for row in query("SELECT * FROM sm_temp_conditions ORDER BY worst_case_temp_celsius")]

    def pick_condition(value, rows, key):
        if value is None or not rows:
            return None
        for row in rows:
            if value <= row[key]:
                return row
        return rows[-1]

    # Support both the legacy single time/temp payload and the new multi-row payload.
    if isinstance(condition_inputs, list):
        raw_conditions = condition_inputs
    else:
        raw_conditions = [
            {
                "worst_case_time_minutes": worst_case_time_input,
                "worst_case_temp_celsius": worst_case_temp_input,
            }
        ]

    condition_results = []
    for cond in raw_conditions:
        wc_time_val = coerce_int(cond.get("worst_case_time_minutes"))
        wc_temp_val = coerce_int(cond.get("worst_case_temp_celsius"))
        input_time_raw = coerce_int(cond.get("input_time_raw"))
        input_time_unit = cond.get("input_time_unit") or "minutes"
        condition_results.append(
            {
                "worst_case_time_minutes": wc_time_val,
                "worst_case_temp_celsius": wc_temp_val,
                "input_time_raw": input_time_raw if input_time_raw is not None else wc_time_val,
                "input_time_unit": input_time_unit or "minutes",
                "selected_time_condition": pick_condition(wc_time_val, time_conditions, "worst_case_time_minutes"),
                "selected_temp_condition": pick_condition(wc_temp_val, temp_conditions, "worst_case_temp_celsius"),
            }
        )

    # Keep legacy keys for backward compatibility (first row only).
    first_cond = condition_results[0] if condition_results else {"worst_case_time_minutes": None, "worst_case_temp_celsius": None, "selected_time_condition": None, "selected_temp_condition": None}

    return jsonify(
        {
            "foods": foods,
            "substances": substances_details,
            "time_conditions": time_conditions,
            "temp_conditions": temp_conditions,
            "conditions": condition_results,
            "selected_time_condition": first_cond["selected_time_condition"],
            "selected_temp_condition": first_cond["selected_temp_condition"],
            "worst_case_time_minutes": first_cond["worst_case_time_minutes"],
            "worst_case_temp_celsius": first_cond["worst_case_temp_celsius"],
        }
    )


@bp.route("/favorites", methods=["GET"])
def list_favorites():
    rows = query("SELECT id, name, created_at FROM plan_favorites ORDER BY created_at DESC")
    return jsonify(rows)


@bp.route("/favorites/<int:fav_id>", methods=["GET"])
def get_favorite(fav_id: int):
    rows = query(
        "SELECT id, name, payload, created_at FROM plan_favorites WHERE id = :id",
        {"id": fav_id},
    )
    if not rows:
        return jsonify({"error": "not found"}), 404
    row = rows[0]
    try:
        payload = json.loads(row["payload"])
    except Exception:
        payload = None
    return jsonify({"id": row["id"], "name": row["name"], "created_at": row["created_at"], "plan": payload})


@bp.route("/favorites", methods=["POST"])
def create_favorite():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    plan = payload.get("plan")
    if not name:
        return jsonify({"error": "name is required"}), 400
    if plan is None:
        return jsonify({"error": "plan payload is required"}), 400
    execute(
        "INSERT INTO plan_favorites (name, payload) VALUES (:name, :payload)",
        {"name": name, "payload": json.dumps(plan)},
    )
    # Return updated list for convenience.
    rows = query("SELECT id, name, created_at FROM plan_favorites ORDER BY created_at DESC")
    return jsonify(rows), 201
