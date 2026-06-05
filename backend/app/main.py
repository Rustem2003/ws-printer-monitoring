from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from .core import init_db
from .routers import auth, printers, events, discovery, statistics, telegram, notification_settings, system_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Printer Monitoring API",
    description="Enterprise Printer & MFP Monitoring System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(printers.router)
app.include_router(events.router)
app.include_router(discovery.router)
app.include_router(statistics.router)
app.include_router(telegram.router)
app.include_router(notification_settings.router)
app.include_router(system_settings.router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "service": "backend-api"}


@app.get("/")
async def root():
    return {
        "service": "Printer Monitoring API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
