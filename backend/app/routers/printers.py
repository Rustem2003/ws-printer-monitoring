from typing import Optional
from datetime import datetime, timezone
import json
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import get_db, get_current_user, get_user_or_internal
from ..core.config import get_settings
from ..models.printer import Printer
from ..models.consumable import Consumable
from ..models.printer_status import PrinterStatus
from ..models.printer_event import PrinterEvent
from ..schemas import (
    PrinterCreate, PrinterUpdate, PrinterResponse,
    ConsumableResponse, PrinterStatusResponse, PaginatedResponse,
)


class ConsumableIn(BaseModel):
    name: str
    current_level: Optional[float] = None
    max_capacity: Optional[int] = None


class EventIn(BaseModel):
    event_type: str
    severity: str = "info"
    message: Optional[str] = None


class StatusReport(BaseModel):
    status_code: Optional[int] = None
    status_text: Optional[str] = None
    is_online: bool = False
    page_count: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    raw_snmp_data: Optional[dict] = None
    consumables: list[ConsumableIn] = []
    events: list[EventIn] = []
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None

router = APIRouter(prefix="/api/v1/printers", tags=["printers"])


@router.get("", response_model=PaginatedResponse)
async def list_printers(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    vendor: Optional[str] = None,
    is_online: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_user_or_internal),
):
    query = select(Printer)
    count_query = select(func.count(Printer.id))

    if vendor:
        query = query.where(Printer.vendor == vendor)
        count_query = count_query.where(Printer.vendor == vendor)
    if is_online is not None:
        query = query.where(Printer.is_online == is_online)
        count_query = count_query.where(Printer.is_online == is_online)
    if search:
        query = query.where(Printer.name.ilike(f"%{search}%") | Printer.ip_address.ilike(f"%{search}%"))
        count_query = count_query.where(Printer.name.ilike(f"%{search}%") | Printer.ip_address.ilike(f"%{search}%"))

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size).order_by(Printer.name))
    printers = result.scalars().all()

    return PaginatedResponse(
        items=[PrinterResponse.model_validate(p) for p in printers],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{printer_id}", response_model=PrinterResponse)
async def get_printer(
    printer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_user_or_internal),
):
    result = await db.execute(select(Printer).where(Printer.id == printer_id))
    printer = result.scalar_one_or_none()
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    return PrinterResponse.model_validate(printer)


@router.get("/{printer_id}/consumables", response_model=list[ConsumableResponse])
async def get_printer_consumables(
    printer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Consumable).where(Consumable.printer_id == printer_id))
    return [ConsumableResponse.model_validate(c) for c in result.scalars().all()]


@router.get("/{printer_id}/status", response_model=list[PrinterStatusResponse])
async def get_printer_status_history(
    printer_id: int,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(PrinterStatus)
        .where(PrinterStatus.printer_id == printer_id)
        .order_by(PrinterStatus.recorded_at.desc())
        .limit(limit)
    )
    return [PrinterStatusResponse.model_validate(s) for s in result.scalars().all()]


@router.post("", response_model=PrinterResponse, status_code=201)
async def create_printer(
    body: PrinterCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_user_or_internal),
):
    existing = await db.execute(select(Printer).where(Printer.ip_address == body.ip_address))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Printer with this IP already exists")

    printer = Printer(**body.model_dump())
    db.add(printer)
    await db.flush()
    await db.refresh(printer)
    return PrinterResponse.model_validate(printer)


@router.put("/{printer_id}", response_model=PrinterResponse)
async def update_printer(
    printer_id: int,
    body: PrinterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Printer).where(Printer.id == printer_id))
    printer = result.scalar_one_or_none()
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")

    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(printer, key, val)

    await db.flush()
    await db.refresh(printer)
    return PrinterResponse.model_validate(printer)


@router.delete("/{printer_id}", status_code=204)
async def delete_printer(
    printer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Printer).where(Printer.id == printer_id))
    printer = result.scalar_one_or_none()
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    await db.delete(printer)


@router.post("/{printer_id}/status", status_code=201)
async def post_printer_status(
    printer_id: int,
    body: StatusReport,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_user_or_internal),
):
    """Receive a status report from monitoring service: updates printer.is_online,
    inserts printer_status row, upserts consumables, inserts events."""
    result = await db.execute(select(Printer).where(Printer.id == printer_id))
    printer = result.scalar_one_or_none()
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")

    # Update printer header
    printer.is_online = bool(body.is_online)
    printer.last_seen = datetime.now(timezone.utc)
    if body.serial_number and not printer.serial_number:
        printer.serial_number = body.serial_number[:256]
    if body.firmware_version:
        printer.firmware_version = body.firmware_version[:128]

    # Insert status snapshot
    ps = PrinterStatus(
        printer_id=printer_id,
        status_code=body.status_code,
        status_text=(body.status_text or "")[:128],
        page_count=body.page_count,
        error_code=body.error_code,
        error_message=(body.error_message or "")[:512] if body.error_message else None,
        raw_snmp_data=json.dumps(body.raw_snmp_data) if body.raw_snmp_data else None,
    )
    db.add(ps)

    # Upsert consumables by (printer_id, name)
    existing_q = await db.execute(select(Consumable).where(Consumable.printer_id == printer_id))
    by_name = {c.name: c for c in existing_q.scalars().all()}
    for c in body.consumables:
        name = (c.name or "")[:256] or "Supply"
        existing = by_name.get(name)
        # Convert from SNMP units to %
        level_pct: Optional[float] = None
        if c.current_level is not None and c.max_capacity and c.max_capacity > 0:
            level_pct = round(float(c.current_level) * 100.0 / float(c.max_capacity), 1)
        elif c.current_level is not None and 0 <= c.current_level <= 100:
            level_pct = float(c.current_level)
        elif c.current_level is not None:
            level_pct = float(c.current_level)
        if existing:
            existing.current_level = level_pct
            existing.max_capacity = c.max_capacity
        else:
            db.add(Consumable(
                printer_id=printer_id,
                name=name,
                current_level=level_pct,
                max_capacity=c.max_capacity,
            ))

    # Insert events
    for ev in body.events:
        db.add(PrinterEvent(
            printer_id=printer_id,
            event_type=ev.event_type[:64],
            severity=ev.severity[:16],
            message=(ev.message or "")[:512] if ev.message else None,
        ))

    await db.flush()
    return {"ok": True, "printer_id": printer_id, "consumables_count": len(body.consumables), "events_count": len(body.events)}


@router.post("/{printer_id}/check")
async def check_printer_now(
    printer_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Trigger immediate monitoring check via monitoring service."""
    result = await db.execute(select(Printer).where(Printer.id == printer_id))
    printer = result.scalar_one_or_none()
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")

    settings = get_settings()
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                f"{settings.monitoring_service_url}/check/{printer_id}",
                timeout=30.0,
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Monitoring service error: {resp.status_code}")
            return resp.json()
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Monitoring service unreachable: {e}")
