from pathlib import Path
from typing import Any, Dict, List, Tuple

from flask import Blueprint, render_template, request

from .db import query

bp = Blueprint("pages", __name__)


@bp.route("/")
def index():
    rows = query(
        """
        SELECT
          (SELECT COUNT(*) FROM substances) AS substances,
          (SELECT COUNT(*) FROM foods) AS foods,
          (SELECT COUNT(*) FROM food_categories) AS categories
        """
    )
    totals = rows[0] if rows else None
    return render_template("index.html", totals=totals)


@bp.route("/search")
def search():
    q = (request.args.get("q") or "").strip()
    substances: List[Dict[str, Any]] = []
    if q:
        like = f"%{q}%"
        rows = query(
            """
            SELECT s.id, s.cas_no, s.fcm_no, s.ec_ref_no,
                   se.use_as_additive_or_ppa, se.use_as_monomer_or_starting_substance,
                   se.frf_applicable, se.sml, se.restrictions_and_specifications,
                   se.id AS sm_entry_id
            FROM substances s
            LEFT JOIN sm_entries se ON se.substance_id = s.id
            WHERE s.cas_no LIKE :like OR CAST(s.fcm_no AS CHAR) LIKE :like OR CAST(s.ec_ref_no AS CHAR) LIKE :like
            ORDER BY s.cas_no
            """,
            {"like": like},
        )
        for row in rows:
            group_limits = []
            if row["sm_entry_id"]:
                group_limits = query(
                    """
                    SELECT gr.group_sml, gr.unit, gr.specification
                    FROM group_restrictions gr
                    JOIN sm_entry_group_restrictions sgr ON sgr.group_restriction_id = gr.id
                    WHERE sgr.sm_id = :sm_id
                    """,
                    {"sm_id": row["sm_entry_id"]},
                )
            substances.append(
                {
                    "cas_no": row["cas_no"],
                    "fcm_no": row["fcm_no"],
                    "ec_ref_no": row["ec_ref_no"],
                    "use_as_additive_or_ppa": bool(row["use_as_additive_or_ppa"]) if row["use_as_additive_or_ppa"] is not None else None,
                    "use_as_monomer_or_starting_substance": bool(row["use_as_monomer_or_starting_substance"]) if row["use_as_monomer_or_starting_substance"] is not None else None,
                    "frf_applicable": bool(row["frf_applicable"]) if row["frf_applicable"] is not None else None,
                    "sml": row["sml"],
                    "restrictions_and_specifications": row["restrictions_and_specifications"],
                    "group_limits": group_limits,
                }
            )
    return render_template("search.html", substances=substances, query=q)


@bp.route("/charts")
def charts():
    foods_per_category: List[Tuple] = query(
        """
        SELECT fc.ref_no, fc.description, COUNT(f.id) as total, fc.frf
        FROM food_categories fc
        LEFT JOIN foods f ON f.food_category_id = fc.id
        GROUP BY fc.id
        ORDER BY fc.ref_no
        """
    )
    simulants_per_category: List[Tuple] = query(
        """
        SELECT s.abbreviation, s.name, COUNT(fcs.food_category_id) as total
        FROM simulants s
        LEFT JOIN food_category_simulants fcs ON fcs.simulant_id = s.id
        GROUP BY s.id
        ORDER BY total DESC
        """
    )
    return render_template(
        "charts.html",
        foods_per_category=foods_per_category,
        simulants_per_category=simulants_per_category,
    )


@bp.route("/api")
def api_docs():
    return render_template("api.html")


@bp.route("/about")
def about():
    readme_path = Path(bp.root_path).parent / "README.md"
    try:
        raw = readme_path.read_text()
        try:
            import markdown

            readme_html = markdown.markdown(raw)
        except Exception:
            readme_html = f"<pre>{raw}</pre>"
        return render_template("about.html", readme_html=readme_html, readme_error=None)
    except FileNotFoundError as exc:
        return render_template(
            "about.html", readme_html=None, readme_error=f"README not found: {exc}"
        )


@bp.route("/plan")
def plan():
    latest_time_rows = query(
        "SELECT worst_case_time_minutes FROM sm_time_conditions ORDER BY worst_case_time_minutes DESC LIMIT 1"
    )
    latest_temp_rows = query(
        "SELECT worst_case_temp_celsius FROM sm_temp_conditions ORDER BY worst_case_temp_celsius DESC LIMIT 1"
    )
    latest_time = latest_time_rows[0] if latest_time_rows else None
    latest_temp = latest_temp_rows[0] if latest_temp_rows else None
    return render_template(
        "plan.html",
        baseline_time=latest_time["worst_case_time_minutes"] if latest_time else None,
        baseline_temp=latest_temp["worst_case_temp_celsius"] if latest_temp else None,
    )
