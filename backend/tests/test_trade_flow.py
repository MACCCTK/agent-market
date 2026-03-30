from __future__ import annotations

import os

import pytest
import psycopg
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
    "base_price",
    "sla_hours",
    "status",
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
    "sla_hours",
    "requirement_payload",
    "accepted_at",
    "delivered_at",
    "completed_at",
    "cancelled_at",
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


def assert_exact_keys(payload: dict, expected_keys: set[str]) -> None:
    assert set(payload.keys()) == expected_keys


@pytest.fixture()
def client() -> TestClient:
    db_url = (os.getenv("TEST_MARKETPLACE_DB_URL") or os.getenv("MARKETPLACE_DB_URL") or "").strip()
    if not db_url:
        pytest.skip("PostgreSQL URL is required: set TEST_MARKETPLACE_DB_URL or MARKETPLACE_DB_URL")

    MarketplaceService(db_url=db_url)

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE openclaw_usage_receipts, openclaw_notifications, openclaw_task_events, openclaw_task_orders, openclaw_profiles, openclaws"
            )
        conn.commit()

    main_module.service = MarketplaceService(db_url=db_url)
    return TestClient(main_module.app)


def register_openclaw(client: TestClient, openclaw_id: int, name: str, service_status: str = "available") -> dict:
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


def test_trade_flow_auto_assign_deliver_approve_settle(client: TestClient) -> None:
    register_openclaw(client, 1, "Requester-A", "available")
    register_openclaw(client, 2, "Executor-B", "available")

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": 1,
            "task_template_id": 1,
            "title": "Need research brief",
            "requirement_payload": {"topic": "agent marketplace"},
        },
    )
    assert create_order_resp.status_code == 200
    order = create_order_resp.json()
    assert order["status"] == "accepted"
    assert order["executor_openclaw_id"] == 2

    order_id = order["id"]

    deliver_resp = client.post(
        f"/api/v1/orders/{order_id}/deliverables",
        json={
            "delivery_note": "Draft delivered",
            "deliverable_payload": {"doc_url": "https://example.com/doc"},
            "submitted_by_openclaw_id": 2,
        },
    )
    assert deliver_resp.status_code == 200
    deliverable = deliver_resp.json()
    assert deliverable["version_no"] == 1

    approve_resp = client.post(
        f"/api/v1/orders/{order_id}/acceptance/approve",
        json={
            "requester_openclaw_id": 1,
            "checklist_result": {"all_passed": True},
            "comment": "Looks good",
        },
    )
    assert approve_resp.status_code == 200
    approved_order = approve_resp.json()
    assert approved_order["status"] == "approved"

    usage_receipt_resp = client.post(
        f"/api/v1/orders/{order_id}/usage-receipts",
        json={
            "openclaw_id": 2,
            "provider": "openai",
            "provider_request_id": "req-auto-assign-001",
            "model": "gpt-4.1-mini",
            "prompt_tokens": 500,
            "completion_tokens": 360,
        },
    )
    assert usage_receipt_resp.status_code == 200
    receipt = usage_receipt_resp.json()
    assert receipt["total_tokens"] == 860

    settle_resp = client.post(
        f"/api/v1/openclaws/2/orders/{order_id}/settle",
        json={"usage_receipt_id": receipt["id"]},
    )
    assert settle_resp.status_code == 200
    settlement = settle_resp.json()
    assert settlement["order_id"] == order_id
    assert settlement["openclaw_id"] == 2
    assert settlement["token_used"] == 860



def test_trade_flow_heartbeat_recovery_assignment(client: TestClient) -> None:
    register_openclaw(client, 1, "Requester-A", "available")
    register_openclaw(client, 2, "Executor-B", "offline")

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": 1,
            "task_template_id": 2,
            "title": "Need content draft",
            "requirement_payload": {"brief": "homepage copy"},
        },
    )
    assert create_order_resp.status_code == 200
    pending_order = create_order_resp.json()
    assert pending_order["status"] == "created"
    assert pending_order["executor_openclaw_id"] is None

    heartbeat_resp = client.post(
        "/api/v1/openclaws/2/heartbeat",
        json={"service_status": "available"},
    )
    assert heartbeat_resp.status_code == 200
    heartbeat = heartbeat_resp.json()
    assert heartbeat["service_status"] == "busy"
    assert heartbeat["assigned_order"] is not None
    assert heartbeat["assigned_order"]["status"] == "accepted"
    assert heartbeat["assigned_order"]["executor_openclaw_id"] == 2



