import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class MonitorState(str, enum.Enum):
    unknown = "unknown"
    up = "up"
    down = "down"


class MonitorStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    deleted = "deleted"


class Monitor(Base):
    __tablename__ = "monitors"

    id = Column(Integer, primary_key=True, autoincrement=True, unsigned=True)
    name = Column(String(255), nullable=False)
    url = Column(String(2048), nullable=False)
    check_interval_sec = Column(SmallInteger, nullable=False, default=60)
    expected_status = Column(SmallInteger, nullable=False, default=200)
    timeout_sec = Column(Integer, nullable=False, default=10)
    state = Column(Enum(MonitorState), nullable=False, default=MonitorState.unknown)
    status = Column(Enum(MonitorStatus), nullable=False, default=MonitorStatus.active)
    webhook_url = Column(String(2048), nullable=True)
    last_checked_at = Column(DateTime, nullable=True)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    checks = relationship("Check", back_populates="monitor", cascade="all, delete-orphan")
    transitions = relationship("Transition", back_populates="monitor", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_monitors_status_last_checked", "status", "last_checked_at"),
    )


class Check(Base):
    __tablename__ = "checks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    monitor_id = Column(Integer, ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False)
    checked_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    status_code = Column(SmallInteger, nullable=True)
    latency_ms = Column(SmallInteger, nullable=True)
    is_ok = Column(Boolean, nullable=False, default=False)
    error_message = Column(String(1024), nullable=True)
    body_hash = Column(String(64), nullable=True)

    monitor = relationship("Monitor", back_populates="checks")

    __table_args__ = (
        Index("idx_checks_monitor_checked", "monitor_id", "checked_at"),
    )


class Transition(Base):
    __tablename__ = "transitions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    monitor_id = Column(Integer, ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False)
    from_state = Column(Enum(MonitorState), nullable=False)
    to_state = Column(Enum(MonitorState), nullable=False)
    at = Column(DateTime, nullable=False, default=datetime.utcnow)

    monitor = relationship("Monitor", back_populates="transitions")

    __table_args__ = (
        Index("idx_transitions_monitor", "monitor_id", "at"),
    )
