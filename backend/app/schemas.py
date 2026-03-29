from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import AliasChoices, BaseModel, Field, field_validator


class UserView(BaseModel):
    id: int
    email: str
    display_name: str
    status: str
    roles: list[str]
    created_at: str
    updated_at: str


class AuthView(BaseModel):
    access_token: str
    token_type: str
    user: UserView


class OpenClawView(BaseModel):
    id: int
    name: str
    subscription_status: str
    service_status: str
    active_order_id: int | None
    updated_at: str


class OpenClawProfileView(BaseModel):
    id: int
    name: str
    capacity_per_week: int
    service_config: dict[str, Any]
    subscription_status: str
    service_status: str
    updated_at: str


class TaskTemplateView(BaseModel):
    id: int
    code: str
    name: str
    task_type: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    acceptance_schema: dict[str, Any]
    pricing_model: str
    base_price: Decimal
    sla_hours: int
    status: str


class CapabilityPackageView(BaseModel):
    id: int
    owner_openclaw_id: int
    title: str
    summary: str
    task_template_id: int
    sample_deliverables: dict[str, Any]
    price_min: Decimal | None
    price_max: Decimal | None
    capacity_per_week: int
    status: str
    created_at: str
    updated_at: str


class OrderView(BaseModel):
    id: int
    order_no: str
    requester_openclaw_id: int
    executor_openclaw_id: int | None
    task_template_id: int
    capability_package_id: int | None
    title: str
    status: str
    quoted_price: Decimal
    currency: str
    sla_hours: int
    requirement_payload: dict[str, Any]
    accepted_at: str | None
    delivered_at: str | None
    completed_at: str | None
    cancelled_at: str | None
    created_at: str
    updated_at: str


class DeliverableView(BaseModel):
    id: int
    order_id: int
    version_no: int
    delivery_note: str
    deliverable_payload: dict[str, Any]
    submitted_by: int
    submitted_at: str


class DisputeView(BaseModel):
    id: int
    order_id: int
    opened_by: int
    reason_code: str
    description: str
    status: str
    created_at: str


class SettlementFeeView(BaseModel):
    order_id: int
    openclaw_id: int
    hire_fee: Decimal
    token_used: int
    token_fee: Decimal
    total_fee: Decimal
    currency: str
    settled_at: str


class NotificationView(BaseModel):
    id: int
    openclaw_id: int
    order_id: int
    notification_type: str
    status: str
    callback_url: str | None
    payload: dict[str, Any]
    created_at: str
    sent_at: str | None
    acked_at: str | None
    updated_at: str


class HeartbeatView(BaseModel):
    openclaw_id: int
    service_status: str
    active_order_id: int | None
    assigned_order: OrderView | None
    checked_at: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str
    roles: list[str] | None = None
    client_type: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str
    as_role: str | None = None
    client_type: str | None = None


class RegisterOpenClawRequest(BaseModel):
    id: int | None = None
    name: str
    capacity_per_week: int = Field(ge=1)
    service_config: dict[str, Any]
    subscription_status: str
    service_status: str


class UpdateSubscriptionRequest(BaseModel):
    subscription_status: str


class UpdateServiceStatusRequest(BaseModel):
    service_status: str
    active_order_id: int | None = None


class HeartbeatRequest(BaseModel):
    service_status: str


class PublishOrderByOpenClawRequest(BaseModel):
    task_template_id: int
    capability_package_id: int | None = None
    title: str
    requirement_payload: dict[str, Any]


class NotifyResultReadyRequest(BaseModel):
    result_summary: dict[str, Any]


class CompleteOrderRequest(BaseModel):
    delivery_note: str
    deliverable_payload: dict[str, Any]
    result_summary: dict[str, Any]


class ReceiveResultRequest(BaseModel):
    checklist_result: dict[str, Any]
    note: str | None = None


class SettleByTokenUsageRequest(BaseModel):
    token_used: int = Field(ge=0)


class CreateCapabilityPackageRequest(BaseModel):
    owner_openclaw_id: int = Field(
        validation_alias=AliasChoices("owner_openclaw_id", "owner_open_claw_id")
    )
    title: str
    summary: str
    task_template_id: int
    sample_deliverables: dict[str, Any] | None = None
    price_min: Decimal | None = None
    price_max: Decimal | None = None
    capacity_per_week: int = Field(ge=1)
    status: str


class CreateOrderRequest(BaseModel):
    requester_openclaw_id: int = Field(
        validation_alias=AliasChoices("requester_openclaw_id", "requester_open_claw_id")
    )
    task_template_id: int
    capability_package_id: int | None = None
    title: str
    requirement_payload: dict[str, Any]


class AssignOrderRequest(BaseModel):
    executor_openclaw_id: int | None = Field(
        default=None,
        validation_alias=AliasChoices("executor_openclaw_id", "executor_open_claw_id"),
    )


class SubmitDeliverableRequest(BaseModel):
    delivery_note: str
    deliverable_payload: dict[str, Any]
    submitted_by_openclaw_id: int = Field(
        validation_alias=AliasChoices("submitted_by_openclaw_id", "submitted_by_open_claw_id")
    )


class ApproveAcceptanceRequest(BaseModel):
    requester_openclaw_id: int = Field(
        validation_alias=AliasChoices("requester_openclaw_id", "requester_open_claw_id")
    )
    checklist_result: dict[str, Any]
    comment: str | None = None


class CreateDisputeRequest(BaseModel):
    opened_by_openclaw_id: int = Field(
        validation_alias=AliasChoices("opened_by_openclaw_id", "opened_by_open_claw_id")
    )
    reason_code: str
    description: str


class ApiErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str


class PaginationQuery(BaseModel):
    page: int = Field(default=0, ge=0)
    size: int = Field(default=20, ge=1)
    sort: str = "id,asc"


class SearchOpenClawQuery(BaseModel):
    keyword: str | None = None
    page: int = Field(default=0, ge=0)
    size: int = Field(default=20, ge=1)


class PriceRangeMixin(BaseModel):
    price_min: Decimal | None
    price_max: Decimal | None

    @field_validator("price_max")
    @classmethod
    def check_price_range(cls, value: Decimal | None, info):
        price_min = info.data.get("price_min")
        if value is not None and price_min is not None and price_min > value:
            raise ValueError("price_max must be >= price_min")
        return value
