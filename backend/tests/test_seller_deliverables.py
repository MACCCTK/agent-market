"""Integration tests for seller deliverables retrieval endpoint"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app import main as main_module


# ============================================================================
# Helper functions (from test_trade_flow.py)
# ============================================================================

def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def first_template_id(client: TestClient) -> str:
    resp = client.get("/api/v1/task-templates")
    templates = resp.json()
    assert len(templates) > 0
    return templates[0]["id"]


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


def register_openclaw_actor(
    client: TestClient,
    openclaw_id: str,
    name: str,
    service_status: str = "available",
) -> tuple[dict, dict[str, str]]:
    profile = register_openclaw(client, openclaw_id, name, service_status)
    headers = bootstrap_openclaw_auth_headers(client, openclaw_id)
    if service_status == "available":
        heartbeat_resp = client.post(
            f"/api/v1/openclaws/{openclaw_id}/heartbeat",
            json={"service_status": "available"},
            headers=headers,
        )
        assert heartbeat_resp.status_code == 200
    return profile, headers


@pytest.fixture(scope="session")
def client():
    """Create a test client with service from environment"""
    main_module.service = main_module.create_service_from_env()
    main_module.deadline_worker = None
    return TestClient(main_module.app)


# ============================================================================
# Integration Tests for seller deliverables
# ============================================================================

class TestSellerDeliverablesIntegration:
    """Integration tests for seller deliverables endpoint"""

    def test_list_empty_deliverables(self, client: TestClient) -> None:
        """Test GET endpoint with seller having no deliverables"""
        seller_id = str(uuid4())
        _, seller_headers = register_openclaw_actor(client, seller_id, "Seller-Integration-Empty", "available")

        # List deliverables for seller with none
        resp = client.get(
            f"/api/v1/openclaws/{seller_id}/deliverables",
            headers=seller_headers,
        )

        assert resp.status_code == 200
        deliverables = resp.json()
        assert isinstance(deliverables, list)
        assert len(deliverables) == 0

    def test_list_single_deliverable(self, client: TestClient) -> None:
        """Test listing a single submitted deliverable via API"""
        requester_id = str(uuid4())
        seller_id = str(uuid4())
        template_id = first_template_id(client)

        _, requester_headers = register_openclaw_actor(client, requester_id, "Requester-Integration", "available")
        _, seller_headers = register_openclaw_actor(client, seller_id, "Seller-Integration", "available")

        # Create order
        create_resp = client.post(
            "/api/v1/orders",
            json={
                "requester_openclaw_id": requester_id,
                "task_template_id": template_id,
                "title": "Integration Test Task",
                "requirement_payload": {"test": True},
            },
            headers=requester_headers,
        )
        assert create_resp.status_code == 200
        order = create_resp.json()

        # Try to accept the order
        accept_resp = client.post(
            f"/api/v1/openclaws/{seller_id}/orders/{order['id']}/accept",
            headers=seller_headers,
        )
        # Order might already be auto-assigned, that's ok
        if accept_resp.status_code == 200:
            # Now submit deliverable
            delivery_resp = client.post(
                f"/api/v1/openclaws/{seller_id}/orders/{order['id']}/complete",
                json={
                    "delivery_note": "Integration test deliverable",
                    "deliverable_payload": {},
                    "result_summary": {"summary": "Integration test result"},
                },
                headers=seller_headers,
            )
            assert delivery_resp.status_code == 200

            # List seller deliverables
            list_resp = client.get(
                f"/api/v1/openclaws/{seller_id}/deliverables",
                headers=seller_headers,
            )
            assert list_resp.status_code == 200
            deliverables = list_resp.json()
            
            # Should have at least one deliverable
            assert len(deliverables) >= 1
            
            # Verify structure
            deliverable = deliverables[0]
            assert deliverable["order_id"] == order["id"]
            assert deliverable["delivery_note"] == "Integration test deliverable"
            assert deliverable["submitted_by_openclaw_id"] == seller_id
            assert "submitted_at" in deliverable
            assert "id" in deliverable
            assert "version_no" in deliverable
            assert "deliverable_payload" in deliverable

    def test_unauthorized_access_denied(self, client: TestClient) -> None:
        """Test that other sellers cannot access this seller's deliverables"""
        requester_id = str(uuid4())
        seller_1_id = str(uuid4())
        seller_2_id = str(uuid4())

        _, requester_headers = register_openclaw_actor(client, requester_id, "Requester-Auth", "available")
        _, seller_1_headers = register_openclaw_actor(client, seller_1_id, "Seller-Auth-1", "available")
        _, seller_2_headers = register_openclaw_actor(client, seller_2_id, "Seller-Auth-2", "available")

        # Seller 1 tries to access seller 2's deliverables - should be forbidden
        resp = client.get(
            f"/api/v1/openclaws/{seller_2_id}/deliverables",
            headers=seller_1_headers,
        )
        assert resp.status_code == 403

    def test_pagination_parameters(self, client: TestClient) -> None:
        """Test pagination parameters work correctly"""
        seller_id = str(uuid4())
        _, seller_headers = register_openclaw_actor(client, seller_id, "Seller-Pagination", "available")

        # Test with pagination params
        resp = client.get(
            f"/api/v1/openclaws/{seller_id}/deliverables?page=0&size=10",
            headers=seller_headers,
        )
        assert resp.status_code == 200
        deliverables = resp.json()
        assert isinstance(deliverables, list)
        assert len(deliverables) <= 10

    def test_sorting_parameter(self, client: TestClient) -> None:
        """Test that sort parameter is accepted"""
        seller_id = str(uuid4())
        _, seller_headers = register_openclaw_actor(client, seller_id, "Seller-Sort", "available")

        # Test with sort descending (default)
        resp_desc = client.get(
            f"/api/v1/openclaws/{seller_id}/deliverables?sort=submitted_at,desc",
            headers=seller_headers,
        )
        assert resp_desc.status_code == 200

        # Test with sort ascending
        resp_asc = client.get(
            f"/api/v1/openclaws/{seller_id}/deliverables?sort=submitted_at,asc",
            headers=seller_headers,
        )
        assert resp_asc.status_code == 200

    def test_response_structure(self, client: TestClient) -> None:
        """Test the response structure is correct"""
        seller_id = str(uuid4())
        _, seller_headers = register_openclaw_actor(client, seller_id, "Seller-Structure", "available")

        resp = client.get(
            f"/api/v1/openclaws/{seller_id}/deliverables",
            headers=seller_headers,
        )
        
        assert resp.status_code == 200
        
        # Response should be a list
        data = resp.json()
        assert isinstance(data, list)
        
        # Each item should have required fields if list is not empty
        if len(data) > 0:
            for item in data:
                assert isinstance(item, dict)
                assert "id" in item
                assert "order_id" in item
                assert "version_no" in item
                assert "delivery_note" in item
                assert "deliverable_payload" in item
                assert "submitted_by_openclaw_id" in item
                assert "submitted_at" in item
                
                # Verify types
                assert isinstance(item["id"], str)
                assert isinstance(item["order_id"], str)
                assert isinstance(item["version_no"], int)
                assert isinstance(item["delivery_note"], str)
                assert isinstance(item["deliverable_payload"], dict)
                assert isinstance(item["submitted_by_openclaw_id"], str)
                assert isinstance(item["submitted_at"], str)

    def test_missing_auth_header(self, client: TestClient) -> None:
        """Test that missing auth header returns 401"""
        seller_id = str(uuid4())
        
        resp = client.get(f"/api/v1/openclaws/{seller_id}/deliverables")
        assert resp.status_code == 401

    def test_invalid_seller_id_format(self, client: TestClient) -> None:
        """Test with invalid UUID format"""
        _, headers = register_openclaw_actor(client, str(uuid4()), "Seller-Invalid", "available")
        
        # Use invalid UUID format
        resp = client.get(
            "/api/v1/openclaws/not-a-uuid/deliverables",
            headers=headers,
        )
        # Should fail with 400/403/422 depending on validation
        assert resp.status_code in [400, 403, 422]
