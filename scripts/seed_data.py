import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import (
    Base,
    Annex1GroupRestriction,
    Food,
    FoodCategory,
    FoodCategorySimulant,
    Simulant,
    SmEntry,
    SmEntryGroupRestriction,
    SmEntryLimit,
    Substance,
    SmlKind,
)


def seed(engine):
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        if session.query(FoodCategory).count() > 0:
            print("Database already seeded; skipping.")
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
        print("Seed data inserted.")


if __name__ == "__main__":
    database_url = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://legidb:legidb@localhost:3306/legidb",
    )
    engine = create_engine(database_url, future=True)
    seed(engine)
