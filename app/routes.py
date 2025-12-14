from collections import OrderedDict
from flask import Blueprint, current_app, render_template, request
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from .models import (
    Annex1GroupRestriction,
    Food,
    FoodCategory,
    FoodCategorySimulant,
    Simulant,
    SmCondition,
    SmEntry,
    SmEntryGroupRestriction,
    SmEntryLimit,
    Substance,
)

pages_bp = Blueprint("pages", __name__)


def _get_session():
    return current_app.session


TABLE_CONFIG = OrderedDict(
    [
        ("food_categories", {"model": FoodCategory, "label": "Food Categories"}),
        ("foods", {"model": Food, "label": "Foods"}),
        ("simulants", {"model": Simulant, "label": "Simulants"}),
        (
            "food_category_simulants",
            {"model": FoodCategorySimulant, "label": "Food ↔ Simulant links"},
        ),
        ("substances", {"model": Substance, "label": "Substances"}),
        ("sm_entries", {"model": SmEntry, "label": "SM Entries"}),
        ("sm_entry_limits", {"model": SmEntryLimit, "label": "SM Entry Limits"}),
        (
            "annex1_group_restrictions",
            {"model": Annex1GroupRestriction, "label": "Annex I group restrictions"},
        ),
        (
            "sm_entry_group_restrictions",
            {"model": SmEntryGroupRestriction, "label": "SM entry ↔ group links"},
        ),
        ("sm_conditions", {"model": SmCondition, "label": "SM conditions"}),
    ]
)


def _describe_columns(model):
    columns = []
    for col in model.__table__.columns:
        col_type = col.type.__class__.__name__.lower()
        enum_values = []
        if hasattr(col.type, "enum_class"):
            enum_values = [e.value for e in col.type.enum_class]
            col_type = "enum"
        elif col_type in ("boolean", "bool"):
            col_type = "bool"
        elif col_type in ("integer", "numeric"):
            col_type = "number"
        columns.append(
            {
                "name": col.name,
                "pk": col.primary_key,
                "nullable": col.nullable,
                "type": col_type,
                "enum_values": enum_values,
            }
        )
    return columns


def _row_to_dict(obj):
    row = {}
    for col in obj.__table__.columns:
        value = getattr(obj, col.name)
        if hasattr(value, "value"):
            value = value.value
        row[col.name] = value
    return row


def _parse_value(col, form):
    raw = form.get(col.name)
    if hasattr(col.type, "enum_class"):
        if raw in (None, ""):
            return None
        return col.type.enum_class(raw)
    if col.type.__class__.__name__.lower() in ("boolean", "bool"):
        return raw in ("1", "true", "on", "yes", "True")
    if raw in (None, ""):
        return None
    col_type = col.type.__class__.__name__.lower()
    if col_type == "integer":
        return int(raw)
    if col_type == "numeric":
        return float(raw)
    return raw


def _assign_fields(obj, form, include_pk=False):
    for col in obj.__table__.columns:
        if col.primary_key and not include_pk:
            continue
        # For booleans unchecked checkboxes won't post; treat missing as False.
        if col.type.__class__.__name__.lower() in ("boolean", "bool") and col.name not in form:
            setattr(obj, col.name, False)
            continue
        if col.name not in form:
            continue
        setattr(obj, col.name, _parse_value(col, form))


def _pk_identity(model, form):
    keys = [col for col in model.__table__.columns if col.primary_key]
    values = [_parse_value(col, form) for col in keys]
    if len(values) == 1:
        return values[0]
    return tuple(values)


@pages_bp.route("/")
def index():
    return render_template("index.html")


@pages_bp.route("/search")
def search():
    q = request.args.get("q", "").strip()
    session = _get_session()

    substances = []
    if q:
        stmt = (
            select(Substance)
            .options(
                selectinload(Substance.sm_entries).selectinload(SmEntry.limits),
                selectinload(Substance.sm_entries).selectinload(SmEntry.group_restrictions),
            )
            .where(
                or_(
                    Substance.cas_no.ilike(f"%{q}%"),
                    Substance.smiles.ilike(f"%{q}%"),
                )
            )
            .order_by(Substance.cas_no)
        )
        substances = session.execute(stmt).scalars().all()

    return render_template(
        "search.html",
        query=q,
        substances=substances,
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


@pages_bp.route("/api")
def api_docs():
    return render_template("api.html")


@pages_bp.route("/editor", methods=["GET", "POST"])
def editor():
    session = _get_session()
    table_key = request.values.get("table") or next(iter(TABLE_CONFIG.keys()))
    table_cfg = TABLE_CONFIG.get(table_key) or TABLE_CONFIG[next(iter(TABLE_CONFIG.keys()))]

    message = None
    error = None

    if request.method == "POST":
        table_key = request.form.get("table", table_key)
        table_cfg = TABLE_CONFIG.get(table_key) or table_cfg
        model = table_cfg["model"]
        action = request.form.get("action")
        try:
            if action == "create":
                obj = model()
                _assign_fields(obj, request.form, include_pk=True)
                session.add(obj)
                session.commit()
                message = f"Created new row in {table_cfg['label']}."
            elif action == "update":
                ident = _pk_identity(model, request.form)
                obj = session.get(model, ident)
                if not obj:
                    raise ValueError("Row not found for update.")
                _assign_fields(obj, request.form, include_pk=False)
                session.commit()
                message = f"Updated row in {table_cfg['label']}."
            elif action == "delete":
                ident = _pk_identity(model, request.form)
                obj = session.get(model, ident)
                if obj:
                    session.delete(obj)
                    session.commit()
                    message = f"Deleted row from {table_cfg['label']}."
                else:
                    raise ValueError("Row not found for delete.")
        except (SQLAlchemyError, ValueError) as exc:
            session.rollback()
            error = str(exc)

    model = table_cfg["model"]
    columns = _describe_columns(model)
    rows = [_row_to_dict(obj) for obj in session.query(model).all()]

    return render_template(
        "editor.html",
        tables=TABLE_CONFIG,
        table_key=table_key,
        columns=columns,
        rows=rows,
        message=message,
        error=error,
    )
