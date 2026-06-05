from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, func
from sqlalchemy.orm import relationship
from ..core.database import Base


class Printer(Base):
    __tablename__ = "printers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False)
    ip_address = Column(String(45), nullable=False, index=True)
    mac_address = Column(String(17), nullable=True)
    vendor = Column(String(128), nullable=True)  # HP, Xerox, Canon, Brother, Kyocera, Ricoh, KM, Epson
    model = Column(String(256), nullable=True)
    serial_number = Column(String(256), nullable=True)
    firmware_version = Column(String(128), nullable=True)
    location = Column(String(256), nullable=True)
    is_color = Column(Boolean, default=False)
    is_online = Column(Boolean, default=False)
    snmp_version = Column(String(8), default="2c")  # v1, v2c, v3
    snmp_community = Column(String(64), default="public")
    snmp_port = Column(Integer, default=161)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    tenant_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    consumables = relationship("Consumable", back_populates="printer", cascade="all, delete-orphan")
    statuses = relationship("PrinterStatus", back_populates="printer", cascade="all, delete-orphan")
    events = relationship("PrinterEvent", back_populates="printer", cascade="all, delete-orphan")
