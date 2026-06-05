import os
from typing import Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import get_db, get_current_user, get_user_or_internal
from ..models.system_setting import SystemSetting


KEY_TOKEN = "telegram_bot_token"
KEY_CHAT = "telegram_default_chat_id"
KEY_ADMIN_CHAT = "telegram_admin_chat_id"


class BotSettingsOut(BaseModel):
    token_masked: Optional[str]
    token_set: bool
    chat_id: Optional[str]
    admin_chat_id: Optional[str]
    source: str  # "db" or "env"


class BotSettingsIn(BaseModel):
    token: Optional[str] = None  # if None — не менять; пустая строка — удалить
    chat_id: Optional[str] = None
    admin_chat_id: Optional[str] = None


class BotSettingsInternal(BaseModel):
    """Internal endpoint payload used by notification service to fetch raw token."""
    token: Optional[str]
    chat_id: Optional[str]
    admin_chat_id: Optional[str]


router = APIRouter(prefix="/api/v1/system-settings", tags=["system-settings"])


def _mask(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    # 8969756666:AAGY... → 8969***:AAGY...***f2z1Y
    if ":" in token:
        prefix, secret = token.split(":", 1)
        masked_prefix = (prefix[:3] + "***" if len(prefix) > 3 else prefix)
        masked_secret = (secret[:4] + "***" + secret[-4:] if len(secret) > 12 else "***")
        return f"{masked_prefix}:{masked_secret}"
    return token[:3] + "***" + token[-3:] if len(token) > 6 else "***"


async def _get(db: AsyncSession, key: str) -> Optional[str]:
    r = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    row = r.scalar_one_or_none()
    return row.value if row else None


async def _set(db: AsyncSession, key: str, value: Optional[str]):
    r = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    row = r.scalar_one_or_none()
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key=key, value=value))
    await db.flush()


@router.get("/telegram", response_model=BotSettingsOut)
async def get_telegram_settings(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    db_token = await _get(db, KEY_TOKEN)
    db_chat = await _get(db, KEY_CHAT)
    db_admin = await _get(db, KEY_ADMIN_CHAT)

    env_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    env_chat = os.getenv("TELEGRAM_CHAT_ID", "")
    env_admin = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")

    token = db_token or env_token
    chat = db_chat or env_chat
    admin = db_admin or env_admin

    return BotSettingsOut(
        token_masked=_mask(token),
        token_set=bool(token),
        chat_id=chat or None,
        admin_chat_id=admin or None,
        source="db" if db_token else ("env" if env_token else "none"),
    )


@router.put("/telegram", response_model=BotSettingsOut)
async def update_telegram_settings(
    body: BotSettingsIn,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    if body.token is not None:
        token = body.token.strip()
        # Basic validation
        if token and (":" not in token or len(token) < 30):
            raise HTTPException(status_code=400, detail="Token format looks wrong (expected '<bot_id>:<secret>')")
        await _set(db, KEY_TOKEN, token or None)
    if body.chat_id is not None:
        await _set(db, KEY_CHAT, body.chat_id.strip() or None)
    if body.admin_chat_id is not None:
        await _set(db, KEY_ADMIN_CHAT, body.admin_chat_id.strip() or None)

    return await get_telegram_settings(db=db, _=None)


@router.post("/telegram/test")
async def test_telegram(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """Hit Telegram API /getMe to verify token works."""
    token = await _get(db, KEY_TOKEN) or os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise HTTPException(status_code=400, detail="Token is not configured")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            data = r.json()
            if r.status_code == 200 and data.get("ok"):
                bot = data.get("result", {})
                return {
                    "ok": True,
                    "bot_id": bot.get("id"),
                    "username": bot.get("username"),
                    "first_name": bot.get("first_name"),
                    "can_join_groups": bot.get("can_join_groups"),
                    "supports_inline_queries": bot.get("supports_inline_queries"),
                }
            return {
                "ok": False,
                "error_code": data.get("error_code"),
                "description": data.get("description"),
            }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Telegram API error: {e}")


@router.get("/telegram/internal", response_model=BotSettingsInternal)
async def get_telegram_internal(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_user_or_internal),
):
    """Internal endpoint for notification service to fetch raw token."""
    db_token = await _get(db, KEY_TOKEN)
    db_chat = await _get(db, KEY_CHAT)
    db_admin = await _get(db, KEY_ADMIN_CHAT)
    return BotSettingsInternal(
        token=db_token or os.getenv("TELEGRAM_BOT_TOKEN") or None,
        chat_id=db_chat or os.getenv("TELEGRAM_CHAT_ID") or None,
        admin_chat_id=db_admin or os.getenv("TELEGRAM_ADMIN_CHAT_ID") or None,
    )
