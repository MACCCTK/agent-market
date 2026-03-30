from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class OrderView(BaseModel):
    id: UUID
    order_no: str
    requester_openclaw_id: UUID
    executor_openclaw_id: UUID | None
    task_template_id: UUID
    capability_package_id: UUID | None
    title: str
    status: str
    quoted_price: Decimal
    currency: str
    sla_seconds: int
    requirement_payload: dict[str, Any]
    published_at: str | None
    assigned_at: str | None
    assignment_expires_at: str | None
    acknowledged_at: str | None
    started_at: str | None
    delivered_at: str | None
    review_started_at: str | None
    review_expires_at: str | None
    approved_at: str | None
    settled_at: str | None
    cancelled_at: str | None
    expired_at: str | None
    failed_at: str | None
    latest_failure_code: str | None = None
    latest_failure_note: str | None = None
    assignment_attempt_count: int = 0
    created_at: str
    updated_at: str


class CreateOrderRequest(BaseModel):
    requester_openclaw_id: UUID = Field(
        validation_alias=AliasChoices("requester_openclaw_id", "requester_open_claw_id")
    )
    task_template_id: UUID
    capability_package_id: UUID | None = None
    title: str
    requirement_payload: dict[str, Any]


class AssignOrderRequest(BaseModel):
    executor_openclaw_id: UUID | None = Field(
        default=None,
        validation_alias=AliasChoices("executor_openclaw_id", "executor_open_claw_id"),
    )


class PublishOrderByOpenClawRequest(BaseModel):
    task_template_id: UUID
    capability_package_id: UUID | None = None
    title: str
    requirement_payload: dict[str, Any]


class NotifyResultReadyRequest(BaseModel):
    result_summary: dict[str, Any]


class CompleteOrderRequest(BaseModel):
    delivery_note: str
    deliverable_payload: dict[str, Any]
    result_summary: dict[str, Any]


class OrderSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: UUID
    order_no: str
    requester_openclaw_id: UUID
    executor_openclaw_id: UUID | None
    task_template_id: UUID
    capability_package_id: UUID | None
    title: str
    status: str
    quoted_price: Decimal
    currency: str
    sla_seconds: int
    requirement_payload: dict[str, Any]
    published_at: str | None
    assigned_at: str | None
    assignment_expires_at: str | None
    acknowledged_at: str | None
    started_at: str | None
    delivered_at: str | None
    review_started_at: str | None
    review_expires_at: str | None
    approved_at: str | None
    settled_at: str | None
    cancelled_at: str | None
    expired_at: str | None
    failed_at: str | None
    latest_failure_code: str | None = None
    latest_failure_note: str | None = None
    assignment_attempt_count: int
    created_at: str
    updated_at: str


class OrderDetail(OrderSummary):
    pass


class OrderCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requester_openclaw_id: UUID
    task_template_id: UUID
    capability_package_id: UUID | None = None
    title: str
    requirement_payload: dict[str, Any]


class OrderPublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: UUID


class OrderAcknowledgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executor_openclaw_id: UUID


class OrderStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executor_openclaw_id: UUID


class OrderCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requester_openclaw_id: UUID = Field(
        validation_alias=AliasChoices("requester_openclaw_id", "requester_open_claw_id")
    )
    reason: str | None = None


class ExpireOrderAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pass


class ExpireOrderReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pass


class FailOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executor_openclaw_id: UUID = Field(
        validation_alias=AliasChoices("executor_openclaw_id", "executor_open_claw_id")
    )
    failure_code: str
    failure_note: str | None = None
