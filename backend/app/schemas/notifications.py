from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class NotificationView(BaseModel):
    id: UUID
    openclaw_id: UUID
    order_id: UUID
    notification_type: str
    status: str
    callback_url: str | None
    payload: dict
    retry_count: int = 0
    last_error: str | None = None
    next_retry_at: str | None = None
    created_at: str
    sent_at: str | None
    acked_at: str | None
    updated_at: str


class HeartbeatView(BaseModel):
    openclaw_id: UUID
    service_status: str
    active_order_id: UUID | None
    assigned_order: object | None
    checked_at: str


class HeartbeatRequest(BaseModel):
    service_status: str


class NotificationSummary(BaseModel):
    id: UUID
    order_id: UUID
    recipient_openclaw_id: UUID
    notification_type: str
    status: str
    requires_ack: bool
    created_at: str
    sent_at: str | None = None
    acked_at: str | None = None


class NotificationDetail(NotificationSummary):
    callback_url: str | None = None
    payload: dict
    retry_count: int = 0
    last_error: str | None = None
    next_retry_at: str | None = None
    updated_at: str


class NotificationRetryProcessSummary(BaseModel):
    attempted: int
    sent: int
    retry_scheduled: int
    dead_letter: int


class NotificationDeliveryMetrics(BaseModel):
    total_notifications: int
    callback_configured_total: int
    callback_success_total: int
    callback_failure_total: int
    callback_success_rate: float
    pending_total: int
    sent_total: int
    acked_total: int
    retry_scheduled_total: int
    dead_letter_total: int


class NotificationAlertSummary(BaseModel):
    has_alerts: bool
    retry_scheduled_total: int
    dead_letter_total: int
    callback_failure_total: int
    retry_scheduled_notifications: list[NotificationView]
    dead_letter_notifications: list[NotificationView]
