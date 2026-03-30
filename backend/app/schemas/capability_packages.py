from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field

from .common import PriceRangeMixin


class CapabilityPackageView(BaseModel):
    id: UUID
    owner_openclaw_id: UUID
    title: str
    summary: str
    task_template_id: UUID
    sample_deliverables: dict[str, Any]
    price_min: Decimal | None
    price_max: Decimal | None
    capacity_per_week: int
    status: str
    created_at: str
    updated_at: str


class CreateCapabilityPackageRequest(PriceRangeMixin):
    owner_openclaw_id: UUID = Field(
        validation_alias=AliasChoices("owner_openclaw_id", "owner_open_claw_id")
    )
    title: str
    summary: str
    task_template_id: UUID
    sample_deliverables: dict[str, Any] | None = None
    capacity_per_week: int = Field(ge=1)
    status: str


class CapabilityPackageDetail(BaseModel):
    id: UUID
    owner_openclaw_id: UUID
    task_template_id: UUID
    title: str
    summary: str
    sample_deliverables: dict[str, Any]
    price_min: Decimal | None
    price_max: Decimal | None
    capacity_per_week: int
    status: str
    created_at: str
    updated_at: str
