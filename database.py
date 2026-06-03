from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    Float,
    String,
    ForeignKey,
    Boolean,
    JSON,
    inspect,
    text,
)

from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    relationship,
)

from werkzeug.security import (
    generate_password_hash,
)

# ==========================
# DATABASE SETUP
# ==========================

engine = create_engine("sqlite:///cki.db")

Session = sessionmaker(bind=engine)

Base = declarative_base()


# ==========================
# MODELS
# ==========================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    full_name = Column(String)

    role = Column(String, default="venue")

    # Multi venue access
    venues = Column(JSON, nullable=True)

    active = Column(Boolean, default=True)


class Period(Base):
    __tablename__ = "periods"

    id = Column(Integer, primary_key=True)

    # SINGLE venue per report
    venue = Column(String, nullable=False)
    financial_year = Column(String)
    period = Column(String)
    report_type = Column(String)

    revenue = Column(Float)
    cogs = Column(Float)
    purchases = Column(Float)

    food_cost_percent = Column(Float)
    waste_total = Column(Float)
    waste_percent = Column(Float)

    food_cost_target = Column(Float)
    waste_target = Column(Float)

    food_cost_variance = Column(Float)
    waste_variance = Column(Float)

    risk_rating = Column(String)
    closing_stock = Column(Float)


class SalesLine(Base):
    __tablename__ = "sales_lines"

    id = Column(Integer, primary_key=True)

    period_id = Column(
        Integer,
        ForeignKey("periods.id"),
        index=True
    )

    item_name = Column(String, nullable=False)
    qty = Column(Float, default=0)

    revenue = Column(Float, default=0)

    food_cost = Column(Float, default=0)

    gross_profit = Column(Float, default=0)

    gross_profit_percent = Column(Float, default=0)

    period = relationship(
        "Period",
        backref="sales_lines"
    )


class WasteLine(Base):
    __tablename__ = "waste_lines"

    id = Column(Integer, primary_key=True)

    period_id = Column(
        Integer,
        ForeignKey("periods.id"),
        index=True
    )

    item = Column(String)
    qty = Column(Float)
    total = Column(Float)
    reason = Column(String)

    period = relationship(
        "Period",
        backref="waste_lines"
    )


# ==========================
# CREATE TABLES
# ==========================

Base.metadata.create_all(engine)


# ==========================
# SAFE AUTO MIGRATION
# ==========================

def fix_db():

    inspector = inspect(engine)

    with engine.connect() as conn:

        # -------------------------
        # PERIODS TABLE
        # -------------------------

        try:
            period_cols = [
                c["name"]
                for c in inspector.get_columns("periods")
            ]
        except Exception:
            period_cols = []

        if "venue" not in period_cols:
            conn.execute(
                text(
                    "ALTER TABLE periods "
                    "ADD COLUMN venue TEXT"
                )
            )

        # -------------------------
        # USERS TABLE
        # -------------------------

        try:
            user_cols = [
                c["name"]
                for c in inspector.get_columns("users")
            ]
        except Exception:
            user_cols = []

        if "venues" not in user_cols:
            conn.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN venues TEXT"
                )
            )

        conn.commit()


fix_db()


# ==========================
# SEED ADMIN
# ==========================

def seed_admin_user():

    session = Session()

    existing = (
        session.query(User)
        .filter_by(username="Brandyn")
        .first()
    )

    if not existing:

        admin = User(
            username="Brandyn",
            password_hash=generate_password_hash(
                "chef123"
            ),
            full_name="Brandyn",
            role="admin",
            venues="ALL",
            active=True
        )

        session.add(admin)
        session.commit()

    session.close()


seed_admin_user()