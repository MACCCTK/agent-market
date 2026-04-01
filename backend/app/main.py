from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

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
    DeliverableDetail,
    FailOrderRequest,
    HeartbeatRequest,
    OpenClawCapabilityUpdateRequest,
    OpenClawLoginRequest,
    OpenClawProfileUpdateRequest,
    OpenClawRegisterRequest,
    NotifyResultReadyRequest,
    OrderCancelRequest,
    OrderReviewRequest,
    PublishOrderByOpenClawRequest,
    ReceiveResultRequest,
    RegisterOpenClawRequest,
    ResolveDisputeRequest,
    SearchCapabilityRequest,
    SettleByTokenUsageRequest,
    SubmitDeliverableRequest,
    UpdateServiceStatusRequest,
    UpdateSubscriptionRequest,
)
from .service import MarketplaceService

_APP_FILE = Path(__file__).resolve()
load_dotenv(_APP_FILE.parents[2] / ".env")
load_dotenv(_APP_FILE.parents[1] / ".env")

def create_service_from_env() -> MarketplaceService | None:
    db_url = (os.getenv("MARKETPLACE_DB_URL") or "").strip()
    if not db_url:
        return None
    return MarketplaceService(
        db_url=db_url,
        usage_receipt_secret=os.getenv("MARKETPLACE_USAGE_RECEIPT_SECRET"),
    )


service: MarketplaceService | None = None


def get_service() -> MarketplaceService:
    global service
    if service is None:
        service = create_service_from_env()
    if service is None:
        raise ApiError("PERSISTENCE_ERROR", 500, "MARKETPLACE_DB_URL must be configured")
    return service


def deadline_worker_enabled_from_env() -> bool:
    raw = (os.getenv("MARKETPLACE_ENABLE_DEADLINE_WORKER") or "").strip().lower()
    if raw:
        return raw in {"1", "true", "yes", "on"}
    return "PYTEST_CURRENT_TEST" not in os.environ


def notification_retry_worker_enabled_from_env() -> bool:
    raw = (os.getenv("MARKETPLACE_ENABLE_NOTIFICATION_RETRY_WORKER") or "").strip().lower()
    if raw:
        return raw in {"1", "true", "yes", "on"}
    return "PYTEST_CURRENT_TEST" not in os.environ


@asynccontextmanager
async def marketplace_lifespan(_: FastAPI):
    current_service = get_service()
    if deadline_worker_enabled_from_env():
        current_service.start_deadline_worker()
    if notification_retry_worker_enabled_from_env():
        current_service.start_notification_retry_worker()
    try:
        yield
    finally:
        if service is not None:
            service.stop_notification_retry_worker()
            service.stop_deadline_worker()


app = FastAPI(title="OpenClaw Marketplace API", version="1.0.0", lifespan=marketplace_lifespan)


def request_id_from(request: Request) -> str:
    raw = request.headers.get("X-Request-Id", "").strip()
    return raw or str(uuid.uuid4())


def bearer_token_from(request: Request) -> str:
    authorization = request.headers.get("Authorization", "").strip()
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        raise ApiError("AUTH_TOKEN_REQUIRED", 401, "Bearer token is required")
    return credentials.strip()


def authenticated_openclaw_id(request: Request) -> UUID:
    return get_service().authenticate_token(bearer_token_from(request)).id


def require_openclaw_owner(request: Request, openclaw_id: UUID) -> UUID:
    actor_id = authenticated_openclaw_id(request)
    if actor_id != openclaw_id:
        raise ApiError("AUTH_FORBIDDEN", 403, "Authenticated OpenClaw does not own this resource")
    return actor_id


def require_body_actor(request: Request, openclaw_id: UUID) -> UUID:
    actor_id = authenticated_openclaw_id(request)
    if actor_id != openclaw_id:
        raise ApiError("AUTH_FORBIDDEN", 403, "Authenticated OpenClaw does not match the requested actor")
    return actor_id


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
def register(request: OpenClawRegisterRequest):
    auth = get_service().register(
        request.email,
        request.password,
        request.display_name,
        request.capacity_per_week,
        request.service_config,
        request.subscription_status,
        request.service_status,
        request.profile.model_dump(exclude_none=True) if request.profile is not None else None,
        request.capabilities.model_dump(exclude_none=True) if request.capabilities is not None else None,
    )
    return {"access_token": auth.access_token, "token_type": auth.token_type, "openclaw": auth.user.model_dump()}


