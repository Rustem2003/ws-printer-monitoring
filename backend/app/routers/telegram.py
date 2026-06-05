from typing import Optional
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import get_db, get_current_user
from ..core.config import get_settings
from ..models.telegram_chat import TelegramChat


EVENT_TYPES = [
    "offline", "paper_jam", "no_paper", "open_cover", "scanner_error",
    "fuser_error", "drum_error", "toner_error", "service_required",
    "maintenance_required", "discovered",
]


class TelegramChatBody(BaseModel):
    chat_id: str
    name: Optional[str] = None
    chat_type: str = "group"
    is_active: int = 1
    subscribed_events: Optional[str] = None


class TelegramChatUpdate(BaseModel):
    name: Optional[str] = None
    chat_type: Optional[str] = None
    is_active: Optional[int] = None
    subscribed_events: Optional[str] = None


class TelegramChatOut(BaseModel):
    id: int
    chat_id: str
    name: Optional[str]
    chat_type: str
    is_active: int
    subscribed_events: Optional[str]

    model_config = {"from_attributes": True}


router = APIRouter(prefix="/api/v1/telegram-chats", tags=["telegram"])


@router.get("", response_model=list[TelegramChatOut])
async def list_chats(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select(TelegramChat).order_by(TelegramChat.id))
    return [TelegramChatOut.model_validate(c) for c in result.scalars().all()]


@router.get("/event-types")
async def event_types(_=Depends(get_current_user)):
    return {"event_types": EVENT_TYPES}


@router.post("", response_model=TelegramChatOut, status_code=201)
async def create_chat(
    body: TelegramChatBody,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    existing = await db.execute(select(TelegramChat).where(TelegramChat.chat_id == body.chat_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Chat with this chat_id already exists")
    chat = TelegramChat(**body.model_dump())
    db.add(chat)
    await db.flush()
    await db.refresh(chat)
    return TelegramChatOut.model_validate(chat)


@router.put("/{chat_pk}", response_model=TelegramChatOut)
async def update_chat(
    chat_pk: int,
    body: TelegramChatUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select(TelegramChat).where(TelegramChat.id == chat_pk))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(chat, k, v)
    await db.flush()
    await db.refresh(chat)
    return TelegramChatOut.model_validate(chat)


@router.delete("/{chat_pk}", status_code=204)
async def delete_chat(
    chat_pk: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select(TelegramChat).where(TelegramChat.id == chat_pk))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    await db.delete(chat)


@router.post("/{chat_pk}/test")
async def send_test(
    chat_pk: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select(TelegramChat).where(TelegramChat.id == chat_pk))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    settings = get_settings()
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{settings.notification_service_url}/send",
                json={
                    "chat_id": chat.chat_id,
                    "text": f"🧪 Тестовое сообщение для чата «{chat.name or chat.chat_id}» — Printer Monitoring System работает.",
                    "event_type": "test",
                },
            )
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
            return {"ok": resp.status_code == 200, "status_code": resp.status_code, "response": data}
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Notification service unreachable: {e}")
