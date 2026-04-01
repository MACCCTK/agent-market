from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.errors import ApiError
from app.schemas.deliverables import DeliverableView
from app.schemas.orders import OrderView
from app.service import MarketplaceService


def build_order(*, requester_id, executor_id=None) -> OrderView:
    now = "2026-04-01T00:00:00Z"
    return OrderView(
        id=uuid4(),
        order_no="ORD-TEST-001",
        requester_openclaw_id=requester_id,
        executor_openclaw_id=executor_id,
        task_template_id=uuid4(),
        capability_package_id=None,
        title="Deliverable access test",
        status="reviewing",
        quoted_price=Decimal("1.00"),
        currency="USD",
        sla_seconds=3600,
        requirement_payload={"topic": "access"},
        published_at=now,
        assigned_at=now,
        assignment_expires_at=None,
        acknowledged_at=now,
        started_at=now,
        delivered_at=now,
        review_started_at=now,
        review_expires_at=None,
        approved_at=None,
        settled_at=None,
        cancelled_at=None,
        expired_at=None,
        failed_at=None,
        latest_failure_code=None,
        latest_failure_note=None,
        assignment_attempt_count=1,
        created_at=now,
        updated_at=now,
    )


def build_deliverable(order_id, submitted_by, version_no: int, submitted_at: str) -> DeliverableView:
    return DeliverableView(
        id=uuid4(),
        order_id=order_id,
        version_no=version_no,
        delivery_note=f"delivery-{version_no}",
        deliverable_payload={"artifact": f"bundle-{version_no}"},
        submitted_by=submitted_by,
        submitted_at=submitted_at,
    )


def build_service(order: OrderView, deliverables: list[DeliverableView]) -> MarketplaceService:
    service = MarketplaceService.__new__(MarketplaceService)
    service.orders = {order.id: order}
    service.deliverables = {order.id: deliverables}
    return service


def test_list_order_deliverables_allows_requester_and_executor() -> None:
    requester_id = uuid4()
    executor_id = uuid4()
    order = build_order(requester_id=requester_id, executor_id=executor_id)
    service = build_service(
        order,
        [
            build_deliverable(order.id, executor_id, 1, "2026-04-01T09:00:00Z"),
            build_deliverable(order.id, executor_id, 2, "2026-04-01T10:00:00Z"),
        ],
    )

    requester_view = service.list_order_deliverables_for_openclaw(
        order.id, requester_id, page=0, size=20, sort="submitted_at,desc"
    )
    executor_view = service.list_order_deliverables_for_openclaw(
        order.id, executor_id, page=0, size=20, sort="submitted_at,asc"
    )

    assert [item.version_no for item in requester_view] == [2, 1]
    assert [item.version_no for item in executor_view] == [1, 2]
    assert all(item.submitted_by_openclaw_id == executor_id for item in requester_view)


def test_list_order_deliverables_rejects_unrelated_openclaw() -> None:
    requester_id = uuid4()
    executor_id = uuid4()
    outsider_id = uuid4()
    order = build_order(requester_id=requester_id, executor_id=executor_id)
    service = build_service(order, [build_deliverable(order.id, executor_id, 1, "2026-04-01T09:00:00Z")])

    with pytest.raises(ApiError) as exc_info:
        service.list_order_deliverables_for_openclaw(order.id, outsider_id, page=0, size=20, sort="submitted_at,desc")

    assert exc_info.value.code == "AUTH_FORBIDDEN"
    assert exc_info.value.status_code == 403


def test_order_deliverables_endpoint_allows_buyer_reads() -> None:
    requester_id = uuid4()
    executor_id = uuid4()
    order = build_order(requester_id=requester_id, executor_id=executor_id)
    service = build_service(order, [build_deliverable(order.id, executor_id, 1, "2026-04-01T09:00:00Z")])
    service.authenticate_token = lambda token: SimpleNamespace(id=requester_id)

    original_service = main_module.service
    main_module.service = service
    try:
        client = TestClient(main_module.app)
        response = client.get(
            f"/api/v1/openclaws/{requester_id}/orders/{order.id}/deliverables",
            headers={"Authorization": "Bearer buyer-token"},
        )
    finally:
        main_module.service = original_service

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["order_id"] == str(order.id)
    assert payload[0]["submitted_by_openclaw_id"] == str(executor_id)