@app.post("/api/v1/auth/login")
def login(request: OpenClawLoginRequest):
    auth = get_service().login(request.email, request.password)
    return {"access_token": auth.access_token, "token_type": auth.token_type, "openclaw": auth.user.model_dump()}


@app.get("/api/v1/openclaws")
def list_openclaws():
    return [item.model_dump() for item in get_service().list_openclaws()]


@app.get("/api/v1/openclaws/search")
def search_openclaws(
    keyword: str | None = Query(default=None),
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1),
):
    return [item.model_dump() for item in get_service().search_openclaws(keyword, page, size)]


@app.get("/api/v1/openclaws/{openclaw_id}")
def get_openclaw_detail(openclaw_id: UUID):
    return get_service().get_openclaw_detail(openclaw_id).model_dump()


@app.get("/api/v1/openclaws/{openclaw_id}/deliverables")
def list_seller_deliverables(
    openclaw_id: UUID,
    http_request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1),
    sort: str = Query(default="submitted_at,desc"),
):
    require_openclaw_owner(http_request, openclaw_id)
    return [item.model_dump() for item in get_service().list_seller_deliverables(openclaw_id, page, size, sort)]


@app.post("/api/v1/openclaws/{openclaw_id}/profile")
def update_openclaw_profile(openclaw_id: UUID, request: OpenClawProfileUpdateRequest, http_request: Request):
    require_openclaw_owner(http_request, openclaw_id)
    return get_service().update_openclaw_profile(
        openclaw_id,
        request.model_dump(exclude_unset=True, exclude_none=True),
    ).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/capabilities")
def update_openclaw_capabilities(openclaw_id: UUID, request: OpenClawCapabilityUpdateRequest, http_request: Request):
    require_openclaw_owner(http_request, openclaw_id)
    return get_service().update_openclaw_capabilities(
        openclaw_id,
        request.model_dump(exclude_unset=True, exclude_none=True),
    ).model_dump()


@app.get("/api/v1/openclaws/{openclaw_id}/notifications")
def list_openclaw_notifications(openclaw_id: UUID, http_request: Request):
    require_openclaw_owner(http_request, openclaw_id)
    return [item.model_dump() for item in get_service().list_notifications(openclaw_id)]


@app.get("/api/v1/openclaws/{openclaw_id}/orders/{order_id}/deliverables")
def list_order_deliverables_for_openclaw(
    openclaw_id: UUID,
    order_id: UUID,
    http_request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1),
    sort: str = Query(default="submitted_at,desc"),
):
    require_openclaw_owner(http_request, openclaw_id)
    return [
        item.model_dump()
        for item in get_service().list_order_deliverables_for_openclaw(order_id, openclaw_id, page, size, sort)
    ]


@app.get("/api/v1/notifications/operations")
def list_notification_operations(
    status: list[str] | None = Query(default=None),
    openclaw_id: UUID | None = Query(default=None),
    order_id: UUID | None = Query(default=None),
):
    return [
        item.model_dump()
        for item in get_service().list_notification_operations(statuses=status, openclaw_id=openclaw_id, order_id=order_id)
    ]


@app.get("/api/v1/notifications/delivery-metrics")
def get_notification_delivery_metrics(
    openclaw_id: UUID | None = Query(default=None),
    order_id: UUID | None = Query(default=None),
):
    return get_service().get_notification_delivery_metrics(openclaw_id=openclaw_id, order_id=order_id).model_dump()


@app.get("/api/v1/notifications/alerts")
def get_notification_alert_summary(
    openclaw_id: UUID | None = Query(default=None),
    order_id: UUID | None = Query(default=None),
):
    return get_service().get_notification_alert_summary(openclaw_id=openclaw_id, order_id=order_id).model_dump()


@app.post("/api/v1/notifications/process-retries")
def process_notification_retries():
    return get_service().process_notification_retries().model_dump()


@app.post("/api/v1/openclaws/register")
def register_openclaw(request: RegisterOpenClawRequest):
    return get_service().register_openclaw(
        request.id,
        request.name,
        request.capacity_per_week,
        request.service_config,
        request.subscription_status,
        request.service_status,
    ).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/subscription")
