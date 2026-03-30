from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
import psycopg
from psycopg.rows import dict_row
from fastapi.testclient import TestClient

from app import main as main_module
from app.service import MarketplaceService


OPENCLAW_VIEW_KEYS = {
    "id",
    "name",
    "subscription_status",
    "service_status",
    "active_order_id",
    "updated_at",
}

OPENCLAW_PROFILE_VIEW_KEYS = {
    "id",
    "name",
    "capacity_per_week",
    "service_config",
    "subscription_status",
    "service_status",
    "updated_at",
}

TASK_TEMPLATE_VIEW_KEYS = {
    "id",
    "code",
    "name",
    "task_type",
    "description",
    "input_schema",
    "output_schema",
    "acceptance_schema",
    "pricing_model",
    "default_price",
    "default_sla_seconds",
    "status",
    "created_at",
    "updated_at",
}

CAPABILITY_PACKAGE_VIEW_KEYS = {
    "id",
    "owner_openclaw_id",
    "title",
    "summary",
    "task_template_id",
    "sample_deliverables",
    "price_min",
    "price_max",
    "capacity_per_week",
    "status",
    "created_at",
    "updated_at",
}

ORDER_VIEW_KEYS = {
    "id",
    "order_no",
    "requester_openclaw_id",
    "executor_openclaw_id",
    "task_template_id",
    "capability_package_id",
    "title",
    "status",
    "quoted_price",
    "currency",
    "sla_seconds",
    "requirement_payload",
    "published_at",
    "assigned_at",
    "assignment_expires_at",
    "acknowledged_at",
    "started_at",
    "delivered_at",
    "review_started_at",
    "review_expires_at",
    "approved_at",
    "settled_at",
    "cancelled_at",
    "expired_at",
    "failed_at",
    "latest_failure_code",
    "latest_failure_note",
    "assignment_attempt_count",
    "created_at",
    "updated_at",
}

DELIVERABLE_VIEW_KEYS = {
    "id",
    "order_id",
    "version_no",
    "delivery_note",
    "deliverable_payload",
    "submitted_by",
    "submitted_at",
}

DISPUTE_VIEW_KEYS = {
    "id",
    "order_id",
    "opened_by",
    "reason_code",
    "description",
    "status",
    "created_at",
    "resolution_payload",
    "updated_at",
}

SETTLEMENT_VIEW_KEYS = {
    "order_id",
    "openclaw_id",
    "hire_fee",
    "token_used",
    "token_fee",
    "total_fee",
    "currency",
    "settled_at",
}

TOKEN_USAGE_RECEIPT_VIEW_KEYS = {
    "id",
    "order_id",
    "openclaw_id",
    "provider",
    "provider_request_id",
    "model",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "measured_at",
    "receipt_commitment",
    "signature",
    "created_at",
}

NOTIFICATION_VIEW_KEYS = {
    "id",
    "openclaw_id",
    "order_id",
    "notification_type",
    "status",
    "callback_url",
    "payload",
    "retry_count",
    "last_error",
    "next_retry_at",
    "created_at",
    "sent_at",
    "acked_at",
    "updated_at",
}

HEARTBEAT_VIEW_KEYS = {
    "openclaw_id",
    "service_status",
    "active_order_id",
    "assigned_order",
    "checked_at",
}

OPENCLAW_DETAIL_KEYS = {
    "id",
    "email",
    "display_name",
    "user_status",
    "runtime",
    "profile",
    "capabilities",
    "reputation",
    "created_at",
    "updated_at",
}


def assert_exact_keys(payload: dict, expected_keys: set[str]) -> None:
    assert set(payload.keys()) == expected_keys


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def bootstrap_openclaw_auth_headers(client: TestClient, openclaw_id: str) -> dict[str, str]:
    parsed_id = UUID(openclaw_id)
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"bootstrap+{parsed_id.hex[:16]}@openclaw.local",
            "password": openclaw_id,
        },
    )
    assert response.status_code == 200
    return auth_headers(response.json()["access_token"])


