from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field


class SettlementFeeView(BaseModel):
    order_id: UUID
    openclaw_id: UUID
    hire_fee: Decimal
    token_used: int
    token_fee: Decimal
    total_fee: Decimal
    currency: str
    settled_at: str


class SettleByTokenUsageRequest(BaseModel):
    token_used: int | None = Field(default=None, ge=0)
    usage_receipt_id: UUID | None = None


class TokenUsageReceiptView(BaseModel):
    id: UUID
    order_id: UUID
    openclaw_id: UUID
    provider: str
    provider_request_id: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    measured_at: str
    receipt_commitment: str
    signature: str
    created_at: str


class CreateTokenUsageReceiptRequest(BaseModel):
    openclaw_id: UUID = Field(
        validation_alias=AliasChoices("openclaw_id", "open_claw_id")
    )
    provider: str
    provider_request_id: str
    model: str
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    measured_at: str | None = None


class SettlementSummary(BaseModel):
    id: UUID
    order_id: UUID
    status: str
    total_amount: Decimal
    currency: str
    settled_at: str | None = None


class SettlementView(SettlementSummary):
    requester_openclaw_id: UUID
    executor_openclaw_id: UUID
    hire_fee: Decimal
    token_fee: Decimal
    platform_fee: Decimal
    external_reference: str | None = None
    created_at: str
    updated_at: str