def update_subscription(openclaw_id: UUID, request: UpdateSubscriptionRequest, http_request: Request):
    require_openclaw_owner(http_request, openclaw_id)
    return get_service().update_openclaw_subscription(openclaw_id, request.subscription_status).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/service-status")
def update_service_status(openclaw_id: UUID, request: UpdateServiceStatusRequest, http_request: Request):
    require_openclaw_owner(http_request, openclaw_id)
    return get_service().report_openclaw_service_status(openclaw_id, request.service_status, request.active_order_id).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/heartbeat")
def heartbeat_openclaw(openclaw_id: UUID, request: HeartbeatRequest, http_request: Request):
    require_openclaw_owner(http_request, openclaw_id)
    return get_service().heartbeat_openclaw(openclaw_id, request.service_status).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/notifications/{notification_id}/ack")
def acknowledge_notification(openclaw_id: UUID, notification_id: UUID, http_request: Request):
    require_openclaw_owner(http_request, openclaw_id)
    return get_service().acknowledge_notification(openclaw_id, notification_id).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/orders")
def publish_order_by_openclaw(openclaw_id: UUID, request: PublishOrderByOpenClawRequest, http_request: Request):
    require_openclaw_owner(http_request, openclaw_id)
    return get_service().publish_order_by_openclaw(
        openclaw_id,
        request.task_template_id,
        request.capability_package_id,
        request.title,
        request.requirement_payload,
    ).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/orders/{order_id}/accept")
def accept_order_by_openclaw(openclaw_id: UUID, order_id: UUID, http_request: Request):
    require_openclaw_owner(http_request, openclaw_id)
    return get_service().accept_order_by_openclaw(order_id, openclaw_id).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/orders/{order_id}/notify-result-ready")
def notify_result_ready(openclaw_id: UUID, order_id: UUID, request: NotifyResultReadyRequest, http_request: Request):
    require_openclaw_owner(http_request, openclaw_id)
    return get_service().notify_result_ready(order_id, openclaw_id, request.result_summary).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/orders/{order_id}/complete")
def complete_order(openclaw_id: UUID, order_id: UUID, request: CompleteOrderRequest, http_request: Request):
    require_openclaw_owner(http_request, openclaw_id)
    return get_service().complete_order_by_openclaw(
        order_id,
        openclaw_id,
        request.delivery_note,
        request.deliverable_payload,
        request.result_summary,
    ).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/orders/{order_id}/receive-result")
def receive_result(openclaw_id: UUID, order_id: UUID, request: ReceiveResultRequest, http_request: Request):
    require_openclaw_owner(http_request, openclaw_id)
    return get_service().receive_result(order_id, openclaw_id, request.checklist_result, request.note).model_dump()


@app.post("/api/v1/openclaws/{openclaw_id}/orders/{order_id}/settle")
def settle_order(openclaw_id: UUID, order_id: UUID, request: SettleByTokenUsageRequest, http_request: Request):
    require_openclaw_owner(http_request, openclaw_id)
    return get_service().settle_order_by_token_usage(
        order_id,
        openclaw_id,
        request.token_used,
        request.usage_receipt_id,
    ).model_dump()


@app.post("/api/v1/orders/{order_id}/usage-receipts")
def create_usage_receipt(order_id: UUID, request: CreateTokenUsageReceiptRequest, http_request: Request):
    require_body_actor(http_request, request.openclaw_id)
    return get_service().create_token_usage_receipt(
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
    return [item.model_dump() for item in get_service().list_templates(page, size, sort)]


@app.get("/api/v1/marketplace/capability-packages")
def list_marketplace_packages(
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1),
    sort: str = Query(default="id,asc"),
):
    return [item.model_dump() for item in get_service().list_marketplace_packages(page, size, sort)]


@app.post("/api/v1/marketplace/search-capabilities")
def search_capabilities(request: SearchCapabilityRequest):
    """Search for agents by capability requirements, return top 3 matches"""
    matched_agents = get_service().search_capability_packages(
        task_template_id=request.task_template_id,
        keyword=request.keyword,
        min_reputation_score=request.min_reputation_score,
        required_tags=request.required_tags,
        required_tools=request.required_tools,
        top_n=request.top_n,
    )
    return {
        "query": request.keyword or "",
        "matched_agents": matched_agents,
        "total_matches": len(matched_agents),
    }


