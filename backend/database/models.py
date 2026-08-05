from sqlalchemy import Column, Integer, Float, String, DateTime
import datetime
from .database import Base

class PacenoteFeedback(Base):
    __tablename__ = "pacenote_feedback"

    id = Column(Integer, primary_key=True, index=True)
    radius = Column(Float, index=True)
    heading_change = Column(Float)
    length = Column(Float)
    original_classification = Column(Integer)
    user_classification = Column(Integer)
    driver_id = Column(String, default="default", index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
