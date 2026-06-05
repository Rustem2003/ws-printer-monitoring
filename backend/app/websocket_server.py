import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import redis.asyncio as aioredis

from .core.config import get_settings

app = FastAPI(title="Printer WebSocket Server")
settings = get_settings()

connected_clients: set[WebSocket] = set()


@app.on_event("startup")
async def startup():
    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)


@app.on_event("shutdown")
async def shutdown():
    await app.state.redis.close()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = Query(None)):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type", "")

            if msg_type == "subscribe":
                printer_id = msg.get("printer_id")
                await websocket.send_json({"type": "subscribed", "printer_id": printer_id})
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            # Publish to Redis so other consumers can pick it up
            await app.state.redis.publish("printer_events", data)

    except WebSocketDisconnect:
        connected_clients.discard(websocket)


async def broadcast_event(event: dict):
    """Called by monitoring service to push realtime events to all connected clients."""
    disconnected = set()
    for client in connected_clients:
        try:
            await client.send_json(event)
        except Exception:
            disconnected.add(client)
    connected_clients.difference_update(disconnected)
