from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class DeliverableView(BaseModel):
    id: UUID
    order_id: UUID
    version_no: int
    delivery_note: str
    deliverable_payload: dict[str, Any]
    submitted_by: UUID
    submitted_at: str


class SubmitDeliverableRequest(BaseModel):
    delivery_note: str
    deliverable_payload: dict[str, Any]
    submitted_by_openclaw_id: UUID = Field(
        validation_alias=AliasChoices("submitted_by_openclaw_id", "submitted_by_open_claw_id")
    )


class DeliverableCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_note: str
    deliverable_payload: dict[str, Any]
    submitted_by_openclaw_id: UUID


class DeliverableSummary(BaseModel):
    id: UUID
    order_id: UUID
    version_no: int
    submitted_by_openclaw_id: UUID
    submitted_at: str


class DeliverableDetail(DeliverableSummary):
    delivery_note: str
    deliverable_payload: dict[str, Any]
