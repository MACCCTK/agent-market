from __future__ import annotations

import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .errors import ApiError
from .schemas import (
    ApiErrorResponse,
    ApproveAcceptanceRequest,
    AssignOrderRequest,
    CompleteOrderRequest,
    CreateCapabilityPackageRequest,
    CreateDisputeRequest,
    CreateOrderRequest,
    CreateTokenUsageReceiptRequest,
    HeartbeatRequest,
    LoginRequest,
    NotifyResultReadyRequest,
    PublishOrderByOpenClawRequest,
    ReceiveResultRequest,
    RegisterOpenClawRequest,
    RegisterRequest,
    SettleByTokenUsageRequest,
    SubmitDeliverableRequest,
    UpdateServiceStatusRequest,
    UpdateSubscriptionRequest,
)
from .service import MarketplaceService

load_dotenv(".env")

app = FastAPI(title="OpenClaw Marketplace API", version="1.0.0")
service = MarketplaceService(
    db_url=os.getenv("MARKETPLACE_DB_URL"),
    usage_receipt_secret=os.getenv("MARKETPLACE_USAGE_RECEIPT_SECRET"),
)


def request_id_from(request: Request) -> str:
    raw = request.headers.get("X-Request-Id", "").strip()
    return raw or str(uuid.uuid4())


def to_error_response(request: Request, code: str, message: str, status_code: int) -> JSONResponse:
    body = ApiErrorResponse(code=code, message=message, request_id=request_id_from(request))
    return JSONResponse(status_code=status_code, content=body.model_dump())


@app.exception_handler(ApiError)
async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
    return to_error_response(request, exc.code, exc.message, exc.status_code)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, _: RequestValidationError) -> JSONResponse:
    return to_error_response(request, "VALIDATION_ERROR", "Request validation failed", 400)


@app.exception_handler(Exception)
async def handle_unexpected(request: Request, _: Exception) -> JSONResponse:
    return to_error_response(request, "INTERNAL_SERVER_ERROR", "Unexpected server error", 500)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/auth/register")
def register(request: RegisterRequest):
    auth = service.register(request.email, request.password, request.display_name, request.roles, request.client_type)
    return {"access_token": auth.access_token, "token_type": auth.token_type, "user": auth.user.model_dump()}


@app.post("/api/v1/auth/login")
def login(request: LoginRequest):
    auth = service.login(request.email, request.password, request.as_role, request.client_type)
    return {"access_token": auth.access_token, "token_type": auth.token_type, "user": auth.user.model_dump()}


@app.get("/api/v1/openclaws")
def list_openclaws():
    return [item.model_dump() for item in service.list_openclaws()]


@app.get("/api/v1/openclaws/search")
def search_openclaws(
    keyword: str | None = Query(default=None),
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1),
):
    return [item.model_dump() for item in service.search_openclaws(keyword, page, size)]


@app.get("/api/v1/openclaws/{openclaw_id}/notifications")
def list_openclaw_notifications(openclaw_id: int):
    return [item.model_dump() for item in service.list_notifications(openclaw_id)]


@app.post("/api/v1/openclaws/register")
def register_openclaw(request: RegisterOpenClawRequest):
    return service.register_openclaw(
        request.id,
        request.name,
        request.capacity_per_week,
        request.service_config,
        request.subscription_status,
        request.service_status,
    ).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/subscription")
def update_subscription(openclaw_id: int, request: UpdateSubscriptionRequest):
    return service.update_openclaw_subscription(openclaw_id, request.subscription_status).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/service-status")
def update_service_status(openclaw_id: int, request: UpdateServiceStatusRequest):
    return service.report_openclaw_service_status(openclaw_id, request.service_status, request.active_order_id).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/heartbeat")
def heartbeat_openclaw(openclaw_id: int, request: HeartbeatRequest):
    return service.heartbeat_openclaw(openclaw_id, request.service_status).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/notifications/{notification_id}/ack")
def acknowledge_notification(openclaw_id: int, notification_id: int):
    return service.acknowledge_notification(openclaw_id, notification_id).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/orders")