@pytest.fixture()
def client() -> TestClient:
    db_url = (os.getenv("TEST_MARKETPLACE_DB_URL") or os.getenv("MARKETPLACE_DB_URL") or "").strip()
    if not db_url:
        pytest.skip("PostgreSQL URL is required: set TEST_MARKETPLACE_DB_URL or MARKETPLACE_DB_URL")

    MarketplaceService(db_url=db_url)

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                TRUNCATE TABLE
                    openclaw_usage_receipts,
                    settlements,
                    order_notifications,
                    order_events,
                    order_disputes,
                    order_reviews,
                    order_deliverables,
                    orders,
                    capability_packages,
                    openclaw_reputation_stats,
                    openclaw_capabilities,
                    openclaw_profiles,
                    openclaws
                """
            )
        conn.commit()

    main_module.service = MarketplaceService(db_url=db_url)
    return TestClient(main_module.app)


def register_openclaw(client: TestClient, openclaw_id: str, name: str, service_status: str = "available") -> dict:
    response = client.post(
        "/api/v1/openclaws/register",
        json={
            "id": openclaw_id,
            "name": name,
            "capacity_per_week": 10,
            "service_config": {},
            "subscription_status": "subscribed",
            "service_status": service_status,
        },
    )
    assert response.status_code == 200
    return response.json()


def register_openclaw_actor(
    client: TestClient,
    openclaw_id: str,
    name: str,
    service_status: str = "available",
) -> tuple[dict, dict[str, str]]:
    profile = register_openclaw(client, openclaw_id, name, service_status)
    return profile, bootstrap_openclaw_auth_headers(client, openclaw_id)


def expire_order_deadline_in_service(order_id: str, *, assignment: bool = False, review: bool = False) -> None:
    service = main_module.service
    assert service is not None

    order_uuid = UUID(order_id)
    order = service.orders[order_uuid]
    updates = {"updated_at": "2026-03-30T00:00:00Z"}
    if assignment:
        updates["assignment_expires_at"] = "2026-03-30T00:00:00Z"
    if review:
        updates["review_expires_at"] = "2026-03-30T00:00:00Z"
    updated = order.model_copy(update=updates)
    service.orders[order_uuid] = updated
    service._persist_order_snapshot(updated)


def update_notification_retry_due_in_service(notification_id: str, *, next_retry_at: str) -> None:
    service = main_module.service
    assert service is not None

    notification_uuid = UUID(notification_id)
    notification = service.notifications[notification_uuid]
    updated = notification.model_copy(update={"next_retry_at": next_retry_at, "updated_at": next_retry_at})
    service.notifications[notification_uuid] = updated
    service._persist_notification(updated)


def first_template_id(client: TestClient) -> str:
    response = client.get("/api/v1/task-templates")
    assert response.status_code == 200
    templates = response.json()
    assert templates
    return templates[0]["id"]


def test_trade_flow_auto_assign_deliver_approve_settle(client: TestClient) -> None:
    requester_id = str(uuid4())
    executor_id = str(uuid4())
    template_id = first_template_id(client)

    _, requester_headers = register_openclaw_actor(client, requester_id, "Requester-A", "available")
    _, executor_headers = register_openclaw_actor(client, executor_id, "Executor-B", "available")

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "title": "Need research brief",
            "requirement_payload": {"topic": "agent marketplace"},
        },
        headers=requester_headers,
    )
    assert create_order_resp.status_code == 200
    order = create_order_resp.json()
    assert_exact_keys(order, ORDER_VIEW_KEYS)
    assert order["status"] == "assigned"
    assert order["executor_openclaw_id"] == executor_id

    order_id = order["id"]

    acknowledge_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/orders/{order_id}/accept",
        headers=executor_headers,
    )
    assert acknowledge_resp.status_code == 200
    acknowledged_order = acknowledge_resp.json()
    assert acknowledged_order["status"] == "acknowledged"
    assert acknowledged_order["acknowledged_at"] is not None

    deliver_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/orders/{order_id}/complete",
        json={
            "delivery_note": "Draft delivered",
            "deliverable_payload": {"doc_url": "https://example.com/doc"},
            "result_summary": {"doc_url": "https://example.com/doc", "summary": "Draft delivered"},
        },
        headers=executor_headers,
    )
    assert deliver_resp.status_code == 200
    delivered_order = deliver_resp.json()
    assert delivered_order["status"] == "reviewing"
    assert delivered_order["review_started_at"] is not None

    approve_resp = client.post(
        f"/api/v1/openclaws/{requester_id}/orders/{order_id}/receive-result",
        json={
            "checklist_result": {"all_passed": True},
            "note": "Looks good",
        },
        headers=requester_headers,
    )
    assert approve_resp.status_code == 200
    approved_order = approve_resp.json()
    assert approved_order["status"] == "approved"
    assert approved_order["approved_at"] is not None

    usage_receipt_resp = client.post(
        f"/api/v1/orders/{order_id}/usage-receipts",
        json={
            "openclaw_id": executor_id,
            "provider": "openai",
            "provider_request_id": "req-auto-assign-001",
            "model": "gpt-4.1-mini",
            "prompt_tokens": 500,
            "completion_tokens": 360,
        },
        headers=executor_headers,
    )
    assert usage_receipt_resp.status_code == 200
    receipt = usage_receipt_resp.json()
    assert receipt["total_tokens"] == 860

    settle_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/orders/{order_id}/settle",
        json={"usage_receipt_id": receipt["id"]},
        headers=executor_headers,
    )
    assert settle_resp.status_code == 200
    settlement = settle_resp.json()
    assert settlement["order_id"] == order_id
    assert settlement["openclaw_id"] == executor_id
    assert settlement["token_used"] == 860



def test_auth_register_persists_onboarding_profile_and_capabilities(client: TestClient) -> None:
    register_auth_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "builder@example.com",
            "password": "secret123",
            "display_name": "Builder Agent",
            "capacity_per_week": 6,
            "service_config": {"provider": "openai", "model": "gpt-5.4"},
            "subscription_status": "subscribed",
            "service_status": "available",
            "profile": {
                "bio": "Builds and executes marketplace tasks",
                "geo_location": "Singapore",
                "timezone_name": "Asia/Singapore",
                "callback_url": "https://example.com/openclaw/callback",
            },
            "capabilities": {
                "gpu_vram": 24,
                "cpu_threads": 12,
                "system_ram": 64,
                "max_concurrency": 3,
                "network_speed": 500,
                "disk_iops": 9000,
                "env_sandbox": "hybrid",
                "internet_access": True,
                "skill_tags": ["research", "delivery"],
                "pre_installed_tools": ["uv", "node"],
                "external_auths": ["github", "notion"],
            },
        },
    )
    assert register_auth_resp.status_code == 200
    auth_payload = register_auth_resp.json()
    openclaw_id = auth_payload["openclaw"]["id"]
    owner_headers = auth_headers(auth_payload["access_token"])

    list_openclaws_resp = client.get("/api/v1/openclaws")
    assert list_openclaws_resp.status_code == 200
    openclaws = list_openclaws_resp.json()
    matching_openclaw = next(item for item in openclaws if item["id"] == openclaw_id)
    assert matching_openclaw["subscription_status"] == "subscribed"
    assert matching_openclaw["service_status"] == "available"

    detail_resp = client.get(f"/api/v1/openclaws/{openclaw_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert_exact_keys(detail, OPENCLAW_DETAIL_KEYS)
    assert detail["profile"] == {
        "bio": "Builds and executes marketplace tasks",
        "geo_location": "Singapore",
        "timezone_name": "Asia/Singapore",
        "callback_url": "https://example.com/openclaw/callback",
    }
    assert detail["capabilities"]["max_concurrency"] == 3
    assert detail["capabilities"]["env_sandbox"] == "hybrid"
    assert detail["capabilities"]["skill_tags"] == ["research", "delivery"]
    assert detail["reputation"] == {
        "total_completed_tasks": 0,
        "average_rating": 0.0,
        "positive_rate": 0.0,
        "reliability_score": 0,
        "latest_feedback": None,
    }

    update_profile_resp = client.post(
        f"/api/v1/openclaws/{openclaw_id}/profile",
        json={
            "capacity_per_week": 9,
            "service_config": {"provider": "anthropic", "model": "claude"},
            "bio": "Updated OpenClaw profile",
            "geo_location": "US",
            "timezone_name": "America/Los_Angeles",
            "callback_url": "https://example.com/openclaw/callback-v2",
        },
        headers=owner_headers,
    )
    assert update_profile_resp.status_code == 200
    updated_profile_detail = update_profile_resp.json()
    assert_exact_keys(updated_profile_detail, OPENCLAW_DETAIL_KEYS)
    assert updated_profile_detail["profile"] == {
        "bio": "Updated OpenClaw profile",
        "geo_location": "US",
        "timezone_name": "America/Los_Angeles",
        "callback_url": "https://example.com/openclaw/callback-v2",
    }

    update_capabilities_resp = client.post(
        f"/api/v1/openclaws/{openclaw_id}/capabilities",
        json={
            "max_concurrency": 7,
            "internet_access": False,
            "skill_tags": ["ops"],
            "pre_installed_tools": ["docker"],
            "external_auths": ["slack"],
        },
        headers=owner_headers,
    )
    assert update_capabilities_resp.status_code == 200
    updated_capability_detail = update_capabilities_resp.json()
    assert_exact_keys(updated_capability_detail, OPENCLAW_DETAIL_KEYS)
    assert updated_capability_detail["capabilities"]["gpu_vram"] == 24
    assert updated_capability_detail["capabilities"]["max_concurrency"] == 7
    assert updated_capability_detail["capabilities"]["internet_access"] is False
    assert updated_capability_detail["capabilities"]["skill_tags"] == ["ops"]
    assert updated_capability_detail["capabilities"]["pre_installed_tools"] == ["docker"]
    assert updated_capability_detail["capabilities"]["external_auths"] == ["slack"]

    unauthorized_profile_resp = client.post(
        f"/api/v1/openclaws/{openclaw_id}/profile",
        json={"bio": "Should fail"},
    )
    assert unauthorized_profile_resp.status_code == 401

    other_auth_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "other@example.com",
            "password": "secret123",
            "display_name": "Other Agent",
        },
    )
    assert other_auth_resp.status_code == 200
    other_headers = auth_headers(other_auth_resp.json()["access_token"])
    forbidden_capability_resp = client.post(
        f"/api/v1/openclaws/{openclaw_id}/capabilities",
        json={"max_concurrency": 11},
        headers=other_headers,
    )
    assert forbidden_capability_resp.status_code == 403

    db_url = (os.getenv("TEST_MARKETPLACE_DB_URL") or os.getenv("MARKETPLACE_DB_URL") or "").strip()
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT email, display_name, subscription_status, service_status
                FROM openclaws
                WHERE id = %s
                """,
                (openclaw_id,),
            )
            identity = cur.fetchone()
            cur.execute(
                """
                SELECT bio, geo_location, timezone_name, callback_url, routing_payload
                FROM openclaw_profiles
                WHERE openclaw_id = %s
                """,
                (openclaw_id,),
            )
            profile = cur.fetchone()
            cur.execute(
                """
                SELECT gpu_vram, cpu_threads, system_ram, max_concurrency, network_speed, disk_iops,
                       env_sandbox, internet_access, skill_tags, pre_installed_tools, external_auths, capability_payload
                FROM openclaw_capabilities
                WHERE openclaw_id = %s
                """,
                (openclaw_id,),
            )
            capabilities = cur.fetchone()

    assert identity == {
        "email": "builder@example.com",
        "display_name": "Builder Agent",
        "subscription_status": "subscribed",
        "service_status": "available",
    }
    assert profile["bio"] == "Updated OpenClaw profile"
    assert profile["geo_location"] == "US"
    assert profile["timezone_name"] == "America/Los_Angeles"
    assert profile["callback_url"] == "https://example.com/openclaw/callback-v2"
    assert profile["routing_payload"]["capacity_per_week"] == 9
    assert profile["routing_payload"]["service_config"] == {
        "provider": "anthropic",
        "model": "claude",
        "callback_url": "https://example.com/openclaw/callback-v2",
    }
    assert capabilities["gpu_vram"] == 24
    assert capabilities["cpu_threads"] == 12
    assert capabilities["system_ram"] == 64
    assert capabilities["max_concurrency"] == 7
    assert capabilities["network_speed"] == 500
    assert capabilities["disk_iops"] == 9000
    assert capabilities["env_sandbox"] == "hybrid"
    assert capabilities["internet_access"] is False
    assert capabilities["skill_tags"] == ["ops"]
    assert capabilities["pre_installed_tools"] == ["docker"]
    assert capabilities["external_auths"] == ["slack"]
    assert capabilities["capability_payload"]["max_concurrency"] == 7
    assert capabilities["capability_payload"]["env_sandbox"] == "hybrid"


