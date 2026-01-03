import os
from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin import form as admin_form
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .models import (
    Base,
    Annex1GroupRestriction,
    Food,
    FoodCategory,
    FoodCategorySimulant,
    LimitBasis,
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
        "mysql+pymysql://legidb:legidb@localhost:3307/legidb",
    )

    engine = create_engine(app.config["DATABASE_URL"], future=True)
    SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False))

    Base.metadata.create_all(engine)

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

    class PatchedBaseForm(admin_form.BaseForm):
        """WTForms 3 compatibility: coerce tuple/list flags into a dict."""

        class Meta(admin_form.BaseForm.Meta):
            def bind_field(self, form, unbound_field, options):
                def _as_flag_dict(flag_value):
                    if isinstance(flag_value, (tuple, list)):
                        return {flag: True for flag in flag_value}
                    return flag_value

                def _coerce_validator_flags(validators):
                    for validator in validators:
                        v_flags = getattr(validator, "field_flags", None)
                        coerced_v_flags = _as_flag_dict(v_flags)
                        if coerced_v_flags is not v_flags:
                            validator.field_flags = coerced_v_flags
                    return validators

                flags = options.get("flags")
                coerced_flags = _as_flag_dict(flags)
                if coerced_flags is not flags:
                    options["flags"] = coerced_flags

                uf_flags = getattr(unbound_field, "flags", None)
                if isinstance(uf_flags, (tuple, list)):
                    # WTForms expects a mapping; coerce tuples/lists of flag names.
                    unbound_field.flags = {flag: True for flag in uf_flags}

                # Validators can live on the UnboundField kwargs and not in options;
                # normalize both locations before WTForms copies them.
                if "validators" in unbound_field.kwargs:
                    unbound_field.kwargs["validators"] = _coerce_validator_flags(
                        unbound_field.kwargs["validators"] or []
                    )

                validators = options.get("validators") or []
                options["validators"] = _coerce_validator_flags(validators)
                return super().bind_field(form, unbound_field, options)

    class BaseView(ModelView):
        can_view_details = True
        page_size = 50
        form_base_class = PatchedBaseForm

        def _patch_select_fields(self, form):
            """Ensure iter_choices yields render_kw to satisfy WTForms >=3 select widget."""
            for field in form._fields.values():
                if hasattr(field, "iter_choices"):
                    orig = field.iter_choices

                    def iter_choices(orig_iter=orig):
                        for choice in orig_iter():
                            if len(choice) == 4:
                                yield choice
                            elif len(choice) == 3:
                                val, label, selected = choice
                                yield val, label, selected, {}
                            elif len(choice) == 2:
                                val, label = choice
                                yield val, label, False, {}

                    field.iter_choices = iter_choices
            return form

        def create_form(self, obj=None):
            form = super().create_form(obj)
            return self._patch_select_fields(form)

        def edit_form(self, obj=None):
            form = super().edit_form(obj)
            return self._patch_select_fields(form)

    def view(model, category, excluded=None, **attrs):
        attrs = dict(attrs)
        if excluded:
            attrs["form_excluded_columns"] = excluded
        cls = type(f"{model.__name__}Admin", (BaseView,), attrs)
        return cls(model, SessionLocal, category=category)

    admin.add_view(view(FoodCategory, "Foods", excluded=["foods", "simulants"]))
    admin.add_view(view(Food, "Foods"))
    admin.add_view(view(Simulant, "Foods", excluded=["food_categories"]))
    admin.add_view(
        view(
            FoodCategorySimulant,
            "Foods",
            column_list=("food_category", "simulant"),
            form_columns=("food_category", "simulant"),
            column_labels={
                "food_category": "Food category",
                "simulant": "Simulant",
            },
        )
    )

    admin.add_view(view(Substance, "Substances", excluded=["sm_entries"]))
    admin.add_view(view(SmEntry, "Substances", excluded=["limits", "group_restrictions"]))

    class SmEntryLimitAdmin(BaseView):
        form_choices = {
            "kind": [(k.value, k.value) for k in SmlKind],
            "unit_basis": [(b.value, b.value) for b in LimitBasis],
        }

    admin.add_view(SmEntryLimitAdmin(SmEntryLimit, SessionLocal, category="Substances"))
    admin.add_view(view(Annex1GroupRestriction, "Substances", excluded=["sm_entries"]))
    admin.add_view(
        view(
            SmEntryGroupRestriction,
            "Substances",
            column_list=("sm_entry", "group_restriction"),
            form_columns=("sm_entry", "group_restriction"),
            column_labels={
                "sm_entry": "SM entry",
                "group_restriction": "Group restriction",
            },
        )
    )
    admin.add_view(view(SmCondition, "Substances"))
