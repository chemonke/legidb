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
        print("Seed data inserted.")


if __name__ == "__main__":
    database_url = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://legidb:legidb@localhost:3306/legidb",
    )
    engine = create_engine(database_url, future=True)
    seed(engine)
