from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .openclaws import OpenClawCapabilityUpdateRequest, OpenClawProfileUpdateRequest


class OpenClawIdentityView(BaseModel):
    id: UUID
    email: str
    display_name: str
    user_status: str
    created_at: str
    updated_at: str


class OpenClawAuthResponse(BaseModel):
    access_token: str
    token_type: str
    openclaw: OpenClawIdentityView


class OpenClawRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str
    display_name: str
    capacity_per_week: int = Field(default=1, ge=1)
    service_config: dict[str, Any] = Field(default_factory=dict)
    subscription_status: str = "unsubscribed"
    service_status: str = "offline"
    profile: OpenClawProfileUpdateRequest | None = None
    capabilities: OpenClawCapabilityUpdateRequest | None = None


class OpenClawLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str
