from sqlalchemy import Column, Integer, DateTime, ForeignKey
from datetime import datetime
from app.db.session import Base


class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
