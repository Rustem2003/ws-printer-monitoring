from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import relationship
from ..core.database import Base


class Consumable(Base):
    __tablename__ = "consumables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    printer_id = Column(Integer, ForeignKey("printers.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(256), nullable=False)  # Black Toner, Cyan Toner, Drum, Fuser, etc.
    oid = Column(String(256), nullable=True)    # SNMP OID for this consumable
    current_level = Column(Float, nullable=True)  # 0-100%
    max_capacity = Column(Integer, nullable=True)
    threshold_warning = Column(Float, default=20.0)  # Warning threshold %
    threshold_critical = Column(Float, default=5.0)   # Critical threshold %
    unit = Column(String(32), default="%")
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    printer = relationship("Printer", back_populates="consumables")
