from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # Null apenas para ADMIN_SISTEMA (tenant via X-Gym-Id ou legado X-Academia-Id).
    gym_id = Column(Integer, ForeignKey("gyms.id"), nullable=True, index=True)
    gym = relationship("Gym", back_populates="users")

    email = Column(String, unique=True, index=True)
    password = Column(String)
    is_verified = Column(Boolean, default=False)
    role = Column(String, default="ALUNO")
    password_reset_at = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

