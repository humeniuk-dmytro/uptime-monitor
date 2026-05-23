import asyncio
import hashlib
import logging
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Check, Monitor, MonitorState, MonitorStatus, Transition

logger = logging.getLogger(__name__)

FAILURES_BEFORE_DOWN = 3


async def _send_webhook(
    webhook_url: str,
    monitor: Monitor,
    from_state: MonitorState,
    to_state: MonitorState,
    last_error: str | None,
) -> None:
    payload = {
        "monitor_id": monitor.id,
        "name": monitor.name,
        "from": from_state.value,
        "to": to_state.value,
        "at": datetime.utcnow().isoformat(),
        "url": monitor.url,
        "last_error": last_error,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(webhook_url, json=payload)
            logger.info(
                "Webhook sent for monitor %d: %s -> %s (status %d)",
                monitor.id,
                from_state.value,
                to_state.value,
                response.status_code,
            )
    except Exception as exc:
        logger.warning("Webhook failed for monitor %d: %s", monitor.id, exc)


async def _apply_state_machine(
    db: AsyncSession,
    monitor: Monitor,
    is_ok: bool,
    last_error: str | None,
) -> None:
    previous_state = monitor.state

    if is_ok:
        monitor.consecutive_failures = 0
        if monitor.state == MonitorState.down:
            monitor.state = MonitorState.up
    else:
        monitor.consecutive_failures += 1
        if (
            monitor.consecutive_failures >= FAILURES_BEFORE_DOWN
            and monitor.state != MonitorState.down
        ):
            monitor.state = MonitorState.down

    # перший успішний check — переводимо з unknown в up
    if is_ok and previous_state == MonitorState.unknown:
        monitor.state = MonitorState.up

    state_changed = monitor.state != previous_state

    if state_changed:
        transition = Transition(
            monitor_id=monitor.id,
            from_state=previous_state,
            to_state=monitor.state,
        )
        db.add(transition)
        logger.info(
            "Monitor %d transition: %s -> %s",
            monitor.id,
            previous_state.value,
            monitor.state.value,
        )

        if monitor.webhook_url:
            asyncio.create_task(
                _send_webhook(
                    webhook_url=monitor.webhook_url,
                    monitor=monitor,
                    from_state=previous_state,
                    to_state=monitor.state,
                    last_error=last_error,
                )
            )


async def _ping_monitor(db: AsyncSession, monitor: Monitor) -> None:
    # одразу оновлюємо last_checked_at щоб уникнути дублів при рестарті
    monitor.last_checked_at = datetime.utcnow()
    await db.flush()

    status_code: int | None = None
    latency_ms: int | None = None
    error_message: str | None = None
    body_hash: str | None = None
    is_ok = False

    try:
        start = asyncio.get_event_loop().time()
        async with httpx.AsyncClient(timeout=monitor.timeout_sec) as client:
            response = await client.get(monitor.url)
        elapsed = asyncio.get_event_loop().time() - start

        status_code = response.status_code
        latency_ms = int(elapsed * 1000)
        is_ok = status_code == monitor.expected_status
        body_hash = hashlib.sha256(response.content).hexdigest()

    except httpx.TimeoutException:
        error_message = "Timeout"
    except httpx.ConnectError as exc:
        error_message = f"Connection error: {exc}"
    except Exception as exc:
        error_message = f"Unexpected error: {exc}"

    check = Check(
        monitor_id=monitor.id,
        status_code=status_code,
        latency_ms=latency_ms,
        is_ok=is_ok,
        error_message=error_message,
        body_hash=body_hash,
    )
    db.add(check)

    await _apply_state_machine(db, monitor, is_ok, error_message)

    logger.info(
        "Monitor %d [%s] — ok=%s status=%s latency=%sms error=%s",
        monitor.id,
        monitor.url,
        is_ok,
        status_code,
        latency_ms,
        error_message,
    )


async def _tick() -> None:
    async with AsyncSessionLocal() as db:
        try:
            now = datetime.utcnow()
            result = await db.execute(
                select(Monitor).where(
                    Monitor.status == MonitorStatus.active,
                    Monitor.last_checked_at.is_(None)
                    | (
                        Monitor.last_checked_at
                        <= (now - Monitor.check_interval_sec * 1)
                    ),
                )
            )
            monitors = list(result.scalars().all())

            for monitor in monitors:
                try:
                    await _ping_monitor(db, monitor)
                except Exception as exc:
                    logger.exception("Failed to ping monitor %d: %s", monitor.id, exc)

            await db.commit()

        except Exception as exc:
            logger.exception("Worker tick failed: %s", exc)
            await db.rollback()


async def run_worker() -> None:
    logger.info("Worker started, tick every %d sec", settings.WORKER_TICK_SEC)
    while True:
        try:
            await _tick()
        except Exception as exc:
            logger.exception("Unexpected worker error: %s", exc)
        await asyncio.sleep(settings.WORKER_TICK_SEC)
