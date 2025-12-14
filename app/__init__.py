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

    class SmEntryLimitAdmin(BaseView):
        form_choices = {
            "kind": [(k.value, k.value) for k in SmlKind],
            "unit_basis": [(b.value, b.value) for b in LimitBasis],
        }

    admin.add_view(SmEntryLimitAdmin(SmEntryLimit, SessionLocal, category="Substances"))
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
            FoodCategory(ref_no="01.01A", description="Clear non-alcoholic drinks (water, infusions, soft drinks)", acidic=True, frf=1),
            FoodCategory(ref_no="01.01B", description="Cloudy non-alcoholic drinks with pulp or chocolate", acidic=True, frf=1),
            FoodCategory(ref_no="01.02", description="Alcoholic beverages between 6 % vol and 20 % vol", acidic=False, frf=1),
            FoodCategory(ref_no="01.03", description="Alcoholic beverages above 20 % vol and cream liqueurs", acidic=False, frf=1),
            FoodCategory(ref_no="02.01", description="Starches (dry powders)", acidic=False, frf=None),
            FoodCategory(ref_no="02.05A", description="Dry pastry, biscuits, cakes with fatty surface", acidic=False, frf=3),
            FoodCategory(ref_no="03.01", description="Chocolate and chocolate-coated products", acidic=False, frf=3),
        ]
        session.add_all(categories)

        simulants = [
            Simulant(name="Ethanol 10% (v/v)", abbreviation="A"),
            Simulant(name="Acetic acid 3% (w/v)", abbreviation="B"),
            Simulant(name="Ethanol 20% (v/v)", abbreviation="C"),
            Simulant(name="Ethanol 50% (v/v)", abbreviation="D1"),
            Simulant(name="Vegetable oil (<1% unsaponifiable matter)", abbreviation="D2"),
            Simulant(name="poly(2,6-diphenyl-p-phenylene oxide), 60-80 mesh, 200 nm pores", abbreviation="E"),
        ]
        session.add_all(simulants)
        session.flush()

        cat_by_ref = {cat.ref_no: cat.id for cat in categories}
        sim_by_abbr = {sim.abbreviation: sim.id for sim in simulants}

        junctions = [
            FoodCategorySimulant(food_category_id=cat_by_ref["01.01A"], simulant_id=sim_by_abbr["B"]),
            FoodCategorySimulant(food_category_id=cat_by_ref["01.01A"], simulant_id=sim_by_abbr["C"]),
            FoodCategorySimulant(food_category_id=cat_by_ref["01.01B"], simulant_id=sim_by_abbr["B"]),
            FoodCategorySimulant(food_category_id=cat_by_ref["01.01B"], simulant_id=sim_by_abbr["D1"]),
            FoodCategorySimulant(food_category_id=cat_by_ref["01.02"], simulant_id=sim_by_abbr["C"]),
            FoodCategorySimulant(food_category_id=cat_by_ref["01.03"], simulant_id=sim_by_abbr["D1"]),
            FoodCategorySimulant(food_category_id=cat_by_ref["02.01"], simulant_id=sim_by_abbr["E"]),
            FoodCategorySimulant(food_category_id=cat_by_ref["02.05A"], simulant_id=sim_by_abbr["D2"]),
            FoodCategorySimulant(food_category_id=cat_by_ref["03.01"], simulant_id=sim_by_abbr["D2"]),
        ]
        session.add_all(junctions)

        foods = [
            Food(name="Still water", food_category_id=cat_by_ref["01.01A"]),
            Food(name="Orange juice with pulp", food_category_id=cat_by_ref["01.01B"]),
            Food(name="Table wine (12% vol)", food_category_id=cat_by_ref["01.02"]),
            Food(name="Whisky", food_category_id=cat_by_ref["01.03"]),
            Food(name="Corn starch", food_category_id=cat_by_ref["02.01"]),
            Food(name="Butter croissant (surface fat)", food_category_id=cat_by_ref["02.05A"]),
            Food(name="Chocolate bar", food_category_id=cat_by_ref["03.01"]),
        ]
        session.add_all(foods)

        substances = [
            Substance(smiles=None, cas_no="0000087-78-5", fcm_no=162, ec_ref_no=65520),
            Substance(smiles=None, cas_no="0000088-24-4", fcm_no=163, ec_ref_no=66400),
            Substance(smiles=None, cas_no="0000088-68-6", fcm_no=164, ec_ref_no=34895),
            Substance(smiles=None, cas_no="0000088-99-3", fcm_no=165, ec_ref_no=23200),
            Substance(smiles=None, cas_no="0000089-32-7", fcm_no=166, ec_ref_no=24057),
            Substance(smiles=None, cas_no="0000091-08-7", fcm_no=167, ec_ref_no=25240),
            Substance(smiles=None, cas_no="0000091-76-9", fcm_no=168, ec_ref_no=13075),
            Substance(smiles=None, cas_no="0000091-97-4", fcm_no=169, ec_ref_no=16240),
            Substance(smiles=None, cas_no="0000092-88-6", fcm_no=170, ec_ref_no=16000),
            Substance(smiles=None, cas_no="0000093-58-3", fcm_no=171, ec_ref_no=38080),
            Substance(smiles=None, cas_no="0000093-89-0", fcm_no=172, ec_ref_no=37840),
            Substance(smiles=None, cas_no="0000094-13-3", fcm_no=173, ec_ref_no=60240),
            Substance(smiles=None, cas_no="0000095-48-7", fcm_no=174, ec_ref_no=14740),
        ]
        session.add_all(substances)
        session.flush()

        entries = [
            SmEntry(
                substance_id=substances[0].id,
                fcm_no=162,
                use_as_additive_or_ppa=True,
                use_as_monomer_or_starting_substance=False,
                frf_applicable=False,
                restrictions_and_specifications=None,
            ),
            SmEntry(
                substance_id=substances[1].id,
                fcm_no=163,
                use_as_additive_or_ppa=True,
                use_as_monomer_or_starting_substance=False,
                frf_applicable=True,
                restrictions_and_specifications="Note (13) applies.",
            ),
            SmEntry(
                substance_id=substances[2].id,
                fcm_no=164,
                use_as_additive_or_ppa=True,
                use_as_monomer_or_starting_substance=False,
                frf_applicable=False,
                restrictions_and_specifications="Only for use in PET for water and beverages.",
            ),
            SmEntry(
                substance_id=substances[3].id,
                fcm_no=165,
                use_as_additive_or_ppa=True,
                use_as_monomer_or_starting_substance=True,
                frf_applicable=False,
                restrictions_and_specifications="Additional ref: 74480.",
            ),
            SmEntry(
                substance_id=substances[4].id,
                fcm_no=166,
                use_as_additive_or_ppa=False,
                use_as_monomer_or_starting_substance=True,
                frf_applicable=False,
                restrictions_and_specifications=None,
            ),
            SmEntry(
                substance_id=substances[5].id,
                fcm_no=167,
                use_as_additive_or_ppa=False,
                use_as_monomer_or_starting_substance=True,
                frf_applicable=False,
                restrictions_and_specifications="1 mg/kg in final product expressed as isocyanate moiety. Notes (10) apply.",
            ),
            SmEntry(
                substance_id=substances[6].id,
                fcm_no=168,
                use_as_additive_or_ppa=False,
                use_as_monomer_or_starting_substance=True,
                frf_applicable=False,
                restrictions_and_specifications="See ref 15310 (M8).",
            ),
            SmEntry(
                substance_id=substances[7].id,
                fcm_no=169,
                use_as_additive_or_ppa=False,
                use_as_monomer_or_starting_substance=True,
                frf_applicable=False,
                restrictions_and_specifications="1 mg/kg in final product expressed as isocyanate moiety. Notes (10) apply.",
            ),
            SmEntry(
                substance_id=substances[8].id,
                fcm_no=170,
                use_as_additive_or_ppa=False,
                use_as_monomer_or_starting_substance=True,
                frf_applicable=False,
                restrictions_and_specifications=None,
            ),
            SmEntry(
                substance_id=substances[9].id,
                fcm_no=171,
                use_as_additive_or_ppa=True,
                use_as_monomer_or_starting_substance=False,
                frf_applicable=False,
                restrictions_and_specifications=None,
            ),
            SmEntry(
                substance_id=substances[10].id,
                fcm_no=172,
                use_as_additive_or_ppa=True,
                use_as_monomer_or_starting_substance=False,
                frf_applicable=False,
                restrictions_and_specifications=None,
            ),
            SmEntry(
                substance_id=substances[11].id,
                fcm_no=173,
                use_as_additive_or_ppa=True,
                use_as_monomer_or_starting_substance=False,
                frf_applicable=False,
                restrictions_and_specifications=None,
            ),
            SmEntry(
                substance_id=substances[12].id,
                fcm_no=174,
                use_as_additive_or_ppa=False,
                use_as_monomer_or_starting_substance=True,
                frf_applicable=False,
                restrictions_and_specifications=None,
            ),
        ]
        session.add_all(entries)
        session.flush()

        limits = [
            SmEntryLimit(sm_entry_id=entries[2].id, kind=SmlKind.SML, value=0.05, raw_expression="0.05"),
            SmEntryLimit(sm_entry_id=entries[4].id, kind=SmlKind.SML, value=0.05, raw_expression="0.05"),
            SmEntryLimit(sm_entry_id=entries[5].id, kind=SmlKind.SML, value=1, raw_expression="1"),
            SmEntryLimit(sm_entry_id=entries[6].id, kind=SmlKind.SML, value=5, raw_expression="5"),
            SmEntryLimit(sm_entry_id=entries[7].id, kind=SmlKind.SML, value=1, raw_expression="1"),
            SmEntryLimit(sm_entry_id=entries[8].id, kind=SmlKind.SML, value=6, raw_expression="6"),
        ]
        session.add_all(limits)

        group = Annex1GroupRestriction(
            group_restriction_no=17,
            total_limit_value=1,
            specification="Expressed as isocyanate moiety",
        )
        session.add(group)
        session.flush()
        session.add(SmEntryGroupRestriction(sm_id=entries[5].id, group_restriction_id=group.id))
        session.add(SmEntryGroupRestriction(sm_id=entries[7].id, group_restriction_id=group.id))

        session.commit()
        print("Database was empty; inserted sample data.")
    finally:
        session.close()
