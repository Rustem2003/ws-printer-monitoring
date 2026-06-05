from sqlalchemy import Column, Integer, String, DateTime, func
from ..core.database import Base


class TelegramChat(Base):
    __tablename__ = "telegram_chats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String(64), unique=True, nullable=False)
    name = Column(String(256), nullable=True)
    chat_type = Column(String(32), default="group")  # group, private, channel
    is_active = Column(Integer, default=1)
    subscribed_events = Column(String, nullable=True)  # comma-separated event types
    created_at = Column(DateTime(timezone=True), server_default=func.now())