def test_trade_flow_heartbeat_recovery_assignment(client: TestClient) -> None:
    requester_id = str(uuid4())
    executor_id = str(uuid4())
    template_id = first_template_id(client)

    _, requester_headers = register_openclaw_actor(client, requester_id, "Requester-A", "available")
    _, executor_headers = register_openclaw_actor(client, executor_id, "Executor-B", "offline")

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "title": "Need content draft",
            "requirement_payload": {"brief": "homepage copy"},
        },
        headers=requester_headers,
    )
    assert create_order_resp.status_code == 200
    pending_order = create_order_resp.json()
    assert pending_order["status"] == "published"
    assert pending_order["executor_openclaw_id"] is None

    heartbeat_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/heartbeat",
        json={"service_status": "available"},
        headers=executor_headers,
    )
    assert heartbeat_resp.status_code == 200
    heartbeat = heartbeat_resp.json()
    assert heartbeat["service_status"] == "busy"
    assert heartbeat["assigned_order"] is not None
    assert heartbeat["assigned_order"]["status"] == "assigned"
    assert heartbeat["assigned_order"]["executor_openclaw_id"] == executor_id



def test_trade_flow_create_dispute(client: TestClient) -> None:
    requester_id = str(uuid4())
    executor_id = str(uuid4())
    template_id = first_template_id(client)

    _, requester_headers = register_openclaw_actor(client, requester_id, "Requester-A", "available")
    _, _executor_headers = register_openclaw_actor(client, executor_id, "Executor-B", "available")

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "title": "Need script fix",
            "requirement_payload": {"repo": "openclaw"},
        },
        headers=requester_headers,
    )
    assert create_order_resp.status_code == 200
    order_id = create_order_resp.json()["id"]

    dispute_resp = client.post(
        f"/api/v1/orders/{order_id}/disputes",
        json={
            "opened_by_openclaw_id": requester_id,
            "reason_code": "quality_not_met",
            "description": "Output did not satisfy acceptance checklist",
        },
        headers=requester_headers,
    )
    assert dispute_resp.status_code == 200
    dispute = dispute_resp.json()
    assert dispute["order_id"] == order_id
    assert dispute["status"] == "open"

    list_orders_resp = client.get("/api/v1/orders?page=0&size=20&sort=id,asc")
    assert list_orders_resp.status_code == 200
    orders = list_orders_resp.json()
    target = next(item for item in orders if item["id"] == order_id)
    assert target["status"] == "disputed"


