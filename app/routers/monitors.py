from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Monitor, MonitorStatus
from app.schemas import ErrorResponse, MonitorCreate, MonitorResponse, MonitorUpdate

router = APIRouter(prefix="/monitors", tags=["monitors"])


def _get_monitor_or_404(monitor: Monitor | None) -> Monitor:
    if monitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitor not found")
    return monitor


@router.post(
    "",
    response_model=MonitorResponse,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ErrorResponse}},
)
async def create_monitor(payload: MonitorCreate, db: AsyncSession = Depends(get_db)) -> Monitor:
    monitor = Monitor(
        name=payload.name,
        url=str(payload.url),
        check_interval_sec=payload.check_interval_sec,
        expected_status=payload.expected_status,
        timeout_sec=payload.timeout_sec,
        webhook_url=str(payload.webhook_url) if payload.webhook_url else None,
    )
    db.add(monitor)
    await db.flush()
    await db.refresh(monitor)
    return monitor


@router.get(
    "",
    response_model=list[MonitorResponse],
)
async def list_monitors(db: AsyncSession = Depends(get_db)) -> list[Monitor]:
    result = await db.execute(
        select(Monitor).where(Monitor.status != MonitorStatus.deleted)
    )
    return list(result.scalars().all())


@router.get(
    "/{monitor_id}",
    response_model=MonitorResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_monitor(monitor_id: int, db: AsyncSession = Depends(get_db)) -> Monitor:
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.status != MonitorStatus.deleted,
        )
    )
    return _get_monitor_or_404(result.scalar_one_or_none())


@router.patch(
    "/{monitor_id}",
    response_model=MonitorResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def update_monitor(
    monitor_id: int,
    payload: MonitorUpdate,
    db: AsyncSession = Depends(get_db),
) -> Monitor:
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.status != MonitorStatus.deleted,
        )
    )
    monitor = _get_monitor_or_404(result.scalar_one_or_none())

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "webhook_url" and value is not None:
            value = str(value)
        setattr(monitor, field, value)

    await db.flush()
    await db.refresh(monitor)
    return monitor


@router.delete(
    "/{monitor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
)
async def delete_monitor(monitor_id: int, db: AsyncSession = Depends(get_db)) -> None:
    result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id,
            Monitor.status != MonitorStatus.deleted,
        )
    )
    monitor = _get_monitor_or_404(result.scalar_one_or_none())
    monitor.status = MonitorStatus.deleted
    await db.flush()
