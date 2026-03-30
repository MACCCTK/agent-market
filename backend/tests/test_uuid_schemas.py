from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.auth import OpenClawIdentityView, OpenClawLoginRequest, OpenClawRegisterRequest
from app.schemas.orders import OrderSummary


def test_openclaw_register_request_is_openclaw_only() -> None:
    payload = OpenClawRegisterRequest(
        email="agent@example.com",
        password="secret123",
        display_name="Agent Alpha",
        capacity_per_week=6,
        service_config={"provider": "openai"},
        subscription_status="subscribed",
        service_status="available",
        profile={
            "bio": "General agent operator",
            "geo_location": "Singapore",
            "timezone_name": "Asia/Singapore",
            "callback_url": "https://example.com/callback",
        },
        capabilities={
            "gpu_vram": 48,
            "cpu_threads": 16,
            "system_ram": 64,
            "max_concurrency": 4,
            "network_speed": 1000,
            "disk_iops": 12000,
            "env_sandbox": "hybrid",
            "internet_access": True,
            "skill_tags": ["research", "coding"],
            "pre_installed_tools": ["uv", "node"],
            "external_auths": ["github"],
        },
    )

    assert payload.email == "agent@example.com"
    assert payload.capacity_per_week == 6
    assert payload.profile is not None
    assert payload.profile.callback_url == "https://example.com/callback"
    assert payload.capabilities is not None
    assert payload.capabilities.max_concurrency == 4
    assert not hasattr(payload, "roles")
    assert not hasattr(payload, "client_type")


def test_openclaw_login_request_is_openclaw_only() -> None:
    payload = OpenClawLoginRequest(
        email="agent@example.com",
        password="secret123",
    )

    assert payload.email == "agent@example.com"
    assert not hasattr(payload, "as_role")
    assert not hasattr(payload, "client_type")


def test_openclaw_identity_view_uses_uuid() -> None:
    view = OpenClawIdentityView(
        id=uuid4(),
        email="agent@example.com",
        display_name="Agent Alpha",
        user_status="active",
        created_at="2026-03-30T00:00:00Z",
        updated_at="2026-03-30T00:00:00Z",
    )

    assert isinstance(view.id, type(uuid4()))


def test_order_summary_rejects_integer_ids() -> None:
    with pytest.raises(ValidationError):
        OrderSummary(
            id=1,
            order_no="OC-001",
            requester_openclaw_id=2,
            executor_openclaw_id=None,
            task_template_id=3,
            capability_package_id=None,
            title="Need help",
            status="published",
            quoted_price="3.00",
            currency="USD",
            sla_seconds=3600,
            requirement_payload={},
            published_at=None,
            assigned_at=None,
            assignment_expires_at=None,
            acknowledged_at=None,
            started_at=None,
            delivered_at=None,
            review_started_at=None,
            review_expires_at=None,
            approved_at=None,
            settled_at=None,
            cancelled_at=None,
            expired_at=None,
            failed_at=None,
            latest_failure_code=None,
            latest_failure_note=None,
            assignment_attempt_count=0,
            created_at="2026-03-30T00:00:00Z",
            updated_at="2026-03-30T00:00:00Z",
        )
