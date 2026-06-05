"""
Enterprise Telegram Notification Service
Sends rich alerts (printer name, IP, кабинет, % картриджа) to multiple chats based on subscriptions
"""
import asyncio
import json
import os
import time
from datetime import datetime, timezone
from collections import deque
from typing import Optional

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Printer Notification Service")

BOT_TOKEN_ENV = os.getenv("TELEGRAM_BOT_TOKEN", "")
DEFAULT_CHAT_ID_ENV = os.getenv("TELEGRAM_CHAT_ID", "")
ADMIN_CHAT_ID_ENV = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")

# Live (DB-backed) settings, refreshed every BOT_SETTINGS_TTL seconds
_bot_cache = {"ts": 0.0, "token": BOT_TOKEN_ENV, "chat": DEFAULT_CHAT_ID_ENV, "admin": ADMIN_CHAT_ID_ENV}
BOT_SETTINGS_TTL = 30  # seconds


async def get_bot_settings() -> tuple[str, str, str]:
    """Returns (token, default_chat_id, admin_chat_id), preferring DB then env."""
    now = time.time()
    if now - _bot_cache["ts"] < BOT_SETTINGS_TTL:
        return _bot_cache["token"], _bot_cache["chat"], _bot_cache["admin"]
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(
                f"{BACKEND_URL}/system-settings/telegram/internal",
                headers=INTERNAL_HEADERS,
            )
            if r.status_code == 200:
                data = r.json()
                _bot_cache.update({
                    "ts": now,
                    "token": data.get("token") or BOT_TOKEN_ENV,
                    "chat": data.get("chat_id") or DEFAULT_CHAT_ID_ENV,
                    "admin": data.get("admin_chat_id") or ADMIN_CHAT_ID_ENV,
                })
    except Exception as e:
        print(f"[notification] bot settings fetch err: {e}")
    return _bot_cache["token"], _bot_cache["chat"], _bot_cache["admin"]
BACKEND_URL = os.getenv("BACKEND_API_URL", "http://backend:8000/api/v1").rstrip("/")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/3")
INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "")
INTERNAL_HEADERS = {"X-Internal-Token": INTERNAL_TOKEN} if INTERNAL_TOKEN else {}

_redis: Optional[aioredis.Redis] = None
_settings_cache: dict = {"ts": 0.0, "data": {}}
SETTINGS_TTL = 30  # seconds


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


async def fetch_notification_settings(client: httpx.AsyncClient) -> dict[str, dict]:
    """Cached fetch of /api/v1/notification-settings -> dict by event_type."""
    now = time.time()
    if now - _settings_cache["ts"] < SETTINGS_TTL and _settings_cache["data"]:
        return _settings_cache["data"]
    try:
        r = await client.get(f"{BACKEND_URL}/notification-settings", headers=INTERNAL_HEADERS, timeout=8.0)
        if r.status_code == 200:
            data = {row["event_type"]: row for row in (r.json() or [])}
            _settings_cache["data"] = data
            _settings_cache["ts"] = now
            return data
    except Exception as e:
        print(f"[notification] settings fetch err: {e}")
    return _settings_cache["data"]


