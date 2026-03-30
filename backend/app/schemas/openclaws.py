from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OpenClawView(BaseModel):
    id: UUID
    name: str
    subscription_status: str
    service_status: str
    active_order_id: UUID | None
    updated_at: str


class OpenClawProfileView(BaseModel):
    id: UUID
    name: str
    capacity_per_week: int
    service_config: dict[str, Any]
    subscription_status: str
    service_status: str
    updated_at: str


class RegisterOpenClawRequest(BaseModel):
    id: UUID | None = None
    name: str
    capacity_per_week: int = Field(ge=1)
    service_config: dict[str, Any]
    subscription_status: str
    service_status: str


class UpdateSubscriptionRequest(BaseModel):
    subscription_status: str


class UpdateServiceStatusRequest(BaseModel):
    service_status: str
    active_order_id: UUID | None = None


class OpenClawRuntimeView(BaseModel):
    id: UUID
    subscription_status: str
    service_status: str
    last_heartbeat_at: str | None = None
    updated_at: str


class OpenClawSummary(BaseModel):
    id: UUID
    email: str
    display_name: str
    user_status: str
    runtime: OpenClawRuntimeView


class OpenClawCapabilityView(BaseModel):
    gpu_vram: int = 0
    cpu_threads: int = 0
    system_ram: int = 0
    max_concurrency: int = 1
    network_speed: int = 0
    disk_iops: int = 0
    env_sandbox: str = "linux_shell"
    internet_access: bool = False
    skill_tags: list[str] = []
    pre_installed_tools: list[str] = []
    external_auths: list[str] = []


class OpenClawReputationView(BaseModel):
    total_completed_tasks: int = 0
    average_rating: float = 0.0
    positive_rate: float = 0.0
    reliability_score: int = 0
    latest_feedback: str | None = None


class OpenClawProfileDetail(BaseModel):
    bio: str | None = None
    geo_location: str | None = None
    timezone_name: str | None = None
    callback_url: str | None = None


class OpenClawDetail(BaseModel):
    id: UUID
    email: str
    display_name: str
    user_status: str
    runtime: OpenClawRuntimeView
    profile: OpenClawProfileDetail
    capabilities: OpenClawCapabilityView
    reputation: OpenClawReputationView
    created_at: str
    updated_at: str


class OpenClawProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capacity_per_week: int | None = Field(default=None, ge=1)
    service_config: dict[str, Any] | None = None
    bio: str | None = None
    geo_location: str | None = None
    timezone_name: str | None = None
    callback_url: str | None = None


class OpenClawCapabilityUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gpu_vram: int | None = Field(default=None, ge=0)
    cpu_threads: int | None = Field(default=None, ge=0)
    system_ram: int | None = Field(default=None, ge=0)
    max_concurrency: int | None = Field(default=None, ge=1)
    network_speed: int | None = Field(default=None, ge=0)
    disk_iops: int | None = Field(default=None, ge=0)
    env_sandbox: str | None = None
    internet_access: bool | None = None
    skill_tags: list[str] | None = None
    pre_installed_tools: list[str] | None = None
    external_auths: list[str] | None = None


class OpenClawRegisterRequestPayload(BaseModel):
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
