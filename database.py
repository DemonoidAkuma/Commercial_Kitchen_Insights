from sqlalchemy import create_engine, Column, Integer, Float, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

engine = create_engine("sqlite:///cki.db")
Session = sessionmaker(bind=engine)
Base = declarative_base()


class Period(Base):
    __tablename__ = "periods"

    id = Column(Integer, primary_key=True)
    venue = Column(String)
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

    # IMPORTANT — must match "periods"
    period_id = Column(Integer, ForeignKey("periods.id"), index=True)

    item_name = Column(String, nullable=False)
    qty = Column(Float, default=0)
    revenue = Column(Float, default=0)
    food_cost = Column(Float, default=0)
    gross_profit = Column(Float, default=0)
    gross_profit_percent = Column(Float, default=0)

    period = relationship("Period", backref="sales_lines")

    
class WasteLine(Base):
    __tablename__ = "waste_lines"

    id = Column(Integer, primary_key=True)

    period_id = Column(Integer, ForeignKey("periods.id"), index=True)

    item = Column(String)
    qty = Column(Float)
    total = Column(Float)
    reason = Column(String)

    period = relationship("Period", backref="waste_lines")

    


Base.metadata.create_all(engine)