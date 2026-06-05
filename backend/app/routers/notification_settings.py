from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import get_db, get_current_user, get_user_or_internal
from ..models.notification_setting import NotificationSetting


# Полный список типов событий + русские заголовки + дефолтная периодичность (минут)
DEFAULT_SETTINGS = [
    # (event_type, title_ru, default_repeat_minutes)
    ("offline", "Принтер недоступен", 30),
    ("no_response", "Нет ответа", 30),
    ("no_snmp", "SNMP не отвечает", 60),
    ("paper_jam", "Замятие бумаги", 15),
    ("no_paper", "Закончилась бумага", 30),
    ("open_cover", "Открыта крышка", 15),
    ("scanner_error", "Ошибка сканера", 60),
    ("fuser_error", "Ошибка термоблока", 60),
    ("drum_error", "Ошибка фотобарабана", 60),
    ("toner_error", "Заканчивается / закончился картридж", 120),
    ("toner_low", "Низкий уровень тонера", 240),
    ("service_required", "Требуется сервис", 180),
    ("maintenance_required", "Требуется обслуживание", 180),
    ("discovered", "Найдено новое устройство", 0),
]


class SettingOut(BaseModel):
    event_type: str
    title_ru: Optional[str]
    enabled: bool
    repeat_interval_minutes: int

    model_config = {"from_attributes": True}


class SettingUpdate(BaseModel):
    enabled: Optional[bool] = None
    repeat_interval_minutes: Optional[int] = None
    title_ru: Optional[str] = None


router = APIRouter(prefix="/api/v1/notification-settings", tags=["notification-settings"])


async def _seed_if_empty(db: AsyncSession):
    """Insert default rows on first request if table is empty."""
    result = await db.execute(select(NotificationSetting))
    if result.scalars().first():
        return
    for et, title, period in DEFAULT_SETTINGS:
        db.add(NotificationSetting(event_type=et, title_ru=title, repeat_interval_minutes=period, enabled=True))
    await db.flush()


@router.get("", response_model=list[SettingOut])
async def list_settings(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_user_or_internal),
):
    await _seed_if_empty(db)
    result = await db.execute(select(NotificationSetting).order_by(NotificationSetting.event_type))
    return [SettingOut.model_validate(r) for r in result.scalars().all()]


@router.put("/{event_type}", response_model=SettingOut)
async def update_setting(
    event_type: str,
    body: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    await _seed_if_empty(db)
    result = await db.execute(select(NotificationSetting).where(NotificationSetting.event_type == event_type))
    row = result.scalar_one_or_none()
    if not row:
        # create on-the-fly for unknown event types
        row = NotificationSetting(event_type=event_type, enabled=True, repeat_interval_minutes=30)
        db.add(row)
    if body.enabled is not None:
        row.enabled = body.enabled
    if body.repeat_interval_minutes is not None:
        if body.repeat_interval_minutes < 0 or body.repeat_interval_minutes > 1440 * 7:
            raise HTTPException(status_code=400, detail="repeat_interval_minutes должен быть 0..10080")
        row.repeat_interval_minutes = body.repeat_interval_minutes
    if body.title_ru is not None:
        row.title_ru = body.title_ru[:128]
    await db.flush()
    await db.refresh(row)
    return SettingOut.model_validate(row)


@router.post("/reset", response_model=list[SettingOut])
async def reset_to_defaults(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Сбросить все настройки к дефолтным значениям."""
    for et, title, period in DEFAULT_SETTINGS:
        result = await db.execute(select(NotificationSetting).where(NotificationSetting.event_type == et))
        row = result.scalar_one_or_none()
        if row:
            row.enabled = True
            row.repeat_interval_minutes = period
            row.title_ru = title
        else:
            db.add(NotificationSetting(event_type=et, enabled=True, repeat_interval_minutes=period, title_ru=title))
    await db.flush()
    result = await db.execute(select(NotificationSetting).order_by(NotificationSetting.event_type))
    return [SettingOut.model_validate(r) for r in result.scalars().all()]
