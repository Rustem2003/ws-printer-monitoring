from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import get_db, get_current_user
from ..models.printer import Printer
from ..models.printer_event import PrinterEvent
from ..models.consumable import Consumable
from ..schemas import StatisticsResponse, ConsumableStatisticsResponse

router = APIRouter(prefix="/api/v1/statistics", tags=["statistics"])


@router.get("", response_model=StatisticsResponse)
async def get_statistics(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    total = (await db.execute(select(func.count(Printer.id)))).scalar() or 0
    online = (await db.execute(select(func.count(Printer.id)).where(Printer.is_online == True))).scalar() or 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    events_today = (await db.execute(
        select(func.count(PrinterEvent.id)).where(PrinterEvent.created_at >= today_start)
    )).scalar() or 0
    critical = (await db.execute(
        select(func.count(PrinterEvent.id)).where(
            and_(PrinterEvent.severity == "critical", PrinterEvent.acknowledged == 0)
        )
    )).scalar() or 0
    low_toner = (await db.execute(
        select(func.count(Consumable.id)).where(
            Consumable.current_level <= Consumable.threshold_warning
        )
    )).scalar() or 0

    return StatisticsResponse(
        total_printers=total,
        online_printers=online,
        offline_printers=total - online,
        total_events_today=events_today,
        critical_events=critical,
        low_toner_count=low_toner,
    )


@router.get("/charts")
async def get_charts(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Aggregated data for dashboard charts."""
    now = datetime.now(timezone.utc)
    h24_ago = now - timedelta(hours=24)
    d7_ago = now - timedelta(days=7)

    # ---- Events by type (24h) ----
    by_type_q = await db.execute(
        select(PrinterEvent.event_type, func.count(PrinterEvent.id))
        .where(PrinterEvent.created_at >= h24_ago)
        .group_by(PrinterEvent.event_type)
        .order_by(desc(func.count(PrinterEvent.id)))
    )
    by_type = [{"event_type": et, "count": cnt} for et, cnt in by_type_q.all()]

    # ---- Events by severity (24h) ----
    by_sev_q = await db.execute(
        select(PrinterEvent.severity, func.count(PrinterEvent.id))
        .where(PrinterEvent.created_at >= h24_ago)
        .group_by(PrinterEvent.severity)
    )
    by_severity = [{"severity": sv, "count": cnt} for sv, cnt in by_sev_q.all()]

    # ---- Events per hour (24h timeline) ----
    timeline = []
    for i in range(23, -1, -1):
        hour_start = (now - timedelta(hours=i)).replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)
        cnt = (await db.execute(
            select(func.count(PrinterEvent.id)).where(
                and_(PrinterEvent.created_at >= hour_start, PrinterEvent.created_at < hour_end)
            )
        )).scalar() or 0
        timeline.append({
            "hour": hour_start.strftime("%H:00"),
            "ts": hour_start.isoformat(),
            "count": cnt,
        })

    # ---- Events per day (7 days) ----
    days_timeline = []
    for i in range(6, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        cnt = (await db.execute(
            select(func.count(PrinterEvent.id)).where(
                and_(PrinterEvent.created_at >= day_start, PrinterEvent.created_at < day_end)
            )
        )).scalar() or 0
        days_timeline.append({
            "day": day_start.strftime("%d.%m"),
            "ts": day_start.isoformat(),
            "count": cnt,
        })

    # ---- Printers by vendor ----
    vendor_q = await db.execute(
        select(
            func.coalesce(Printer.vendor, "Unknown").label("vendor"),
            func.count(Printer.id),
        ).group_by(Printer.vendor)
    )
    by_vendor = [{"vendor": v, "count": cnt} for v, cnt in vendor_q.all()]

    # ---- Top 5 printers by event count (24h) ----
    top_q = await db.execute(
        select(
            PrinterEvent.printer_id,
            Printer.name,
            Printer.ip_address,
            Printer.location,
            func.count(PrinterEvent.id).label("cnt"),
        )
        .join(Printer, Printer.id == PrinterEvent.printer_id)
        .where(PrinterEvent.created_at >= h24_ago)
        .group_by(PrinterEvent.printer_id, Printer.name, Printer.ip_address, Printer.location)
        .order_by(desc("cnt"))
        .limit(5)
    )
    top_printers = [
        {"printer_id": pid, "name": name, "ip": ip, "location": loc, "count": cnt}
        for pid, name, ip, loc, cnt in top_q.all()
    ]

    # ---- Low consumables (<= 20%) ----
    low_q = await db.execute(
        select(
            Consumable.name,
            Consumable.current_level,
            Consumable.threshold_warning,
            Consumable.threshold_critical,
            Printer.name.label("printer_name"),
            Printer.ip_address,
            Printer.location,
            Printer.id.label("printer_id"),
        )
        .join(Printer, Printer.id == Consumable.printer_id)
        .where(Consumable.current_level.isnot(None))
        .where(Consumable.current_level <= Consumable.threshold_warning)
        .order_by(Consumable.current_level)
        .limit(10)
    )
    low_consumables = [
        {
            "printer_id": r.printer_id,
            "printer_name": r.printer_name,
            "ip": r.ip_address,
            "location": r.location,
            "name": r.name,
            "level": round(float(r.current_level), 1) if r.current_level is not None else None,
        }
        for r in low_q.all()
    ]

    # ---- Online vs Offline ----
    online_cnt = (await db.execute(
        select(func.count(Printer.id)).where(Printer.is_online == True)
    )).scalar() or 0
    total = (await db.execute(select(func.count(Printer.id)))).scalar() or 0

    return {
        "by_type": by_type,
        "by_severity": by_severity,
        "timeline_24h": timeline,
        "timeline_7d": days_timeline,
        "by_vendor": by_vendor,
        "top_printers": top_printers,
        "low_consumables": low_consumables,
        "online_offline": [
            {"label": "Онлайн", "count": online_cnt},
            {"label": "Оффлайн", "count": total - online_cnt},
        ],
    }


@router.get("/consumables", response_model=list[ConsumableStatisticsResponse])
async def get_consumable_statistics(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(Consumable, Printer.name.label("printer_name"))
        .join(Printer, Consumable.printer_id == Printer.id)
        .where(Consumable.current_level <= Consumable.threshold_warning)
        .order_by(Consumable.current_level)
    )
    return [
        ConsumableStatisticsResponse(
            printer_name=row.printer_name,
            consumable_name=row.Consumable.name,
            current_level=row.Consumable.current_level or 0,
            threshold_warning=row.Consumable.threshold_warning,
            threshold_critical=row.Consumable.threshold_critical,
        )
        for row in result
    ]
