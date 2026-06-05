from sqlalchemy import Column, Integer, String, DateTime, func
from ..core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String(64), nullable=False)
    event_type = Column(String(64), nullable=False)
    message = Column(String(1024), nullable=False)
    severity = Column(String(16), default="info")
    status = Column(String(16), default="sent")    # queued, sent, failed
    error_message = Column(String(512), nullable=True)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
