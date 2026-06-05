from sqlalchemy import Column, Integer, String, DateTime, Float, func
from ..core.database import Base


class ScanJob(Base):
    __tablename__ = "scan_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(String(32), default="discovery")  # discovery, manual, scheduled
    status = Column(String(32), default="pending")       # pending, running, completed, failed
    subnet = Column(String(45), nullable=True)
    method = Column(String(32), default="snmp_broadcast")  # snmp_broadcast, nmap, ping_sweep
    devices_found = Column(Integer, default=0)
    devices_added = Column(Integer, default=0)
    progress = Column(Float, default=0.0)
    error_message = Column(String(512), nullable=True)
    started_by = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
