from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class AnnexListId(str, Enum):
    EU_10_2011_ANNEX_I_TABLE_1 = "EU_10_2011_ANNEX_I_TABLE_1"


class SmlKind(str, Enum):
    SML = "SML"
    ND = "ND"


class LimitBasis(str, Enum):
    FOOD_KG = "FOOD_KG"
    ARTICLE = "ARTICLE"
    SURFACE_DM2 = "SURFACE_DM2"


class FoodCategory(Base):
    __tablename__ = "food_categories"

    id = Column(Integer, primary_key=True)
    ref_no = Column(String(32), nullable=False)
    description = Column(String(255), nullable=False)
    acidic = Column(Boolean)
    frf = Column(Integer)

    foods = relationship(
        "Food",
        back_populates="food_category",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    simulants = relationship(
        "Simulant",
        secondary="food_category_simulants",
        back_populates="food_categories",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"FoodCategory {self.ref_no}: {self.description}"

    __str__ = __repr__


class Food(Base):
    __tablename__ = "foods"

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    food_category_id = Column(
        Integer,
        ForeignKey("food_categories.id", ondelete="CASCADE"),
        nullable=False,
    )

    food_category = relationship("FoodCategory", back_populates="foods")

    def __repr__(self):
        return f"Food {self.name or self.id}"

    __str__ = __repr__


class Simulant(Base):
    __tablename__ = "simulants"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    abbreviation = Column(String(16), nullable=False)

    food_categories = relationship(
        "FoodCategory",
        secondary="food_category_simulants",
        back_populates="simulants",
    )

    def __repr__(self):
        return f"Simulant {self.abbreviation}: {self.name}"

    __str__ = __repr__


class FoodCategorySimulant(Base):
    __tablename__ = "food_category_simulants"
    __table_args__ = (UniqueConstraint("food_category_id", "simulant_id"),)

    food_category_id = Column(
        Integer,
        ForeignKey("food_categories.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    simulant_id = Column(
        Integer,
        ForeignKey("simulants.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )


class Substance(Base):
    __tablename__ = "substances"

    id = Column(Integer, primary_key=True)
    smiles = Column(String(255))
    cas_no = Column(String(64))
    fcm_no = Column(Integer)
    ec_ref_no = Column(Integer)

    sm_entries = relationship(
        "SmEntry",
        back_populates="substance",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        cas = self.cas_no or "no CAS"
        return f"Substance FCM {self.fcm_no} ({cas})"

    __str__ = __repr__


class SmEntry(Base):
    __tablename__ = "sm_entries"

    id = Column(Integer, primary_key=True)
    substance_id = Column(Integer, ForeignKey("substances.id", ondelete="CASCADE"), nullable=False)
    fcm_no = Column(Integer)
    use_as_additive_or_ppa = Column(Boolean, nullable=False)
    use_as_monomer_or_starting_substance = Column(Boolean, nullable=False)
    frf_applicable = Column(Boolean, nullable=False)
    restrictions_and_specifications = Column(Text)

    substance = relationship("Substance", back_populates="sm_entries")
    limits = relationship(
        "SmEntryLimit",
        back_populates="sm_entry",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    group_restrictions = relationship(
        "Annex1GroupRestriction",
        secondary="sm_entry_group_restrictions",
        back_populates="sm_entries",
    )

    def __repr__(self):
        return f"SM Entry FCM {self.fcm_no} / substance {self.substance_id}"

    __str__ = __repr__


class SmEntryLimit(Base):
    __tablename__ = "sm_entry_limits"
    __table_args__ = (UniqueConstraint("sm_entry_id", "kind"),)

    id = Column(Integer, primary_key=True)
    sm_entry_id = Column(Integer, ForeignKey("sm_entries.id", ondelete="CASCADE"), nullable=False)
    kind = Column(SqlEnum(SmlKind), nullable=False)
    value = Column(Numeric(10, 3))
    unit_basis = Column(SqlEnum(LimitBasis), nullable=False, default=LimitBasis.FOOD_KG)
    raw_expression = Column(String(64))

    sm_entry = relationship("SmEntry", back_populates="limits")


class Annex1GroupRestriction(Base):
    __tablename__ = "annex1_group_restrictions"

    id = Column(Integer, primary_key=True)
    group_restriction_no = Column(Integer, nullable=False, unique=True)
    total_limit_value = Column(Numeric(10, 3))
    unit_basis = Column(SqlEnum(LimitBasis), nullable=False, default=LimitBasis.FOOD_KG)
    specification = Column(Text)

    sm_entries = relationship(
        "SmEntry",
        secondary="sm_entry_group_restrictions",
        back_populates="group_restrictions",
    )


class SmEntryGroupRestriction(Base):
    __tablename__ = "sm_entry_group_restrictions"
    __table_args__ = (UniqueConstraint("sm_id", "group_restriction_id"),)

    sm_id = Column(
        Integer,
        ForeignKey("sm_entries.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    group_restriction_id = Column(
        Integer,
        ForeignKey("annex1_group_restrictions.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )


class SmCondition(Base):
    __tablename__ = "sm_conditions"

    id = Column(Integer, primary_key=True)
    worst_case_time = Column(Integer)
    testing_time = Column(Integer)
    worst_case_temp = Column(Integer)
    testing_temp = Column(Integer)
