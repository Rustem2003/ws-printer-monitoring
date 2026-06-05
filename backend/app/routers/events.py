from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core import get_db, get_current_user
from ..models.printer_event import PrinterEvent
from ..models.printer import Printer
from ..schemas import PrinterEventResponse, PaginatedResponse

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("", response_model=PaginatedResponse)
async def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    printer_id: Optional[int] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    acknowledged: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(PrinterEvent).options(selectinload(PrinterEvent.printer))
    count_query = select(func.count(PrinterEvent.id))

    if printer_id:
        query = query.where(PrinterEvent.printer_id == printer_id)
        count_query = count_query.where(PrinterEvent.printer_id == printer_id)
    if event_type:
        query = query.where(PrinterEvent.event_type == event_type)
        count_query = count_query.where(PrinterEvent.event_type == event_type)
    if severity:
        query = query.where(PrinterEvent.severity == severity)
        count_query = count_query.where(PrinterEvent.severity == severity)
    if acknowledged is not None:
        query = query.where(PrinterEvent.acknowledged == acknowledged)
        count_query = count_query.where(PrinterEvent.acknowledged == acknowledged)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        query.offset(offset).limit(page_size).order_by(PrinterEvent.created_at.desc())
    )
    events = result.scalars().all()

    items = []
    for e in events:
        d = {
            "id": e.id,
            "printer_id": e.printer_id,
            "event_type": e.event_type,
            "severity": e.severity,
            "message": e.message,
            "acknowledged": e.acknowledged,
            "created_at": e.created_at,
            "printer_name": e.printer.name if e.printer else None,
            "printer_ip": e.printer.ip_address if e.printer else None,
            "printer_location": e.printer.location if e.printer else None,
        }
        items.append(PrinterEventResponse(**d))

    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)