async def should_send(event_type: str, printer_id: Optional[int]) -> tuple[bool, str]:
    """Check notification_settings + Redis throttle. Returns (allow, reason)."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        settings = await fetch_notification_settings(client)
    cfg = settings.get(event_type) or {"enabled": True, "repeat_interval_minutes": 30}
    if not cfg.get("enabled", True):
        return False, "disabled"
    interval_sec = max(0, int(cfg.get("repeat_interval_minutes", 30))) * 60
    if interval_sec == 0:
        # One-shot: send once per (event_type, printer_id) until manually reset
        # We still mark it sent forever (until next backend restart cycle) — use very long TTL
        interval_sec = 30 * 24 * 3600
    r = await get_redis()
    key = f"notif:throttle:{event_type}:{printer_id or 'na'}"
    if await r.exists(key):
        ttl = await r.ttl(key)
        return False, f"throttled ({ttl}s left)"
    await r.set(key, "1", ex=interval_sec)
    return True, "ok"

def _telegram_api(token: str) -> str:
    return f"https://api.telegram.org/bot{token}"

last_sent: dict[str, float] = {}

EVENT_EMOJIS = {
    "offline": "🔴",
    "no_response": "🔴",
    "no_snmp": "🔴",
    "paper_jam": "🟡",
    "no_paper": "🟡",
    "open_cover": "🟠",
    "scanner_error": "🟠",
    "fuser_error": "🔴",
    "drum_error": "🔴",
    "toner_error": "🟠",
    "toner_low": "🟡",
    "service_required": "🔴",
    "maintenance_required": "🟡",
    "online": "🟢",
    "discovered": "🔍",
    "deployment": "🚀",
    "test": "🧪",
}

EVENT_TITLES_RU = {
    "offline": "Принтер недоступен",
    "no_response": "Нет ответа",
    "no_snmp": "SNMP не отвечает",
    "paper_jam": "Замятие бумаги",
    "no_paper": "Нет бумаги",
    "open_cover": "Открыта крышка",
    "scanner_error": "Ошибка сканера",
    "fuser_error": "Ошибка термоблока",
    "drum_error": "Ошибка фотобарабана",
    "toner_error": "Заканчивается картридж",
    "toner_low": "Низкий уровень тонера",
    "service_required": "Требуется сервис",
    "maintenance_required": "Требуется обслуживание",
    "online": "Подключён",
    "discovered": "Новое устройство",
    "deployment": "Развёртывание",
    "test": "Тестовое сообщение",
}

COLOR_EMOJIS = {
    "Black": "⚫", "Cyan": "🟦", "Magenta": "🟪", "Yellow": "🟨",
    "Drum": "🥁", "Fuser": "🔥",
}


def _h(s: Optional[str]) -> str:
    """Escape HTML for Telegram."""
    if not s:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt_pct(level: Optional[float], max_cap: Optional[int]) -> Optional[float]:
    if level is None:
        return None
    try:
        if max_cap and max_cap > 0:
            return round(float(level) * 100.0 / float(max_cap), 1)
        if 0 <= level <= 100:
            return float(level)
    except (TypeError, ValueError):
        return None
    return None


async def fetch_printer(client: httpx.AsyncClient, printer_id: int) -> Optional[dict]:
    try:
        r = await client.get(f"{BACKEND_URL}/printers/{printer_id}", headers=INTERNAL_HEADERS, timeout=8.0)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"[notification] fetch_printer({printer_id}) err: {e}")
    return None


async def fetch_consumables(client: httpx.AsyncClient, printer_id: int) -> list[dict]:
    try:
        r = await client.get(f"{BACKEND_URL}/printers/{printer_id}/consumables", headers=INTERNAL_HEADERS, timeout=8.0)
        if r.status_code == 200:
            return r.json() or []
    except Exception:
        pass
    return []


async def fetch_active_chats(client: httpx.AsyncClient) -> list[dict]:
    """Get telegram_chats from backend; fallback to default chat from settings."""
    try:
        r = await client.get(f"{BACKEND_URL}/telegram-chats", headers=INTERNAL_HEADERS, timeout=8.0)
        if r.status_code == 200:
            data = r.json() or []
            chats = [c for c in data if c.get("is_active")]
            if chats:
                return chats
    except Exception as e:
        print(f"[notification] fetch_active_chats err: {e}")
    # Fallback to default chat from settings
    _, default_chat, _ = await get_bot_settings()
    if default_chat:
        return [{"chat_id": default_chat, "name": "default", "subscribed_events": None}]
    return []


def chat_subscribed_to(chat: dict, event_type: str) -> bool:
    """If chat.subscribed_events is empty/null → receive all. Else only listed types + test/deployment."""
    if event_type in ("test", "deployment"):
        return True
    subs = (chat.get("subscribed_events") or "").strip()
    if not subs:
        return True
    listed = {s.strip() for s in subs.split(",") if s.strip()}
    return event_type in listed


def build_message(event_type: str, severity: str, message: str,
                  printer: Optional[dict], consumables: list[dict]) -> str:
    emoji = EVENT_EMOJIS.get(event_type, "ℹ️")
    title = EVENT_TITLES_RU.get(event_type, event_type.replace("_", " ").title())
    now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

    lines = [f"{emoji} <b>{_h(title)}</b>"]
    lines.append(f"<i>{now}</i>")

    if printer:
        name = printer.get("name") or "—"
        ip = printer.get("ip_address") or ""
        lines.append("")
        lines.append(f"🖨️ <b>{_h(name)}</b> ({_h(ip)})")
        location = printer.get("location")
        if location:
            lines.append(f"📍 Кабинет: <b>{_h(location)}</b>")
        vendor_model = " ".join(filter(None, [printer.get("vendor"), printer.get("model")]))
        if vendor_model:
            lines.append(f"⚙️ {_h(vendor_model[:120])}")

    if message:
        lines.append("")
        lines.append(f"📋 {_h(message)}")

    if consumables:
        lines.append("")
        lines.append("<b>Картриджи:</b>")
        for c in consumables:
            pct = fmt_pct(c.get("current_level"), c.get("max_capacity"))
            color_emo = COLOR_EMOJIS.get(c.get("name", ""), "▫️")
            label = _h(c.get("name") or "Supply")
            if pct is None:
                lines.append(f"  {color_emo} {label}: — нет данных")
            else:
                bar_len = 10
                filled = int(round(pct / 100 * bar_len))
                bar = "█" * filled + "░" * (bar_len - filled)
                warn = " ⚠️" if pct <= 20 else (" 🛑" if pct <= 5 else "")
                lines.append(f"  {color_emo} {label}: <code>{bar}</code> <b>{pct:.0f}%</b>{warn}")

    sev_emoji = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(severity, "ℹ️")
    lines.append("")
    lines.append(f"{sev_emoji} <b>{severity.upper()}</b>")

    return "\n".join(lines)


async def send_telegram_message(client: httpx.AsyncClient, chat_id: str, text: str) -> bool:
    token, _, _ = await get_bot_settings()
    if not token:
        print("[notification] No bot token configured (DB and env are empty)")
        return False
    # Rate limit per chat
    now = time.time()
    rate_key = f"rate:{chat_id}"
    if rate_key in last_sent and now - last_sent[rate_key] < 1.0:
        await asyncio.sleep(1.0)
    last_sent[rate_key] = time.time()
    try:
        resp = await client.post(
            f"{_telegram_api(token)}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15.0,
        )
        if resp.status_code == 200:
            print(f"[notification] sent → {chat_id} ({len(text)} bytes)")
            return True
        print(f"[notification] Telegram error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"[notification] send error: {e}")
    return False


@app.post("/send")
async def send_notification(data: dict):
    event_type = data.get("event_type", "info")
    message = data.get("message", "")
    severity = data.get("severity", "info")
    printer_id = data.get("printer_id")
    explicit_chat_id = data.get("chat_id")
    explicit_text = data.get("text")

    # Per-event-type throttle via notification_settings + Redis
    # Skip throttle for explicit chat/text override (used by test endpoints)
    if not (explicit_text or explicit_chat_id):
        allow, reason = await should_send(event_type, printer_id)
        if not allow:
            print(f"[notification] skip {event_type}/{printer_id}: {reason}")
            return {"status": "skipped", "reason": reason}

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Pre-built message support (used by /test endpoint from backend)
        if explicit_text:
            _, default_chat, _ = await get_bot_settings()
            target_chats = [{"chat_id": explicit_chat_id or default_chat,
                             "name": "explicit", "subscribed_events": None}]
            text = explicit_text
        else:
            printer = await fetch_printer(client, printer_id) if printer_id else None
            consumables = await fetch_consumables(client, printer_id) if printer_id else []
            text = build_message(event_type, severity, message, printer, consumables)

            # Determine target chats
            if explicit_chat_id:
                target_chats = [{"chat_id": explicit_chat_id, "name": "explicit",
                                 "subscribed_events": None}]
            else:
                all_chats = await fetch_active_chats(client)
                target_chats = [c for c in all_chats if chat_subscribed_to(c, event_type)]

        results = []
        for chat in target_chats:
            cid = chat.get("chat_id")
            if not cid:
                continue
            ok = await send_telegram_message(client, cid, text)
            results.append({"chat_id": cid, "ok": ok})

        # Admin escalation on critical
        _, _, admin_id = await get_bot_settings()
        if severity == "critical" and admin_id and not any(r["chat_id"] == admin_id for r in results):
            await send_telegram_message(client, admin_id, f"🚨 <b>ADMIN ALERT</b>\n\n{text}")

    any_ok = any(r["ok"] for r in results)
    return {
        "status": "sent" if any_ok else "failed",
        "delivered_to": [r["chat_id"] for r in results if r["ok"]],
        "failed": [r["chat_id"] for r in results if not r["ok"]],
    }


@app.post("/send_custom")
async def send_custom(data: dict):
    _, default_chat, _ = await get_bot_settings()
    chat_id = data.get("chat_id", default_chat)
    text = data.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    async with httpx.AsyncClient(timeout=15.0) as client:
        success = await send_telegram_message(client, chat_id, text)
    return {"status": "sent" if success else "failed"}


@app.get("/health")
async def health():
    token, chat, _ = await get_bot_settings()
    return {
        "status": "ok",
        "service": "notification-service",
        "bot_configured": bool(token),
        "default_chat_configured": bool(chat),
        "internal_token_configured": bool(INTERNAL_TOKEN),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9002)
