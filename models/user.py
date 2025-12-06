from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from database.base import Base

class UserRole(enum.Enum):
    USER = "user"
    MANAGER = "manager"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.USER)
    office_id = Column(Integer, ForeignKey("offices.id"), nullable=True)
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    office = relationship("Office", back_populates="users")
    orders = relationship("Order", back_populates="user")



