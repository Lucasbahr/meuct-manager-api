from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    is_verified = Column(Boolean, default=False)
    role = Column(String, default="ALUNO")
    password_reset_at = Column(DateTime, nullable=True)
