import pytest
from unittest.mock import AsyncMock, MagicMock
from app.models import Monitor, MonitorState, Transition
from app.worker import _apply_state_machine, FAILURES_BEFORE_DOWN


def make_monitor(**kwargs) -> Monitor:
    monitor = Monitor()
    monitor.id = 1
    monitor.name = "Test"
    monitor.url = "http://example.com"
    monitor.state = kwargs.get("state", MonitorState.unknown)
    monitor.consecutive_failures = kwargs.get("consecutive_failures", 0)
    monitor.webhook_url = kwargs.get("webhook_url", None)
    return monitor


@pytest.mark.asyncio
async def test_first_successful_check_sets_up():
    """Перший успішний check: unknown -> up"""
    monitor = make_monitor(state=MonitorState.unknown)
    db = AsyncMock()
    db.add = MagicMock()

    await _apply_state_machine(db, monitor, is_ok=True, last_error=None)

    assert monitor.state == MonitorState.up
    assert monitor.consecutive_failures == 0


@pytest.mark.asyncio
async def test_two_failures_do_not_trigger_down():
    """2 фейли підряд (consecutive=1 -> 2) — стан не змінюється на down"""
    monitor = make_monitor(state=MonitorState.up, consecutive_failures=1)
    db = AsyncMock()
    db.add = MagicMock()

    await _apply_state_machine(db, monitor, is_ok=False, last_error="Timeout")

    assert monitor.state == MonitorState.up
    assert monitor.consecutive_failures == 2
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_three_failures_trigger_down():
    """3 фейли підряд (consecutive=2 -> 3): up -> down"""
    monitor = make_monitor(state=MonitorState.up, consecutive_failures=2)
    db = AsyncMock()
    db.add = MagicMock()

    await _apply_state_machine(db, monitor, is_ok=False, last_error="Timeout")

    assert monitor.state == MonitorState.down
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_success_after_down_sets_up():
    """1 успіх після down: down -> up"""
    monitor = make_monitor(state=MonitorState.down, consecutive_failures=5)
    db = AsyncMock()
    db.add = MagicMock()

    await _apply_state_machine(db, monitor, is_ok=True, last_error=None)

    assert monitor.state == MonitorState.up
    assert monitor.consecutive_failures == 0
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_failure_from_unknown_stays_unknown():
    """Перший check — fail: state лишається unknown (ще не 3 фейли)"""
    monitor = make_monitor(state=MonitorState.unknown, consecutive_failures=0)
    db = AsyncMock()
    db.add = MagicMock()

    await _apply_state_machine(db, monitor, is_ok=False, last_error="Connection error")

    assert monitor.state == MonitorState.unknown
    assert monitor.consecutive_failures == 1
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_transition_written_on_state_change():
    """При зміні стану пишеться transition в БД"""
    monitor = make_monitor(state=MonitorState.up, consecutive_failures=2)
    db = AsyncMock()
    db.add = MagicMock()

    await _apply_state_machine(db, monitor, is_ok=False, last_error="Timeout")

    assert monitor.state == MonitorState.down
    assert db.add.call_count == 1
    transition = db.add.call_args[0][0]
    assert isinstance(transition, Transition)
    assert transition.from_state == MonitorState.up
    assert transition.to_state == MonitorState.down