def test_java_compat_alias_fields_are_accepted(client: TestClient) -> None:
    requester_id = str(uuid4())
    executor_id = str(uuid4())
    template_id = first_template_id(client)

    _, requester_headers = register_openclaw_actor(client, requester_id, "Requester-A", "available")
    _, executor_headers = register_openclaw_actor(client, executor_id, "Executor-B", "available")

    package_resp = client.post(
        "/api/v1/openclaws/capability-packages",
        json={
            "owner_open_claw_id": executor_id,
            "title": "Code Fix Package",
            "summary": "Small automation fix",
            "task_template_id": template_id,
            "sample_deliverables": {"type": "script"},
            "price_min": "1.00",
            "price_max": "5.00",
            "capacity_per_week": 5,
            "status": "active",
        },
        headers=executor_headers,
    )
    assert package_resp.status_code == 200
    package_id = package_resp.json()["id"]

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_open_claw_id": requester_id,
            "task_template_id": template_id,
            "capability_package_id": package_id,
            "title": "Need bugfix",
            "requirement_payload": {"ticket": "BUG-100"},
        },
        headers=requester_headers,
    )
    assert create_order_resp.status_code == 200
    order_id = create_order_resp.json()["id"]

    acknowledge_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/orders/{order_id}/accept",
        headers=executor_headers,
    )
    assert acknowledge_resp.status_code == 200

    deliver_resp = client.post(
        f"/api/v1/orders/{order_id}/deliverables",
        json={
            "delivery_note": "done",
            "deliverable_payload": {"pr": "https://example/pr/1"},
            "submitted_by_open_claw_id": executor_id,
        },
        headers=executor_headers,
    )
    assert deliver_resp.status_code == 200

    notify_ready_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/orders/{order_id}/notify-result-ready",
        json={"result_summary": {"status": "ready"}},
        headers=executor_headers,
    )
    assert notify_ready_resp.status_code == 200

    approve_resp = client.post(
        f"/api/v1/orders/{order_id}/acceptance/approve",
        json={
            "requester_open_claw_id": requester_id,
            "checklist_result": {"passed": True},
            "comment": "ok",
        },
        headers=requester_headers,
    )
    assert approve_resp.status_code == 200

    dispute_resp = client.post(
        f"/api/v1/orders/{order_id}/disputes",
        json={
            "opened_by_open_claw_id": requester_id,
            "reason_code": "quality_not_met",
            "description": "Alias field compatibility check",
        },
        headers=requester_headers,
    )
    assert dispute_resp.status_code == 200


def test_generic_accept_without_preassigned_executor_matches_java(client: TestClient) -> None:
    requester_id = str(uuid4())
    template_id = first_template_id(client)

    _, requester_headers = register_openclaw_actor(client, requester_id, "Requester-A", "available")

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "title": "No executor online",
            "requirement_payload": {"topic": "research"},
        },
        headers=requester_headers,
    )
    assert create_order_resp.status_code == 200
    order = create_order_resp.json()
    assert order["status"] == "published"
    assert order["executor_openclaw_id"] is None

    accept_resp = client.post(f"/api/v1/orders/{order['id']}/accept", headers=requester_headers)
    assert accept_resp.status_code == 409


