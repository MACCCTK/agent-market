from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ApproveAcceptanceRequest(BaseModel):
    requester_openclaw_id: UUID = Field(
        validation_alias=AliasChoices("requester_openclaw_id", "requester_open_claw_id")
    )
    checklist_result: dict[str, Any]
    comment: str | None = None


class ReceiveResultRequest(BaseModel):
    checklist_result: dict[str, Any]
    note: str | None = None


class OrderReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requester_openclaw_id: UUID
    decision: str
    checklist_result: dict[str, Any]
    comment: str | None = None


class OrderReviewView(BaseModel):
    id: UUID
    order_id: UUID
    reviewed_by_openclaw_id: UUID
    decision: str
    checklist_result: dict[str, Any]
    comment: str | None = None
    created_at: str
