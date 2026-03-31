#!/usr/bin/env python3
"""
演示脚本：获取reviewing状态订单的交付物信息

使用卖方交付物接口获取reviewing状态订单的交付物信息。
该脚本展示了完整的工作流：
1. 创建需求方和卖方
2. 创建订单
3. 卖方接受订单
4. 卖方提交交付物（订单进入reviewing状态）
5. 通过API获取交付物信息
6. 验证订单状态
"""
from uuid import uuid4, UUID
from fastapi.testclient import TestClient
from app import main as main_module


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def first_template_id(client: TestClient) -> str:
    resp = client.get("/api/v1/task-templates")
    templates = resp.json()
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


def main():
    # 初始化服务
    main_module.service = main_module.create_service_from_env()
    main_module.deadline_worker = None
    client = TestClient(main_module.app)

    print("=" * 80)
    print("获取Reviewing状态订单的交付物信息 - 通过卖方交付物接口")
    print("=" * 80)

    # 设置
    requester_id = str(uuid4())
    seller_id = str(uuid4())
    template_id = first_template_id(client)

    print(f"\n1️⃣  注册用户...")
    _, requester_headers = register_openclaw_actor(client, requester_id, "Test Requester", "available")
    _, seller_headers = register_openclaw_actor(client, seller_id, "Test Seller", "available")
    print(f"   ✅ 需求方ID: {requester_id}")
    print(f"   ✅ 卖方ID: {seller_id}")

    # 创建订单
    print(f"\n2️⃣  创建订单...")
    create_resp = client.post(
        "/api/v1/orders",
        json={
            "requester_openclaw_id": requester_id,
            "task_template_id": template_id,
            "title": "Market Analysis Task",
            "requirement_payload": {"topic": "Cloud Computing Trends"},
        },
        headers=requester_headers,
    )
    assert create_resp.status_code == 200
    order = create_resp.json()
    order_id = order["id"]
    print(f"   ✅ 订单已创建")
    print(f"   📋 订单ID: {order_id}")
    print(f"   📊 初始状态: {order['status']}")

    # 卖方接受订单
    print(f"\n3️⃣  卖方接受订单...")
    accept_resp = client.post(
        f"/api/v1/openclaws/{seller_id}/orders/{order_id}/accept",
        headers=seller_headers,
    )
    assert accept_resp.status_code == 200
    accepted_order = accept_resp.json()
    print(f"   ✅ 订单已接受")
    print(f"   📊 状态: {accepted_order['status']}")

    # 提交交付物，使订单进入reviewing状态
    print(f"\n4️⃣  提交交付物（订单进入reviewing状态）...")
    delivery_resp = client.post(
        f"/api/v1/openclaws/{seller_id}/orders/{order_id}/complete",
        json={
            "delivery_note": "Comprehensive analysis of cloud computing market trends for Q1 2026",
            "deliverable_payload": {
                "market_analysis": {
                    "total_market_value": "$650 billion",
                    "growth_rate": "18.5% YoY",
                    "key_vendors": ["AWS", "Azure", "Google Cloud"],
                    "emerging_trends": [
                        "AI/ML integration",
                        "Edge computing",
                        "Hybrid cloud adoption"
                    ]
                },
                "recommendations": {
                    "for_enterprises": "Focus on multi-cloud strategy",
                    "for_startups": "Leverage serverless architecture"
                }
            },
            "result_summary": {"summary": "Market shows strong growth with AI/ML as primary driver"}
        },
        headers=seller_headers,
    )
    assert delivery_resp.status_code == 200
    reviewing_order = delivery_resp.json()
    print(f"   ✅ 交付物已提交")
    print(f"   📊 当前状态: {reviewing_order['status']}")
    print(f"   ⏰ 评审开始时间: {reviewing_order['review_started_at']}")
    print(f"   ⏰ 评审过期时间: {reviewing_order['review_expires_at']}")

    # 使用卖方交付物接口获取交付物
    print(f"\n5️⃣  通过卖方交付物接口获取交付物...")
    print(f"   🔗 GET /api/v1/openclaws/{seller_id}/deliverables")
    
    list_resp = client.get(
        f"/api/v1/openclaws/{seller_id}/deliverables",
        headers=seller_headers,
    )
    assert list_resp.status_code == 200
    deliverables = list_resp.json()
    print(f"   ✅ 接口响应成功")
    print(f"   📦 返回交付物数量: {len(deliverables)}")

    if deliverables:
        d = deliverables[0]
        print(f"\n" + "=" * 80)
        print("📊 交付物详情 (对应Reviewing状态订单)")
        print("=" * 80)
        print(f"交付物ID:          {d['id']}")
        print(f"关联订单ID:        {d['order_id']}")
        print(f"版本号:            {d['version_no']}")
        print(f"提交者ID:          {d['submitted_by_openclaw_id']}")
        print(f"提交时间:          {d['submitted_at']}")
        print(f"\n交付说明:")
        print(f"  {d['delivery_note']}")
        print(f"\nPayload 内容:")
        if d['deliverable_payload']:
            import json
            payload_str = json.dumps(d['deliverable_payload'], indent=2, ensure_ascii=False)
            for line in payload_str.split('\n'):
                print(f"  {line}")
        print("=" * 80)
        
        # 验证此交付物对应的订单确实是reviewing状态
        print(f"\n6️⃣  验证订单状态...")
        verify_resp = client.get(
            f"/api/v1/orders/{d['order_id']}",
            headers=requester_headers,
        )
        assert verify_resp.status_code == 200
        verified_order = verify_resp.json()
        print(f"   ✅ 订单状态确认: {verified_order['status']}")
        
        if verified_order['status'] == 'reviewing':
            print(f"\n✨ 成功！该交付物对应的订单确实处于 'reviewing' 状态")
        
        print(f"\n📋 订单信息:")
        print(f"   订单ID:        {verified_order['id']}")
        print(f"   订单号:        {verified_order['order_no']}")
        print(f"   标题:          {verified_order['title']}")
        print(f"   状态:          {verified_order['status']}")
        print(f"   需求方:        {verified_order['requester_openclaw_id']}")
        print(f"   执行方:        {verified_order['executor_openclaw_id']}")
        print(f"   创建时间:      {verified_order['created_at']}")
        print(f"   评审开始时间:  {verified_order['review_started_at']}")
        print(f"   评审过期时间:  {verified_order['review_expires_at']}")
        
        print("\n" + "=" * 80)
        print("✅ 测试完成！")
        print("=" * 80)


if __name__ == "__main__":
    main()
