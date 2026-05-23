from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl, field_validator

from app.models import MonitorState, MonitorStatus


# ── Monitor ────────────────────────────────────────────────────────────────────

class MonitorCreate(BaseModel):
    name: str
    url: HttpUrl
    check_interval_sec: int = 60
    expected_status: int = 200
    timeout_sec: int = 10
    webhook_url: Optional[HttpUrl] = None

    @field_validator("check_interval_sec")
    @classmethod
    def interval_min_30(cls, v: int) -> int:
        if v < 30:
            raise ValueError("check_interval_sec must be >= 30")
        return v

    @field_validator("timeout_sec")
    @classmethod
    def timeout_min_1(cls, v: int) -> int:
        if v < 1:
            raise ValueError("timeout_sec must be >= 1")
        return v

    @field_validator("expected_status")
    @classmethod
    def valid_http_status(cls, v: int) -> int:
        if not (100 <= v <= 599):
            raise ValueError("expected_status must be a valid HTTP status code (100-599)")
        return v


class MonitorUpdate(BaseModel):
    name: Optional[str] = None
    check_interval_sec: Optional[int] = None
    expected_status: Optional[int] = None
    timeout_sec: Optional[int] = None
    webhook_url: Optional[HttpUrl] = None
    status: Optional[MonitorStatus] = None

    @field_validator("check_interval_sec")
    @classmethod
    def interval_min_30(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 30:
            raise ValueError("check_interval_sec must be >= 30")
        return v

    @field_validator("timeout_sec")
    @classmethod
    def timeout_min_1(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("timeout_sec must be >= 1")
        return v

    @field_validator("expected_status")
    @classmethod
    def valid_http_status(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (100 <= v <= 599):
            raise ValueError("expected_status must be a valid HTTP status code (100-599)")
        return v


class MonitorResponse(BaseModel):
    id: int
    name: str
    url: str
    check_interval_sec: int
    expected_status: int
    timeout_sec: int
    state: MonitorState
    status: MonitorStatus
    webhook_url: Optional[str] = None
    last_checked_at: Optional[datetime] = None
    consecutive_failures: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Check ──────────────────────────────────────────────────────────────────────

class CheckResponse(BaseModel):
    id: int
    monitor_id: int
    checked_at: datetime
    status_code: Optional[int] = None
    latency_ms: Optional[int] = None
    is_ok: bool
    error_message: Optional[str] = None
    body_hash: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Transition ─────────────────────────────────────────────────────────────────

class TransitionResponse(BaseModel):
    id: int
    monitor_id: int
    from_state: MonitorState
    to_state: MonitorState
    at: datetime

    model_config = {"from_attributes": True}


# ── Uptime ─────────────────────────────────────────────────────────────────────

class UptimeResponse(BaseModel):
    monitor_id: int
    window: str
    total_checks: int
    ok_checks: int
    uptime_percent: float


# ── Error ──────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    detail: str