def test_endpoint_response_fields_alignment_no_legacy(client: TestClient) -> None:
    requester_id = str(uuid4())
    executor_id = str(uuid4())

    register_auth_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@example.com",
            "password": "secret123",
            "display_name": "Owner User",
        },
    )
    assert register_auth_resp.status_code == 200
    auth_payload = register_auth_resp.json()
    assert set(auth_payload.keys()) == {"access_token", "token_type", "openclaw"}
    assert set(auth_payload["openclaw"].keys()) == {
        "id",
        "email",
        "display_name",
        "user_status",
        "created_at",
        "updated_at",
    }

    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": "owner@example.com",
            "password": "secret123",
        },
    )
    assert login_resp.status_code == 200
    login_payload = login_resp.json()
    assert set(login_payload.keys()) == {"access_token", "token_type", "openclaw"}

    profile_1, requester_headers = register_openclaw_actor(client, requester_id, "Requester-A", "available")
    assert_exact_keys(profile_1, OPENCLAW_PROFILE_VIEW_KEYS)
    profile_2, executor_headers = register_openclaw_actor(client, executor_id, "Executor-B", "available")
    assert_exact_keys(profile_2, OPENCLAW_PROFILE_VIEW_KEYS)

    list_openclaws_resp = client.get("/api/v1/openclaws")
    assert list_openclaws_resp.status_code == 200
    openclaws = list_openclaws_resp.json()
    assert len(openclaws) >= 2
    assert_exact_keys(openclaws[0], OPENCLAW_VIEW_KEYS)

    search_resp = client.get("/api/v1/openclaws/search?keyword=executor&page=0&size=20")
    assert search_resp.status_code == 200
    search_items = search_resp.json()
    assert len(search_items) >= 1
    assert_exact_keys(search_items[0], OPENCLAW_VIEW_KEYS)

    templates_resp = client.get("/api/v1/task-templates?page=0&size=20&sort=id,asc")
    assert templates_resp.status_code == 200
    templates = templates_resp.json()
    assert len(templates) >= 1
    assert_exact_keys(templates[0], TASK_TEMPLATE_VIEW_KEYS)
    template_id = templates[0]["id"]

    create_pkg_resp = client.post(
        "/api/v1/openclaws/capability-packages",
        json={
            "owner_openclaw_id": executor_id,
            "title": "Executor Package",
            "summary": "General fulfillment package",
            "task_template_id": template_id,
            "sample_deliverables": {"kind": "doc"},
            "price_min": "1.00",
            "price_max": "10.00",
            "capacity_per_week": 8,
            "status": "active",
        },
        headers=executor_headers,
    )
    assert create_pkg_resp.status_code == 200
    pkg_payload = create_pkg_resp.json()
    assert_exact_keys(pkg_payload, CAPABILITY_PACKAGE_VIEW_KEYS)

    market_pkg_resp = client.get("/api/v1/marketplace/capability-packages?page=0&size=20&sort=id,asc")
    assert market_pkg_resp.status_code == 200
    market_pkgs = market_pkg_resp.json()
    assert len(market_pkgs) >= 1
    assert_exact_keys(market_pkgs[0], CAPABILITY_PACKAGE_VIEW_KEYS)

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "title": "Initial Order",
            "requirement_payload": {"scope": "basic"},
        },
        headers=requester_headers,
    )
    assert create_order_resp.status_code == 200
    order_payload = create_order_resp.json()
    assert_exact_keys(order_payload, ORDER_VIEW_KEYS)
    order_id = order_payload["id"]

    list_orders_resp = client.get("/api/v1/orders?page=0&size=20&sort=id,asc")
    assert list_orders_resp.status_code == 200
    orders = list_orders_resp.json()
    assert len(orders) >= 1
    assert_exact_keys(orders[0], ORDER_VIEW_KEYS)

    deliver_resp = client.post(
        f"/api/v1/orders/{order_id}/deliverables",
        json={
            "delivery_note": "Delivered",
            "deliverable_payload": {"url": "https://example.com/result"},
            "submitted_by_openclaw_id": executor_id,
        },
        headers=executor_headers,
    )
    assert deliver_resp.status_code == 409

    acknowledge_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/orders/{order_id}/accept",
        headers=executor_headers,
    )
    assert acknowledge_resp.status_code == 200

    deliver_resp = client.post(
        f"/api/v1/orders/{order_id}/deliverables",
        json={
            "delivery_note": "Delivered",
            "deliverable_payload": {"url": "https://example.com/result"},
            "submitted_by_openclaw_id": executor_id,
        },
        headers=executor_headers,
    )
    assert deliver_resp.status_code == 200
    deliverable_payload = deliver_resp.json()
    assert_exact_keys(deliverable_payload, DELIVERABLE_VIEW_KEYS)

    notify_ready_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/orders/{order_id}/notify-result-ready",
        json={"result_summary": {"status": "ready"}},
        headers=executor_headers,
    )
    assert notify_ready_resp.status_code == 200
    assert_exact_keys(notify_ready_resp.json(), ORDER_VIEW_KEYS)

    receive_result_resp = client.post(
        f"/api/v1/openclaws/{requester_id}/orders/{order_id}/receive-result",
        json={"checklist_result": {"ok": True}, "note": "received"},
        headers=requester_headers,
    )
    assert receive_result_resp.status_code == 200
    assert_exact_keys(receive_result_resp.json(), ORDER_VIEW_KEYS)

    usage_receipt_resp = client.post(
        f"/api/v1/orders/{order_id}/usage-receipts",
        json={
            "openclaw_id": executor_id,
            "provider": "openai",
            "provider_request_id": "req-contract-001",
            "model": "gpt-4.1-mini",
            "prompt_tokens": 120,
            "completion_tokens": 100,
        },
        headers=executor_headers,
    )
    assert usage_receipt_resp.status_code == 200
    usage_receipt_payload = usage_receipt_resp.json()
    assert_exact_keys(usage_receipt_payload, TOKEN_USAGE_RECEIPT_VIEW_KEYS)

    settle_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/orders/{order_id}/settle",
        json={"usage_receipt_id": usage_receipt_payload["id"]},
        headers=executor_headers,
    )
    assert settle_resp.status_code == 200
    assert_exact_keys(settle_resp.json(), SETTLEMENT_VIEW_KEYS)

    publish_order_resp = client.post(
        f"/api/v1/openclaws/{requester_id}/orders",
        json={
            "task_template_id": template_id,
            "title": "Published by requester",
            "requirement_payload": {"topic": "content"},
        },
        headers=requester_headers,
    )
    assert publish_order_resp.status_code == 200
    publish_order = publish_order_resp.json()
    assert_exact_keys(publish_order, ORDER_VIEW_KEYS)

    openclaw_accept_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/orders/{publish_order['id']}/accept",
        headers=executor_headers,
    )
    assert openclaw_accept_resp.status_code == 409 or openclaw_accept_resp.status_code == 200
    if openclaw_accept_resp.status_code == 200:
        assert_exact_keys(openclaw_accept_resp.json(), ORDER_VIEW_KEYS)

    heartbeat_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/heartbeat",
        json={"service_status": "available"},
        headers=executor_headers,
    )
    assert heartbeat_resp.status_code == 200
    heartbeat_payload = heartbeat_resp.json()
    assert_exact_keys(heartbeat_payload, HEARTBEAT_VIEW_KEYS)
    if heartbeat_payload["assigned_order"] is not None:
        assert_exact_keys(heartbeat_payload["assigned_order"], ORDER_VIEW_KEYS)

    notifications_resp = client.get(f"/api/v1/openclaws/{executor_id}/notifications", headers=executor_headers)
    assert notifications_resp.status_code == 200
    notifications = notifications_resp.json()
    assert len(notifications) >= 1
    assert_exact_keys(notifications[0], NOTIFICATION_VIEW_KEYS)

    ack_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/notifications/{notifications[0]['id']}/ack",
        headers=executor_headers,
    )
    assert ack_resp.status_code == 200
    assert_exact_keys(ack_resp.json(), NOTIFICATION_VIEW_KEYS)

    update_subscription_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/subscription",
        json={"subscription_status": "subscribed"},
        headers=executor_headers,
    )
    assert update_subscription_resp.status_code == 200
    assert_exact_keys(update_subscription_resp.json(), OPENCLAW_VIEW_KEYS)

    update_service_status_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/service-status",
        json={"service_status": "available", "active_order_id": None},
        headers=executor_headers,
    )
    assert update_service_status_resp.status_code == 200
    assert_exact_keys(update_service_status_resp.json(), OPENCLAW_VIEW_KEYS)

    created_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "title": "Need assign endpoint",
            "requirement_payload": {"need": "executor"},
        },
        headers=requester_headers,
    )
    assert created_order_resp.status_code == 200
    created_order = created_order_resp.json()
    assert_exact_keys(created_order, ORDER_VIEW_KEYS)

    assign_resp = client.post(
        f"/api/v1/orders/{created_order['id']}/assign",
        json={"executor_openclaw_id": executor_id},
        headers=requester_headers,
    )
    if assign_resp.status_code == 200:
        assert_exact_keys(assign_resp.json(), ORDER_VIEW_KEYS)

    generic_accept_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "title": "Need generic accept",
            "requirement_payload": {"topic": "analysis"},
        },
        headers=requester_headers,
    )
    assert generic_accept_order_resp.status_code == 200
    generic_accept_order = generic_accept_order_resp.json()
    assert_exact_keys(generic_accept_order, ORDER_VIEW_KEYS)

    generic_accept_resp = client.post(
        f"/api/v1/orders/{generic_accept_order['id']}/accept",
        headers=executor_headers,
    )
    assert generic_accept_resp.status_code in {200, 409}
    if generic_accept_resp.status_code == 200:
        assert_exact_keys(generic_accept_resp.json(), ORDER_VIEW_KEYS)

    complete_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "title": "Need complete callback",
            "requirement_payload": {"topic": "workflow"},
        },
        headers=requester_headers,
    )
    assert complete_order_resp.status_code == 200
    complete_order = complete_order_resp.json()
    assert_exact_keys(complete_order, ORDER_VIEW_KEYS)

    if complete_order["executor_openclaw_id"] == executor_id and complete_order["status"] in {"assigned", "acknowledged"}:
        accept_complete_order_resp = client.post(
            f"/api/v1/openclaws/{executor_id}/orders/{complete_order['id']}/accept",
            headers=executor_headers,
        )
        assert accept_complete_order_resp.status_code == 200

        complete_callback_resp = client.post(
            f"/api/v1/openclaws/{executor_id}/orders/{complete_order['id']}/complete",
            json={
                "delivery_note": "final",
                "deliverable_payload": {"bundle": "zip"},
                "result_summary": {"ok": True},
            },
            headers=executor_headers,
        )
        assert complete_callback_resp.status_code == 200
        assert_exact_keys(complete_callback_resp.json(), ORDER_VIEW_KEYS)

    dispute_resp = client.post(
        f"/api/v1/orders/{created_order['id']}/disputes",
        json={
            "opened_by_openclaw_id": requester_id,
            "reason_code": "quality_not_met",
            "description": "contract test",
        },
        headers=requester_headers,
    )
    assert dispute_resp.status_code == 200
    assert_exact_keys(dispute_resp.json(), DISPUTE_VIEW_KEYS)


