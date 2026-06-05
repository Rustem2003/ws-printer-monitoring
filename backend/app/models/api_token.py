from sqlalchemy import Column, Integer, String, DateTime, func
from ..core.database import Base


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token_hash = Column(String(256), unique=True, nullable=False)
    name = Column(String(256), nullable=True)
    user_id = Column(Integer, nullable=True)
    permissions = Column(String, nullable=True)  # JSON
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