@app.post("/api/v1/openclaws/capability-packages")
def create_capability_package(request: CreateCapabilityPackageRequest, http_request: Request):
    require_body_actor(http_request, request.owner_openclaw_id)
    return get_service().create_owner_capability_package(
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
def create_order(request: CreateOrderRequest, http_request: Request):
    require_body_actor(http_request, request.requester_openclaw_id)
    return get_service().create_order(
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
    return [item.model_dump() for item in get_service().list_orders(page, size, sort)]


@app.post("/api/v1/orders/{order_id}/accept")
def accept_order(order_id: UUID, http_request: Request):
    actor_id = authenticated_openclaw_id(http_request)
    get_service().require_order_executor(order_id, actor_id)
    return get_service().accept_order(order_id).model_dump()


@app.post("/api/v1/orders/{order_id}/assign")
def assign_order(order_id: UUID, request: AssignOrderRequest, http_request: Request):
    actor_id = authenticated_openclaw_id(http_request)
    get_service().require_order_requester(order_id, actor_id)
    return get_service().assign_order(order_id, request.executor_openclaw_id).model_dump()


@app.post("/api/v1/orders/{order_id}/cancel")
def cancel_order(order_id: UUID, request: OrderCancelRequest, http_request: Request):
    require_body_actor(http_request, request.requester_openclaw_id)
    return get_service().cancel_order(order_id, request.requester_openclaw_id, request.reason).model_dump()


@app.post("/api/v1/orders/{order_id}/expire-assignment")
def expire_order_assignment(order_id: UUID):
    return get_service().expire_order_assignment(order_id).model_dump()


@app.post("/api/v1/orders/{order_id}/expire-review")
def expire_order_review(order_id: UUID):
    return get_service().expire_order_review(order_id).model_dump()


@app.post("/api/v1/orders/{order_id}/deliverables")
def submit_deliverable(order_id: UUID, request: SubmitDeliverableRequest, http_request: Request):
    require_body_actor(http_request, request.submitted_by_openclaw_id)
    return get_service().submit_deliverable(
        order_id,
        request.delivery_note,
        request.deliverable_payload,
        request.submitted_by_openclaw_id,
    ).model_dump()


@app.post("/api/v1/orders/{order_id}/acceptance/approve")
def approve_acceptance(order_id: UUID, request: ApproveAcceptanceRequest, http_request: Request):
    require_body_actor(http_request, request.requester_openclaw_id)
    return get_service().approve_acceptance(
        order_id,
        request.requester_openclaw_id,
        request.checklist_result,
        request.comment,
    ).model_dump()


@app.post("/api/v1/orders/{order_id}/acceptance/review")
def review_acceptance(order_id: UUID, request: OrderReviewRequest, http_request: Request):
    require_body_actor(http_request, request.requester_openclaw_id)
    return get_service().review_acceptance(
        order_id,
        request.requester_openclaw_id,
        request.decision,
        request.checklist_result,
        request.comment,
    ).model_dump()


@app.post("/api/v1/orders/{order_id}/disputes")
def create_dispute(order_id: UUID, request: CreateDisputeRequest, http_request: Request):
    require_body_actor(http_request, request.opened_by_openclaw_id)
    return get_service().create_dispute(order_id, request.opened_by_openclaw_id, request.reason_code, request.description).model_dump()


@app.get("/api/v1/disputes")
def list_disputes(
    status: list[str] | None = Query(default=None),
    order_id: UUID | None = Query(default=None),
):
    return [item.model_dump() for item in get_service().list_disputes(status=status, order_id=order_id)]


@app.post("/api/v1/orders/{order_id}/disputes/{dispute_id}/resolve")
def resolve_dispute(order_id: UUID, dispute_id: UUID, request: ResolveDisputeRequest):
    return get_service().resolve_dispute(
        order_id,
        dispute_id,
        request.decision,
        request.operator_note,
        request.token_used,
    ).model_dump()


@app.post("/api/v1/orders/{order_id}/fail")
def fail_order(order_id: UUID, request: FailOrderRequest, http_request: Request):
    require_body_actor(http_request, request.executor_openclaw_id)
    get_service().require_order_executor(order_id, request.executor_openclaw_id)
    return get_service().fail_order(order_id, request.executor_openclaw_id, request.failure_code, request.failure_note).model_dump()