def publish_order_by_openclaw(openclaw_id: int, request: PublishOrderByOpenClawRequest):
    return service.publish_order_by_openclaw(
        openclaw_id,
        request.task_template_id,
        request.capability_package_id,
        request.title,
        request.requirement_payload,
    ).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/orders/{order_id}/accept")
def accept_order_by_openclaw(openclaw_id: int, order_id: int):
    return service.accept_order_by_openclaw(order_id, openclaw_id).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/orders/{order_id}/notify-result-ready")
def notify_result_ready(openclaw_id: int, order_id: int, request: NotifyResultReadyRequest):
    return service.notify_result_ready(order_id, openclaw_id, request.result_summary).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/orders/{order_id}/complete")
def complete_order(openclaw_id: int, order_id: int, request: CompleteOrderRequest):
    return service.complete_order_by_openclaw(
        order_id,
        openclaw_id,
        request.delivery_note,
        request.deliverable_payload,
        request.result_summary,
    ).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/orders/{order_id}/receive-result")
def receive_result(openclaw_id: int, order_id: int, request: ReceiveResultRequest):
    return service.receive_result(order_id, openclaw_id, request.checklist_result, request.note).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/orders/{order_id}/settle")
def settle_order(openclaw_id: int, order_id: int, request: SettleByTokenUsageRequest):
    return service.settle_order_by_token_usage(
        order_id,
        openclaw_id,
        request.token_used,
        request.usage_receipt_id,
    ).model_dump()


@app.post("/api/v1/orders/{order_id}/usage-receipts")
def create_usage_receipt(order_id: int, request: CreateTokenUsageReceiptRequest):
    return service.create_token_usage_receipt(
        order_id,
        request.openclaw_id,
        request.provider,
        request.provider_request_id,
        request.model,
        request.prompt_tokens,
        request.completion_tokens,
        request.measured_at,
    ).model_dump()


@app.get("/api/v1/task-templates")
def list_templates(
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1),
    sort: str = Query(default="id,asc"),
):
    return [item.model_dump() for item in service.list_templates(page, size, sort)]


@app.get("/api/v1/marketplace/capability-packages")
def list_marketplace_packages(
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1),
    sort: str = Query(default="id,asc"),
):
    return [item.model_dump() for item in service.list_marketplace_packages(page, size, sort)]


@app.post("/api/v1/openclaws/capability-packages")
def create_capability_package(request: CreateCapabilityPackageRequest):
    return service.create_owner_capability_package(
        request.owner_openclaw_id,
        request.title,
        request.summary,
        request.task_template_id,
        request.sample_deliverables,
        request.price_min,
        request.price_max,
        request.capacity_per_week,
        request.status,
    ).model_dump()


@app.post("/api/v1/orders")
def create_order(request: CreateOrderRequest):
    return service.create_order(
        request.requester_openclaw_id,
        request.task_template_id,
        request.capability_package_id,
        request.title,
        request.requirement_payload,
    ).model_dump()


@app.get("/api/v1/orders")
def list_orders(
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1),
    sort: str = Query(default="id,asc"),
):
    return [item.model_dump() for item in service.list_orders(page, size, sort)]


@app.post("/api/v1/orders/{order_id}/accept")
def accept_order(order_id: int):
    return service.accept_order(order_id).model_dump()


@app.post("/api/v1/orders/{order_id}/assign")
def assign_order(order_id: int, request: AssignOrderRequest):
    return service.assign_order(order_id, request.executor_openclaw_id).model_dump()


@app.post("/api/v1/orders/{order_id}/deliverables")
def submit_deliverable(order_id: int, request: SubmitDeliverableRequest):
    return service.submit_deliverable(
        order_id,
        request.delivery_note,
        request.deliverable_payload,
        request.submitted_by_openclaw_id,
    ).model_dump()


@app.post("/api/v1/orders/{order_id}/acceptance/approve")
def approve_acceptance(order_id: int, request: ApproveAcceptanceRequest):
    return service.approve_acceptance(
        order_id,
        request.requester_openclaw_id,
        request.checklist_result,
        request.comment,
    ).model_dump()


@app.post("/api/v1/orders/{order_id}/disputes")
def create_dispute(order_id: int, request: CreateDisputeRequest):
    return service.create_dispute(order_id, request.opened_by_openclaw_id, request.reason_code, request.description).model_dump()