def test_trade_flow_create_dispute(client: TestClient) -> None:
    register_openclaw(client, 1, "Requester-A", "available")
    register_openclaw(client, 2, "Executor-B", "available")

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": 1,
            "task_template_id": 3,
            "title": "Need script fix",
            "requirement_payload": {"repo": "openclaw"},
        },
    )
    assert create_order_resp.status_code == 200
    order_id = create_order_resp.json()["id"]

    dispute_resp = client.post(
        f"/api/v1/orders/{order_id}/disputes",
        json={
            "opened_by_openclaw_id": 1,
            "reason_code": "quality_not_met",
            "description": "Output did not satisfy acceptance checklist",
        },
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
    register_openclaw(client, 1, "Requester-A", "available")
    register_openclaw(client, 2, "Executor-B", "available")

    package_resp = client.post(
        "/api/v1/openclaws/capability-packages",
        json={
            "owner_open_claw_id": 2,
            "title": "Code Fix Package",
            "summary": "Small automation fix",
            "task_template_id": 3,
            "sample_deliverables": {"type": "script"},
            "price_min": "1.00",
            "price_max": "5.00",
            "capacity_per_week": 5,
            "status": "active",
        },
    )
    assert package_resp.status_code == 200
    package_id = package_resp.json()["id"]

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_open_claw_id": 1,
            "task_template_id": 3,
            "capability_package_id": package_id,
            "title": "Need bugfix",
            "requirement_payload": {"ticket": "BUG-100"},
        },
    )
    assert create_order_resp.status_code == 200
    order_id = create_order_resp.json()["id"]

    deliver_resp = client.post(
        f"/api/v1/orders/{order_id}/deliverables",
        json={
            "delivery_note": "done",
            "deliverable_payload": {"pr": "https://example/pr/1"},
            "submitted_by_open_claw_id": 2,
        },
    )
    assert deliver_resp.status_code == 200

    approve_resp = client.post(
        f"/api/v1/orders/{order_id}/acceptance/approve",
        json={
            "requester_open_claw_id": 1,
            "checklist_result": {"passed": True},
            "comment": "ok",
        },
    )
    assert approve_resp.status_code == 200

    dispute_resp = client.post(
        f"/api/v1/orders/{order_id}/disputes",
        json={
            "opened_by_open_claw_id": 1,
            "reason_code": "quality_not_met",
            "description": "Alias field compatibility check",
        },
    )
    assert dispute_resp.status_code == 200


def test_generic_accept_without_preassigned_executor_matches_java(client: TestClient) -> None:
    register_openclaw(client, 1, "Requester-A", "available")

    create_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": 1,
            "task_template_id": 1,
            "title": "No executor online",
            "requirement_payload": {"topic": "research"},
        },
    )
    assert create_order_resp.status_code == 200
    order = create_order_resp.json()
    assert order["status"] == "created"
    assert order["executor_openclaw_id"] is None

    accept_resp = client.post(f"/api/v1/orders/{order['id']}/accept")
    assert accept_resp.status_code == 200
    accepted = accept_resp.json()
    assert accepted["status"] == "accepted"
    assert accepted["executor_openclaw_id"] is None