def test_order_cancel_releases_executor_and_notifies_counterparty(client: TestClient) -> None:
    requester_id = str(uuid4())
    executor_id = str(uuid4())
    template_id = first_template_id(client)

    _, requester_headers = register_openclaw_actor(client, requester_id, "Requester-Cancel", "available")
    _, executor_headers = register_openclaw_actor(client, executor_id, "Executor-Cancel", "available")

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "title": "Cancel me",
            "requirement_payload": {"kind": "draft"},
        },
        headers=requester_headers,
    )
    assert create_order_resp.status_code == 200
    order = create_order_resp.json()
    assert order["status"] == "assigned"
    assert order["executor_openclaw_id"] == executor_id

    cancel_resp = client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        json={"requester_openclaw_id": requester_id, "reason": "scope_changed"},
        headers=requester_headers,
    )
    assert cancel_resp.status_code == 200
    cancelled = cancel_resp.json()
    assert_exact_keys(cancelled, ORDER_VIEW_KEYS)
    assert cancelled["status"] == "cancelled"
    assert cancelled["cancelled_at"] is not None

    executor_detail_resp = client.get(f"/api/v1/openclaws/{executor_id}")
    assert executor_detail_resp.status_code == 200
    executor_runtime = executor_detail_resp.json()["runtime"]
    assert executor_runtime["service_status"] == "available"

    notifications_resp = client.get(
        f"/api/v1/openclaws/{executor_id}/notifications",
        headers=executor_headers,
    )
    assert notifications_resp.status_code == 200
    assert any(item["notification_type"] == "task_cancelled" for item in notifications_resp.json())


def test_assignment_expiry_reassigns_order_and_releases_previous_executor(client: TestClient) -> None:
    requester_id = str(uuid4())
    executor_one_id = str(uuid4())
    executor_two_id = str(uuid4())
    template_id = first_template_id(client)

    _, requester_headers = register_openclaw_actor(client, requester_id, "Requester-Expire", "available")
    _, executor_one_headers = register_openclaw_actor(client, executor_one_id, "Executor-One", "available")
    _, executor_two_headers = register_openclaw_actor(client, executor_two_id, "Executor-Two", "available")

    package_resp = client.post(
        "/api/v1/openclaws/capability-packages",
        json={
            "owner_openclaw_id": executor_one_id,
            "title": "Pinned executor package",
            "summary": "Use executor one first",
            "task_template_id": template_id,
            "sample_deliverables": {"type": "report"},
            "price_min": "5.00",
            "price_max": "8.00",
            "capacity_per_week": 3,
            "status": "active",
        },
        headers=executor_one_headers,
    )
    assert package_resp.status_code == 200
    package_id = package_resp.json()["id"]

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "capability_package_id": package_id,
            "title": "Expire assignment",
            "requirement_payload": {"priority": "normal"},
        },
        headers=requester_headers,
    )
    assert create_order_resp.status_code == 200
    order = create_order_resp.json()
    assert order["status"] == "assigned"
    assert order["executor_openclaw_id"] == executor_one_id
    assert order["assignment_attempt_count"] == 1

    expire_resp = client.post(f"/api/v1/orders/{order['id']}/expire-assignment")
    assert expire_resp.status_code == 200
    reassigned = expire_resp.json()
    assert_exact_keys(reassigned, ORDER_VIEW_KEYS)
    assert reassigned["status"] == "assigned"
    assert reassigned["executor_openclaw_id"] == executor_two_id
    assert reassigned["assignment_attempt_count"] == 2

    executor_one_detail_resp = client.get(f"/api/v1/openclaws/{executor_one_id}")
    assert executor_one_detail_resp.status_code == 200
    assert executor_one_detail_resp.json()["runtime"]["service_status"] == "available"

    executor_two_detail_resp = client.get(f"/api/v1/openclaws/{executor_two_id}")
    assert executor_two_detail_resp.status_code == 200
    assert executor_two_detail_resp.json()["runtime"]["service_status"] == "busy"

    previous_executor_notifications = client.get(
        f"/api/v1/openclaws/{executor_one_id}/notifications",
        headers=executor_one_headers,
    )
    assert previous_executor_notifications.status_code == 200
    assert any(item["notification_type"] == "assignment_expired" for item in previous_executor_notifications.json())

    next_executor_notifications = client.get(
        f"/api/v1/openclaws/{executor_two_id}/notifications",
        headers=executor_two_headers,
    )
    assert next_executor_notifications.status_code == 200
    assert any(item["notification_type"] == "task_assigned" for item in next_executor_notifications.json())


def test_review_expiry_marks_order_expired_and_releases_executor(client: TestClient) -> None:
    requester_id = str(uuid4())
    executor_id = str(uuid4())
    template_id = first_template_id(client)

    _, requester_headers = register_openclaw_actor(client, requester_id, "Requester-Review", "available")
    _, executor_headers = register_openclaw_actor(client, executor_id, "Executor-Review", "available")

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "title": "Expire review",
            "requirement_payload": {"acceptance": "manual"},
        },
        headers=requester_headers,
    )
    assert create_order_resp.status_code == 200
    order_id = create_order_resp.json()["id"]

    accept_resp = client.post(f"/api/v1/orders/{order_id}/accept", headers=executor_headers)
    assert accept_resp.status_code == 200

    complete_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/orders/{order_id}/complete",
        json={
            "delivery_note": "ready",
            "deliverable_payload": {"artifact": "bundle"},
            "result_summary": {"ok": True},
        },
        headers=executor_headers,
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "reviewing"

    expire_resp = client.post(f"/api/v1/orders/{order_id}/expire-review")
    assert expire_resp.status_code == 200
    expired = expire_resp.json()
    assert_exact_keys(expired, ORDER_VIEW_KEYS)
    assert expired["status"] == "expired"
    assert expired["expired_at"] is not None

    executor_detail_resp = client.get(f"/api/v1/openclaws/{executor_id}")
    assert executor_detail_resp.status_code == 200
    assert executor_detail_resp.json()["runtime"]["service_status"] == "available"

    requester_notifications = client.get(
        f"/api/v1/openclaws/{requester_id}/notifications",
        headers=requester_headers,
    )
    assert requester_notifications.status_code == 200
    assert any(item["notification_type"] == "review_expired" for item in requester_notifications.json())

    executor_notifications = client.get(
        f"/api/v1/openclaws/{executor_id}/notifications",
        headers=executor_headers,
    )
    assert executor_notifications.status_code == 200
    assert any(item["notification_type"] == "review_expired" for item in executor_notifications.json())


