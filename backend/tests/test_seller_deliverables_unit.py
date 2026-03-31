"""Unit tests for list_seller_deliverables method"""

from __future__ import annotations

from uuid import uuid4, UUID
from app.service import MarketplaceService
from app.schemas.deliverables import DeliverableDetail, DeliverableView


def test_list_seller_deliverables_empty():
    """Test that list_seller_deliverables returns empty list when no deliverables exist"""
    service = MarketplaceService.__new__(MarketplaceService)
    service.deliverables = {}
    
    seller_id = uuid4()
    result = service.list_seller_deliverables(seller_id, page=0, size=20, sort="submitted_at,desc")
    
    assert result == []


def test_list_seller_deliverables_filters_by_seller():
    """Test that only deliverables from the target seller are returned"""
    from datetime import datetime, UTC
    
    service = MarketplaceService.__new__(MarketplaceService)
    
    seller_1_id = uuid4()
    seller_2_id = uuid4()
    order_1_id = uuid4()
    order_2_id = uuid4()
    order_3_id = uuid4()
    
    # Create deliverables from two different sellers
    deliverable_1 = DeliverableView(
        id=uuid4(),
        order_id=order_1_id,
        version_no=1,
        delivery_note="Seller 1 result",
        deliverable_payload={},
        submitted_by=seller_1_id,
        submitted_at="2026-03-31T10:00:00Z"
    )
    
    deliverable_2 = DeliverableView(
        id=uuid4(),
        order_id=order_2_id,
        version_no=1,
        delivery_note="Seller 2 result",
        deliverable_payload={},
        submitted_by=seller_2_id,
        submitted_at="2026-03-31T11:00:00Z"
    )
    
    deliverable_3 = DeliverableView(
        id=uuid4(),
        order_id=order_3_id,
        version_no=1,
        delivery_note="Seller 1 second result",
        deliverable_payload={},
        submitted_by=seller_1_id,
        submitted_at="2026-03-31T12:00:00Z"
    )
    
    service.deliverables = {
        order_1_id: [deliverable_1],
        order_2_id: [deliverable_2],
        order_3_id: [deliverable_3],
    }
    
    # Query for seller 1
    result = service.list_seller_deliverables(seller_1_id, page=0, size=20, sort="submitted_at,desc")
    
    # Should only get seller 1's deliverables
    assert len(result) == 2
    assert result[0].submitted_by_openclaw_id == seller_1_id
    assert result[1].submitted_by_openclaw_id == seller_1_id
    
    # Most recent first (desc order)
    assert result[0].submitted_at == "2026-03-31T12:00:00Z"
    assert result[1].submitted_at == "2026-03-31T10:00:00Z"


def test_list_seller_deliverables_sorting():
    """Test sorting by submitted_at in ascending and descending order"""
    service = MarketplaceService.__new__(MarketplaceService)
    
    seller_id = uuid4()
    
    deliverables = [
        DeliverableView(
            id=uuid4(),
            order_id=uuid4(),
            version_no=1,
            delivery_note=f"Result {i}",
            deliverable_payload={},
            submitted_by=seller_id,
            submitted_at=f"2026-03-31T{10+i:02d}:00:00Z"
        )
        for i in range(3)
    ]
    
    service.deliverables = {d.order_id: [d] for d in deliverables}
    
    # Test descending (most recent first)
    desc_result = service.list_seller_deliverables(seller_id, page=0, size=20, sort="submitted_at,desc")
    assert desc_result[0].submitted_at == "2026-03-31T12:00:00Z"
    assert desc_result[-1].submitted_at == "2026-03-31T10:00:00Z"
    
    # Test ascending (oldest first)
    asc_result = service.list_seller_deliverables(seller_id, page=0, size=20, sort="submitted_at,asc")
    assert asc_result[0].submitted_at == "2026-03-31T10:00:00Z"
    assert asc_result[-1].submitted_at == "2026-03-31T12:00:00Z"


def test_list_seller_deliverables_pagination():
    """Test pagination with page and size parameters"""
    service = MarketplaceService.__new__(MarketplaceService)
    
    seller_id = uuid4()
    
    deliverables = [
        DeliverableView(
            id=uuid4(),
            order_id=uuid4(),
            version_no=1,
            delivery_note=f"Result {i}",
            deliverable_payload={},
            submitted_by=seller_id,
            submitted_at=f"2026-03-31T{10+i:02d}:00:00Z"
        )
        for i in range(5)
    ]
    
    service.deliverables = {d.order_id: [d] for d in deliverables}
    
    # Get page 0, size 2
    page_0 = service.list_seller_deliverables(seller_id, page=0, size=2, sort="submitted_at,desc")
    assert len(page_0) == 2
    
    # Get page 1, size 2
    page_1 = service.list_seller_deliverables(seller_id, page=1, size=2, sort="submitted_at,desc")
    assert len(page_1) == 2
    
    # Get page 2, size 2 (only 1 left)
    page_2 = service.list_seller_deliverables(seller_id, page=2, size=2, sort="submitted_at,desc")
    assert len(page_2) == 1
    
    # Verify no overlap between pages
    page_0_ids = {d.id for d in page_0}
    page_1_ids = {d.id for d in page_1}
    page_2_ids = {d.id for d in page_2}
    
    assert page_0_ids.isdisjoint(page_1_ids)
    assert page_1_ids.isdisjoint(page_2_ids)
    assert page_0_ids.isdisjoint(page_2_ids)


if __name__ == "__main__":
    test_list_seller_deliverables_empty()
    print("✓ Empty list test passed")
    
    test_list_seller_deliverables_filters_by_seller()
    print("✓ Seller filtering test passed")
    
    test_list_seller_deliverables_sorting()
    print("✓ Sorting test passed")
    
    test_list_seller_deliverables_pagination()
    print("✓ Pagination test passed")
    
    print("\nAll unit tests passed!")