def test_endpoint_response_fields_alignment_no_legacy(client: TestClient) -> None:
    register_auth_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@example.com",
            "password": "secret123",
            "display_name": "Owner User",
            "roles": ["openclaw"],
            "client_type": "openclaw",
        },
    )
    assert register_auth_resp.status_code == 200
    auth_payload = register_auth_resp.json()
    assert set(auth_payload.keys()) == {"access_token", "token_type", "user"}
    assert set(auth_payload["user"].keys()) == {
        "id",
        "email",
        "display_name",
        "status",
        "roles",
        "created_at",
        "updated_at",
    }

    login_resp = client.post(
        "/api/v1/auth/login",
        json={
            "email": "owner@example.com",
            "password": "secret123",
            "as_role": "openclaw",
            "client_type": "openclaw",
        },
    )
    assert login_resp.status_code == 200
    login_payload = login_resp.json()
    assert set(login_payload.keys()) == {"access_token", "token_type", "user"}

    profile_1 = register_openclaw(client, 1, "Requester-A", "available")
    assert_exact_keys(profile_1, OPENCLAW_PROFILE_VIEW_KEYS)
    profile_2 = register_openclaw(client, 2, "Executor-B", "available")
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

    create_pkg_resp = client.post(
        "/api/v1/openclaws/capability-packages",
        json={
            "owner_openclaw_id": 2,
            "title": "Executor Package",
            "summary": "General fulfillment package",
            "task_template_id": 1,
            "sample_deliverables": {"kind": "doc"},
            "price_min": "1.00",
            "price_max": "10.00",
            "capacity_per_week": 8,
            "status": "active",
        },
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
            "requester_openclaw_id": 1,
            "task_template_id": 1,
            "title": "Initial Order",
            "requirement_payload": {"scope": "basic"},
        },
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
            "submitted_by_openclaw_id": 2,
        },
    )
    assert deliver_resp.status_code == 200
    deliverable_payload = deliver_resp.json()
    assert_exact_keys(deliverable_payload, DELIVERABLE_VIEW_KEYS)

    notify_ready_resp = client.post(
        f"/api/v1/openclaws/2/orders/{order_id}/notify-result-ready",
        json={"result_summary": {"status": "ready"}},
    )
    assert notify_ready_resp.status_code == 200
    assert_exact_keys(notify_ready_resp.json(), ORDER_VIEW_KEYS)

    receive_result_resp = client.post(
        f"/api/v1/openclaws/1/orders/{order_id}/receive-result",
        json={"checklist_result": {"ok": True}, "note": "received"},
    )
    assert receive_result_resp.status_code == 200
    assert_exact_keys(receive_result_resp.json(), ORDER_VIEW_KEYS)

    usage_receipt_resp = client.post(
        f"/api/v1/orders/{order_id}/usage-receipts",
        json={
            "openclaw_id": 2,
            "provider": "openai",
            "provider_request_id": "req-contract-001",
            "model": "gpt-4.1-mini",
            "prompt_tokens": 120,
            "completion_tokens": 100,
        },
    )
    assert usage_receipt_resp.status_code == 200
    usage_receipt_payload = usage_receipt_resp.json()
    assert_exact_keys(usage_receipt_payload, TOKEN_USAGE_RECEIPT_VIEW_KEYS)

    settle_resp = client.post(
        f"/api/v1/openclaws/2/orders/{order_id}/settle",
        json={"usage_receipt_id": usage_receipt_payload["id"]},
    )
    assert settle_resp.status_code == 200
    assert_exact_keys(settle_resp.json(), SETTLEMENT_VIEW_KEYS)

    publish_order_resp = client.post(
        "/api/v1/openclaws/1/orders",
        json={
            "task_template_id": 2,
            "title": "Published by requester",
            "requirement_payload": {"topic": "content"},
        },
    )
    assert publish_order_resp.status_code == 200
    publish_order = publish_order_resp.json()
    assert_exact_keys(publish_order, ORDER_VIEW_KEYS)

    openclaw_accept_resp = client.post(f"/api/v1/openclaws/2/orders/{publish_order['id']}/accept")
    assert openclaw_accept_resp.status_code == 409 or openclaw_accept_resp.status_code == 200
    if openclaw_accept_resp.status_code == 200:
        assert_exact_keys(openclaw_accept_resp.json(), ORDER_VIEW_KEYS)

    heartbeat_resp = client.post("/api/v1/openclaws/2/heartbeat", json={"service_status": "available"})
    assert heartbeat_resp.status_code == 200
    heartbeat_payload = heartbeat_resp.json()
    assert_exact_keys(heartbeat_payload, HEARTBEAT_VIEW_KEYS)
    if heartbeat_payload["assigned_order"] is not None:
        assert_exact_keys(heartbeat_payload["assigned_order"], ORDER_VIEW_KEYS)

    notifications_resp = client.get("/api/v1/openclaws/2/notifications")
    assert notifications_resp.status_code == 200
    notifications = notifications_resp.json()
    assert len(notifications) >= 1
    assert_exact_keys(notifications[0], NOTIFICATION_VIEW_KEYS)

    ack_resp = client.post(f"/api/v1/openclaws/2/notifications/{notifications[0]['id']}/ack")
    assert ack_resp.status_code == 200
    assert_exact_keys(ack_resp.json(), NOTIFICATION_VIEW_KEYS)

    update_subscription_resp = client.post(
        "/api/v1/openclaws/2/subscription",
        json={"subscription_status": "subscribed"},
    )
    assert update_subscription_resp.status_code == 200
    assert_exact_keys(update_subscription_resp.json(), OPENCLAW_VIEW_KEYS)

    update_service_status_resp = client.post(
        "/api/v1/openclaws/2/service-status",
        json={"service_status": "available", "active_order_id": None},
    )
    assert update_service_status_resp.status_code == 200
    assert_exact_keys(update_service_status_resp.json(), OPENCLAW_VIEW_KEYS)

    created_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": 1,
            "task_template_id": 3,
            "title": "Need assign endpoint",
            "requirement_payload": {"need": "executor"},
        },
    )
    assert created_order_resp.status_code == 200
    created_order = created_order_resp.json()
    assert_exact_keys(created_order, ORDER_VIEW_KEYS)

    assign_resp = client.post(
        f"/api/v1/orders/{created_order['id']}/assign",
        json={"executor_openclaw_id": 2},
    )
    if assign_resp.status_code == 200:
        assert_exact_keys(assign_resp.json(), ORDER_VIEW_KEYS)

    generic_accept_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": 1,
            "task_template_id": 4,
            "title": "Need generic accept",
            "requirement_payload": {"topic": "analysis"},
        },
    )
    assert generic_accept_order_resp.status_code == 200
    generic_accept_order = generic_accept_order_resp.json()
    assert_exact_keys(generic_accept_order, ORDER_VIEW_KEYS)

    generic_accept_resp = client.post(f"/api/v1/orders/{generic_accept_order['id']}/accept")
    if generic_accept_resp.status_code == 200:
        assert_exact_keys(generic_accept_resp.json(), ORDER_VIEW_KEYS)

    complete_order_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": 1,
            "task_template_id": 5,
            "title": "Need complete callback",
            "requirement_payload": {"topic": "workflow"},
        },
    )
    assert complete_order_resp.status_code == 200
    complete_order = complete_order_resp.json()
    assert_exact_keys(complete_order, ORDER_VIEW_KEYS)

    if complete_order["executor_openclaw_id"] == 2 and complete_order["status"] in {"accepted", "in_progress"}:
        complete_callback_resp = client.post(
            f"/api/v1/openclaws/2/orders/{complete_order['id']}/complete",
            json={
                "delivery_note": "final",
                "deliverable_payload": {"bundle": "zip"},
                "result_summary": {"ok": True},
            },
        )
        assert complete_callback_resp.status_code == 200
        assert_exact_keys(complete_callback_resp.json(), ORDER_VIEW_KEYS)

    dispute_resp = client.post(
        f"/api/v1/orders/{created_order['id']}/disputes",
        json={
            "opened_by_openclaw_id": 1,
            "reason_code": "quality_not_met",
            "description": "contract test",
        },
    )
    assert dispute_resp.status_code == 200
    assert_exact_keys(dispute_resp.json(), DISPUTE_VIEW_KEYS)
