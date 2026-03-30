from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class DisputeView(BaseModel):
    id: UUID
    order_id: UUID
    opened_by: UUID
    reason_code: str
    description: str
    status: str
    created_at: str
    resolution_payload: dict[str, Any] = Field(default_factory=dict)
    updated_at: str | None = None


class CreateDisputeRequest(BaseModel):
    opened_by_openclaw_id: UUID = Field(
        validation_alias=AliasChoices("opened_by_openclaw_id", "opened_by_open_claw_id")
    )
    reason_code: str
    description: str


class OrderDisputeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    opened_by_openclaw_id: UUID
    reason_code: str
    description: str


class OrderDisputeView(BaseModel):
    id: UUID
    order_id: UUID
    opened_by_openclaw_id: UUID
    reason_code: str
    description: str
    status: str
    created_at: str
    updated_at: str | None = None


class ResolveDisputeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str
    operator_note: str | None = None
    token_used: int | None = Field(default=None, ge=0)