def test_executor_can_fail_order_and_failure_reason_is_exposed(client: TestClient) -> None:
    requester_id = str(uuid4())
    executor_id = str(uuid4())
    template_id = first_template_id(client)

    _, requester_headers = register_openclaw_actor(client, requester_id, "Requester-Failure", "available")
    _, executor_headers = register_openclaw_actor(client, executor_id, "Executor-Failure", "available")

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "title": "Fail order",
            "requirement_payload": {"kind": "runtime"},
        },
        headers=requester_headers,
    )
    assert create_order_resp.status_code == 200
    order = create_order_resp.json()

    fail_resp = client.post(
        f"/api/v1/orders/{order['id']}/fail",
        json={
            "executor_openclaw_id": executor_id,
            "failure_code": "runtime_unreachable",
            "failure_note": "worker lost network",
        },
        headers=executor_headers,
    )
    assert fail_resp.status_code == 200
    failed = fail_resp.json()
    assert_exact_keys(failed, ORDER_VIEW_KEYS)
    assert failed["status"] == "failed"
    assert failed["failed_at"] is not None
    assert failed["latest_failure_code"] == "runtime_unreachable"
    assert failed["latest_failure_note"] == "worker lost network"

    executor_detail_resp = client.get(f"/api/v1/openclaws/{executor_id}")
    assert executor_detail_resp.status_code == 200
    assert executor_detail_resp.json()["runtime"]["service_status"] == "available"

    requester_notifications = client.get(
        f"/api/v1/openclaws/{requester_id}/notifications",
        headers=requester_headers,
    )
    assert requester_notifications.status_code == 200
    assert any(item["notification_type"] == "order_failed" for item in requester_notifications.json())


def test_deadline_worker_processes_due_assignment_expiry(client: TestClient) -> None:
    requester_id = str(uuid4())
    executor_one_id = str(uuid4())
    executor_two_id = str(uuid4())
    template_id = first_template_id(client)

    _, requester_headers = register_openclaw_actor(client, requester_id, "Requester-Worker-Assign", "available")
    _, executor_one_headers = register_openclaw_actor(client, executor_one_id, "Executor-Worker-One", "available")
    register_openclaw_actor(client, executor_two_id, "Executor-Worker-Two", "available")

    package_resp = client.post(
        "/api/v1/openclaws/capability-packages",
        json={
            "owner_openclaw_id": executor_one_id,
            "title": "Worker assignment package",
            "summary": "Expire through scanner",
            "task_template_id": template_id,
            "sample_deliverables": {"type": "report"},
            "price_min": "5.00",
            "price_max": "8.00",
            "capacity_per_week": 3,
            "status": "active",
        },
        headers=executor_one_headers,
    )
    assert package_resp.status_code == 200

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "capability_package_id": package_resp.json()["id"],
            "title": "Worker expires assignment",
            "requirement_payload": {"priority": "normal"},
        },
        headers=requester_headers,
    )
    assert create_order_resp.status_code == 200
    order = create_order_resp.json()
    expire_order_deadline_in_service(order["id"], assignment=True)

    service = main_module.service
    assert service is not None
    summary = service.process_due_order_deadlines(now="2026-03-30T00:01:00Z")
    assert summary["assignment_processed"] == 1
    assert summary["review_processed"] == 0

    refreshed = service.orders[UUID(order["id"])]
    assert refreshed.status == "assigned"
    assert str(refreshed.executor_openclaw_id) == executor_two_id


def test_deadline_worker_processes_due_review_expiry(client: TestClient) -> None:
    requester_id = str(uuid4())
    executor_id = str(uuid4())
    template_id = first_template_id(client)

    _, requester_headers = register_openclaw_actor(client, requester_id, "Requester-Worker-Review", "available")
    _, executor_headers = register_openclaw_actor(client, executor_id, "Executor-Worker-Review", "available")

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "title": "Worker expires review",
            "requirement_payload": {"acceptance": "manual"},
        },
        headers=requester_headers,
    )
    assert create_order_resp.status_code == 200
    order_id = create_order_resp.json()["id"]

    accept_resp = client.post(f"/api/v1/orders/{order_id}/accept", headers=executor_headers)
    assert accept_resp.status_code == 200

    complete_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/orders/{order_id}/complete",
        json={
            "delivery_note": "ready",
            "deliverable_payload": {"artifact": "bundle"},
            "result_summary": {"ok": True},
        },
        headers=executor_headers,
    )
    assert complete_resp.status_code == 200
    expire_order_deadline_in_service(order_id, review=True)

    service = main_module.service
    assert service is not None
    summary = service.process_due_order_deadlines(now="2026-03-30T00:01:00Z")
    assert summary["assignment_processed"] == 0
    assert summary["review_processed"] == 1

    refreshed = service.orders[UUID(order_id)]
    assert refreshed.status == "expired"
    assert refreshed.expired_at is not None


def test_failed_notification_is_scheduled_for_retry_and_visible_in_operations(client: TestClient) -> None:
    requester_id = str(uuid4())
    executor_id = str(uuid4())
    template_id = first_template_id(client)

    _, requester_headers = register_openclaw_actor(client, requester_id, "Requester-Notify-Retry", "available")
    _, executor_headers = register_openclaw_actor(client, executor_id, "Executor-Notify-Retry", "available")

    update_profile_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/profile",
        json={"callback_url": "http://127.0.0.1:1/notify"},
        headers=executor_headers,
    )
    assert update_profile_resp.status_code == 200

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "title": "Retry notification",
            "requirement_payload": {"need": "callback"},
        },
        headers=requester_headers,
    )
    assert create_order_resp.status_code == 200

    notifications_resp = client.get(
        f"/api/v1/openclaws/{executor_id}/notifications",
        headers=executor_headers,
    )
    assert notifications_resp.status_code == 200
    notifications = notifications_resp.json()
    retry_notification = next(item for item in notifications if item["notification_type"] == "task_assigned")
    assert retry_notification["status"] == "retry_scheduled"
    assert retry_notification["retry_count"] == 1
    assert retry_notification["last_error"]
    assert retry_notification["next_retry_at"] is not None

    operations_resp = client.get("/api/v1/notifications/operations?status=retry_scheduled")
    assert operations_resp.status_code == 200
    operation_notifications = operations_resp.json()
    assert any(item["id"] == retry_notification["id"] for item in operation_notifications)
    assert_exact_keys(operation_notifications[0], NOTIFICATION_VIEW_KEYS)


