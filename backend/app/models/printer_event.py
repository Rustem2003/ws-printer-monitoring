from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from ..core.database import Base


class PrinterEvent(Base):
    __tablename__ = "printer_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    printer_id = Column(Integer, ForeignKey("printers.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    # event_type: offline, paper_jam, no_paper, open_cover, scanner_error,
    #             fuser_error, drum_error, toner_error, service_required,
    #             maintenance_required, no_response, online, discovered, toner_low
    severity = Column(String(16), default="info")  # critical, warning, info
    message = Column(String(512), nullable=True)
    details = Column(String, nullable=True)        # JSON
    acknowledged = Column(Integer, default=0)
    acknowledged_by = Column(Integer, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    printer = relationship("Printer", back_populates="events")
