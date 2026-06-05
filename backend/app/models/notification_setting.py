from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from ..core.database import Base


class NotificationSetting(Base):
    __tablename__ = "notification_settings"

    event_type = Column(String(64), primary_key=True)
    enabled = Column(Boolean, default=True, nullable=False)
    # 0 — отправлять только один раз; > 0 — повторять каждые N минут, пока проблема не устранена
    repeat_interval_minutes = Column(Integer, default=30, nullable=False)
    title_ru = Column(String(128), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
