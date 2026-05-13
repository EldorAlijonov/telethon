from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    blocked = "blocked"
    expired = "expired"
    rejected = "rejected"


class BroadcastStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    finished = "finished"
    failed = "failed"


class DeliveryStatus(str, enum.Enum):
    pending = "pending"
    delivered = "delivered"
    failed = "failed"
    dead_letter = "dead_letter"


class SuspiciousActivityKind(str, enum.Enum):
    otp_bruteforce = "otp_bruteforce"
    callback_abuse = "callback_abuse"
    flood = "flood"
    duplicate_signal = "duplicate_signal"


class AuditAction(str, enum.Enum):
    user_registered = "user_registered"
    user_approved = "user_approved"
    user_rejected = "user_rejected"
    user_blocked = "user_blocked"
    user_deleted = "user_deleted"
    session_connected = "session_connected"
    session_revoked = "session_revoked"
    monitoring_started = "monitoring_started"
    monitoring_stopped = "monitoring_stopped"
    signal_sent = "signal_sent"
    broadcast_created = "broadcast_created"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(128), index=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.pending, index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    keywords: Mapped[list["Keyword"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    session: Mapped["TelegramSession | None"] = relationship(back_populates="user", cascade="all, delete-orphan")


class Approval(Base, TimestampMixin):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    admin_tg_id: Mapped[int | None] = mapped_column(BigInteger)
    decision: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str | None] = mapped_column(Text)
    access_days: Mapped[int | None] = mapped_column(Integer)


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source: Mapped[str] = mapped_column(String(64), default="admin")


class Keyword(Base, TimestampMixin):
    __tablename__ = "keywords"
    __table_args__ = (UniqueConstraint("user_id", "keyword", name="uq_keywords_user_keyword"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    keyword: Mapped[str] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    user: Mapped[User] = relationship(back_populates="keywords")


class MonitoredChat(Base, TimestampMixin):
    __tablename__ = "monitored_chats"
    __table_args__ = (UniqueConstraint("user_id", "chat_id", name="uq_monitored_chats_user_chat"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class TelegramSession(Base, TimestampMixin):
    __tablename__ = "telegram_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    phone: Mapped[str] = mapped_column(String(32))
    encrypted_session: Mapped[str] = mapped_column(Text)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped[User] = relationship(back_populates="session")


class Signal(Base, TimestampMixin):
    __tablename__ = "signals"
    __table_args__ = (
        UniqueConstraint("user_id", "chat_id", "message_id", "keyword", name="uq_signal_dedupe"),
        Index("ix_signals_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    message_id: Mapped[int] = mapped_column(BigInteger)
    keyword: Mapped[str] = mapped_column(String(128), index=True)
    matched_text: Mapped[str] = mapped_column(Text)
    source_chat: Mapped[str | None] = mapped_column(String(255))
    sender_info: Mapped[str | None] = mapped_column(String(255))
    message_link: Mapped[str | None] = mapped_column(Text)
    message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SignalDelivery(Base, TimestampMixin):
    __tablename__ = "signal_deliveries"
    __table_args__ = (
        UniqueConstraint("signal_id", "recipient_tg_id", name="uq_signal_delivery_recipient"),
        Index("ix_signal_deliveries_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id", ondelete="CASCADE"), index=True)
    recipient_tg_id: Mapped[int] = mapped_column(BigInteger, index=True)
    status: Mapped[DeliveryStatus] = mapped_column(Enum(DeliveryStatus), default=DeliveryStatus.pending, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BroadcastJob(Base, TimestampMixin):
    __tablename__ = "broadcast_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_tg_id: Mapped[int] = mapped_column(BigInteger, index=True)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[BroadcastStatus] = mapped_column(Enum(BroadcastStatus), default=BroadcastStatus.pending, index=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_tg_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    target_tg_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction), index=True)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)


class RateLimitRecord(Base, TimestampMixin):
    __tablename__ = "rate_limits"
    __table_args__ = (UniqueConstraint("scope", "subject", "window_key", name="uq_rate_limit_window"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scope: Mapped[str] = mapped_column(String(64), index=True)
    subject: Mapped[str] = mapped_column(String(128), index=True)
    window_key: Mapped[str] = mapped_column(String(64), index=True)
    counter: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class SuspiciousActivity(Base, TimestampMixin):
    __tablename__ = "suspicious_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    kind: Mapped[SuspiciousActivityKind] = mapped_column(Enum(SuspiciousActivityKind), index=True)
    severity: Mapped[str] = mapped_column(String(32), default="medium", index=True)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)


class Setting(Base, TimestampMixin):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, default=dict)
