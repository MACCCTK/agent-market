from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class TaskTemplateView(BaseModel):
    id: UUID
    code: str
    name: str
    task_type: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    acceptance_schema: dict[str, Any]
    pricing_model: str
    default_price: Decimal
    default_sla_seconds: int
    status: str
    created_at: str | None = None
    updated_at: str | None = None