def test_notification_retry_worker_promotes_to_dead_letter_after_retry_limit(client: TestClient) -> None:
    requester_id = str(uuid4())
    executor_id = str(uuid4())
    template_id = first_template_id(client)

    _, requester_headers = register_openclaw_actor(client, requester_id, "Requester-Notify-Dead", "available")
    _, executor_headers = register_openclaw_actor(client, executor_id, "Executor-Notify-Dead", "available")

    update_profile_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/profile",
        json={"callback_url": "http://127.0.0.1:1/notify"},
        headers=executor_headers,
    )
    assert update_profile_resp.status_code == 200

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "title": "Dead letter notification",
            "requirement_payload": {"need": "callback"},
        },
        headers=requester_headers,
    )
    assert create_order_resp.status_code == 200

    service = main_module.service
    assert service is not None
    service._notification_max_retries = 2

    notifications_resp = client.get(
        f"/api/v1/openclaws/{executor_id}/notifications",
        headers=executor_headers,
    )
    assert notifications_resp.status_code == 200
    notifications = notifications_resp.json()
    retry_notification = next(item for item in notifications if item["notification_type"] == "task_assigned")
    update_notification_retry_due_in_service(retry_notification["id"], next_retry_at="2026-03-30T00:00:00Z")

    retry_resp = client.post("/api/v1/notifications/process-retries")
    assert retry_resp.status_code == 200
    summary = retry_resp.json()
    assert summary["attempted"] == 1
    assert summary["dead_letter"] == 1

    refreshed_notifications_resp = client.get(
        f"/api/v1/openclaws/{executor_id}/notifications",
        headers=executor_headers,
    )
    assert refreshed_notifications_resp.status_code == 200
    refreshed = next(item for item in refreshed_notifications_resp.json() if item["id"] == retry_notification["id"])
    assert refreshed["status"] == "dead_letter"
    assert refreshed["retry_count"] == 2
    assert refreshed["next_retry_at"] is None


def test_resolve_dispute_with_requester_refund_releases_executor(client: TestClient) -> None:
    requester_id = str(uuid4())
    executor_id = str(uuid4())
    template_id = first_template_id(client)

    _, requester_headers = register_openclaw_actor(client, requester_id, "Requester-Dispute-Refund", "available")
    _, executor_headers = register_openclaw_actor(client, executor_id, "Executor-Dispute-Refund", "available")

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "title": "Refund dispute",
            "requirement_payload": {"topic": "refund"},
        },
        headers=requester_headers,
    )
    assert create_order_resp.status_code == 200
    order_id = create_order_resp.json()["id"]

    accept_resp = client.post(f"/api/v1/orders/{order_id}/accept", headers=executor_headers)
    assert accept_resp.status_code == 200

    dispute_resp = client.post(
        f"/api/v1/orders/{order_id}/disputes",
        json={
            "opened_by_openclaw_id": requester_id,
            "reason_code": "quality_not_met",
            "description": "refund requested",
        },
        headers=requester_headers,
    )
    assert dispute_resp.status_code == 200
    dispute = dispute_resp.json()
    assert dispute["status"] == "open"

    resolve_resp = client.post(
        f"/api/v1/orders/{order_id}/disputes/{dispute['id']}/resolve",
        json={"decision": "refund_requester", "operator_note": "refund approved"},
    )
    assert resolve_resp.status_code == 200
    resolved = resolve_resp.json()
    assert_exact_keys(resolved, DISPUTE_VIEW_KEYS)
    assert resolved["status"] == "resolved"
    assert resolved["resolution_payload"]["decision"] == "refund_requester"

    list_orders_resp = client.get("/api/v1/orders?page=0&size=50&sort=id,asc")
    assert list_orders_resp.status_code == 200
    order = next(item for item in list_orders_resp.json() if item["id"] == order_id)
    assert order["status"] == "cancelled"
    assert order["cancelled_at"] is not None

    executor_detail_resp = client.get(f"/api/v1/openclaws/{executor_id}")
    assert executor_detail_resp.status_code == 200
    assert executor_detail_resp.json()["runtime"]["service_status"] == "available"


def test_resolve_dispute_with_executor_release_settles_order(client: TestClient) -> None:
    requester_id = str(uuid4())
    executor_id = str(uuid4())
    template_id = first_template_id(client)

    _, requester_headers = register_openclaw_actor(client, requester_id, "Requester-Dispute-Release", "available")
    _, executor_headers = register_openclaw_actor(client, executor_id, "Executor-Dispute-Release", "available")

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "title": "Release dispute",
            "requirement_payload": {"topic": "release"},
        },
        headers=requester_headers,
    )
    assert create_order_resp.status_code == 200
    order_id = create_order_resp.json()["id"]

    accept_resp = client.post(f"/api/v1/orders/{order_id}/accept", headers=executor_headers)
    assert accept_resp.status_code == 200

    complete_resp = client.post(
        f"/api/v1/openclaws/{executor_id}/orders/{order_id}/complete",
        json={
            "delivery_note": "done",
            "deliverable_payload": {"artifact": "bundle"},
            "result_summary": {"ok": True},
        },
        headers=executor_headers,
    )
    assert complete_resp.status_code == 200

    dispute_resp = client.post(
        f"/api/v1/orders/{order_id}/disputes",
        json={
            "opened_by_openclaw_id": requester_id,
            "reason_code": "review_conflict",
            "description": "needs operator decision",
        },
        headers=requester_headers,
    )
    assert dispute_resp.status_code == 200
    dispute = dispute_resp.json()

    resolve_resp = client.post(
        f"/api/v1/orders/{order_id}/disputes/{dispute['id']}/resolve",
        json={"decision": "release_executor", "operator_note": "deliverable accepted", "token_used": 0},
    )
    assert resolve_resp.status_code == 200
    resolved = resolve_resp.json()
    assert resolved["status"] == "resolved"
    assert resolved["resolution_payload"]["decision"] == "release_executor"

    list_orders_resp = client.get("/api/v1/orders?page=0&size=50&sort=id,asc")
    assert list_orders_resp.status_code == 200
    order = next(item for item in list_orders_resp.json() if item["id"] == order_id)
    assert order["status"] == "settled"
    assert order["settled_at"] is not None

    executor_detail_resp = client.get(f"/api/v1/openclaws/{executor_id}")
    assert executor_detail_resp.status_code == 200
    assert executor_detail_resp.json()["runtime"]["service_status"] == "available"
