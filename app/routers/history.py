from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Check, Monitor, MonitorStatus
from app.schemas import CheckResponse, ErrorResponse, UptimeResponse

router = APIRouter(prefix="/monitors", tags=["history"])

WINDOW_MAP: dict[str, timedelta] = {
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


async def _get_active_monitor_or_404(monitor_id: int, db: AsyncSession) -> Monitor:
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.status != MonitorStatus.deleted,
        )
    )
    monitor = result.scalar_one_or_none()
    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitor not found",
        )
    return monitor


@router.get(
    "/{monitor_id}/history",
    response_model=list[CheckResponse],
    responses={404: {"model": ErrorResponse}},
)
async def get_history(
    monitor_id: int,
    limit: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> list[Check]:
    await _get_active_monitor_or_404(monitor_id, db)

    result = await db.execute(
        select(Check)
        .where(Check.monitor_id == monitor_id)
        .order_by(Check.checked_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get(
    "/{monitor_id}/uptime",
    response_model=UptimeResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def get_uptime(
    monitor_id: int,
    window: Literal["1h", "24h", "7d", "30d"] = Query(default="24h"),
    db: AsyncSession = Depends(get_db),
) -> UptimeResponse:
    await _get_active_monitor_or_404(monitor_id, db)

    delta = WINDOW_MAP[window]
    since = datetime.utcnow() - delta

    result = await db.execute(
        select(
            func.count().label("total"),
            func.sum(Check.is_ok.cast(Integer)).label("ok"),
        ).where(
            Check.monitor_id == monitor_id,
            Check.checked_at >= since,
        )
    )
    row = result.one()
    total = row.total or 0
    ok = int(row.ok or 0)
    uptime_percent = round((ok / total) * 100, 2) if total > 0 else 0.0

    return UptimeResponse(
        monitor_id=monitor_id,
        window=window,
        total_checks=total,
        ok_checks=ok,
        uptime_percent=uptime_percent,
    )
