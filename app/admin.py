from dataclasses import dataclass
from typing import Any, Dict, List

from flask import Blueprint, render_template, request

from .db import execute, get_columns, query

bp = Blueprint("admin", __name__, template_folder="templates")


BOOL_COLUMNS = {
    "acidic",
    "use_as_additive_or_ppa",
    "use_as_monomer_or_starting_substance",
    "frf_applicable",
}

TABLE_LABELS = {
    "food_categories": "Food categories",
    "foods": "Foods",
    "simulants": "Simulants",
    "food_category_simulants": "Category ↔ simulant links",
    "substances": "Authorised substances",
    "sm_entries": "Specific migration entries",
    "group_restrictions": "Group restrictions",
    "sm_entry_group_restrictions": "SM entry ↔ group links",
    "sm_time_conditions": "Time conditions",
    "sm_temp_conditions": "Temperature conditions",
}


@dataclass
class Column:
    name: str
    type: str
    pk: bool
    nullable: bool
    enum_values: List[str]


def load_columns(table: str) -> List[Column]:
    columns: List[Column] = []
    for col in get_columns(table):
        col_type = col["type"].lower()
        form_type = "text"
        if col["name"] in BOOL_COLUMNS or "int" in col_type and col["name"].startswith("is_"):
            form_type = "bool"
        columns.append(
            Column(
                name=col["name"],
                type=form_type,
                pk=bool(col.get("primary_key")),
                nullable=col.get("nullable", True),
                enum_values=[],
            )
        )
    return columns


def parse_value(raw: Any, col: Column) -> Any:
    if col.type == "bool":
        return 1 if str(raw) == "1" else 0
    if raw == "" and col.nullable:
        return None
    return raw


@bp.route("/", methods=["GET", "POST"])
def index():
    table_key = request.values.get("table") or next(iter(TABLE_LABELS))
    message = None
    error = None
    columns = load_columns(table_key)

    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "create":
                insert_cols = []
                params: Dict[str, Any] = {}
                for col in columns:
                    val = request.form.get(col.name, "")
                    if col.pk and val == "":
                        continue
                    insert_cols.append(col.name)
                    params[col.name] = parse_value(val, col)
                placeholders = ", ".join(f":{col}" for col in insert_cols)
                execute(
                    f"INSERT INTO {table_key} ({', '.join(insert_cols)}) VALUES ({placeholders})",
                    params,
                )
                message = "Row added."
            elif action == "update":
                pk_parts: List[str] = []
                set_parts: List[str] = []
                params: Dict[str, Any] = {}
                for col in columns:
                    val = request.form.get(col.name, "")
                    if col.pk:
                        pk_parts.append(f"{col.name} = :pk_{col.name}")
                        params[f"pk_{col.name}"] = parse_value(val, col)
                    else:
                        set_parts.append(f"{col.name} = :{col.name}")
                        params[col.name] = parse_value(val, col)
                if pk_parts:
                    execute(
                        f"UPDATE {table_key} SET {', '.join(set_parts)} WHERE {' AND '.join(pk_parts)}",
                        params,
                    )
                    message = "Row updated."
            elif action == "delete":
                pk_parts: List[str] = []
                params: Dict[str, Any] = {}
                for col in columns:
                    if col.pk:
                        val = request.form.get(col.name)
                        pk_parts.append(f"{col.name} = :{col.name}")
                        params[col.name] = parse_value(val, col)
                if pk_parts:
                    execute(f"DELETE FROM {table_key} WHERE {' AND '.join(pk_parts)}", params)
                    message = "Row deleted."
        except Exception as exc:  # pragma: no cover - tiny admin helper
            error = str(exc)

    rows = query(f"SELECT * FROM {table_key}")
    tables: Dict[str, Dict[str, str]] = {
        key: {"label": label} for key, label in TABLE_LABELS.items()
    }

    return render_template(
        "editor.html",
        tables=tables,
        table_key=table_key,
        rows=rows,
        columns=columns,
        message=message,
        error=error,
    )
