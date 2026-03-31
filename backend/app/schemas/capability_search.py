from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AgentCapabilityMatch(BaseModel):
    """Agent with their matching capability package and match score"""
    agent_id: UUID
    agent_name: str
    agent_service_status: str
    agent_subscription_status: str
    capacity_per_week: int
    capability_package_id: UUID
    package_title: str
    package_summary: str
    price_min: Decimal | None
    price_max: Decimal | None
    reputation_score: int
    average_rating: Decimal
    total_completed_tasks: int
    match_score: float  # 0-100, indicates relevance


class SearchCapabilityRequest(BaseModel):
    """Request to search for agents by capability requirements"""
    task_template_id: UUID
    keyword: str | None = None
    min_reputation_score: int = 0
    required_tags: list[str] | None = None
    required_tools: list[str] | None = None
    top_n: int = 3


class SearchCapabilityResult(BaseModel):
    """Search result containing top matching agents"""
    query: str
    matched_agents: list[AgentCapabilityMatch]
    total_matches: int
