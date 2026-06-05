from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import relationship
from ..core.database import Base


class PrinterStatus(Base):
    __tablename__ = "printer_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    printer_id = Column(Integer, ForeignKey("printers.id", ondelete="CASCADE"), nullable=False, index=True)
    status_code = Column(Integer, nullable=True)       # Raw SNMP hrPrinterStatus
    status_text = Column(String(128), nullable=True)    # Online, Offline, Paper Jam, etc.
    page_count = Column(Integer, nullable=True)
    uptime_seconds = Column(Integer, nullable=True)
    cpu_load = Column(Float, nullable=True)
    memory_total = Column(Integer, nullable=True)
    memory_free = Column(Integer, nullable=True)
    temperature = Column(Float, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(String(512), nullable=True)
    raw_snmp_data = Column(String, nullable=True)       # JSON blob
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    printer = relationship("Printer", back_populates="statuses")
