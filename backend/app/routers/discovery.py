from typing import Optional
from datetime import datetime
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core import get_db, get_current_user, get_user_or_internal
from ..core.config import get_settings
from ..models.scan_job import ScanJob
from ..schemas import ScanJobResponse


class ScanStartBody(BaseModel):
    subnet: Optional[str] = None
    subnets: Optional[list[str]] = None
    method: Optional[str] = "snmp_broadcast"


class ScanStatusBody(BaseModel):
    job_id: int
    status: str
    devices_found: Optional[int] = 0
    devices_added: Optional[int] = 0
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])


@router.post("/start", response_model=ScanJobResponse)
async def start_discovery(
    body: ScanStartBody,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    settings = get_settings()
    subnet = body.subnet or (body.subnets[0] if body.subnets else "192.168.0.0/24")
    method = body.method or "snmp_broadcast"

    job = ScanJob(
        job_type="manual",
        status="pending",
        subnet=subnet,
        method=method,
        started_by=current_user.id,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"{settings.discovery_service_url}/scan",
                json={"subnet": subnet, "method": method, "job_id": job.id},
                timeout=10.0,
            )
            job.status = "running"
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)[:500]

    await db.flush()
    await db.refresh(job)
    return ScanJobResponse.model_validate(job)


@router.get("/status", response_model=list[ScanJobResponse])
async def scan_status(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(ScanJob).order_by(ScanJob.created_at.desc()).limit(20)
    )
    return [ScanJobResponse.model_validate(j) for j in result.scalars().all()]


@router.put("/status")
async def update_scan_status(
    body: ScanStatusBody,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_user_or_internal),
):
    result = await db.execute(select(ScanJob).where(ScanJob.id == body.job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = body.status
    job.devices_found = body.devices_found or 0
    job.devices_added = body.devices_added or 0
    if body.completed_at:
        job.completed_at = body.completed_at
    if body.error_message:
        job.error_message = body.error_message[:500]
    await db.flush()
    return {"ok": True}
