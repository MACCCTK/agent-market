from __future__ import annotations

import base64
import hmac
import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Callable
from urllib import error as url_error
from urllib import request as url_request
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - dependency should be installed in runtime
    psycopg = None
    dict_row = None

from .errors import ApiError
from .schemas import (
    CapabilityPackageView,
    DeliverableView,
    DisputeView,
    HeartbeatView,
    NotificationView,
    OpenClawProfileView,
    OpenClawView,
    OrderView,
    SettlementFeeView,
    TaskTemplateView,
    TokenUsageReceiptView,
    UserView,
)


@dataclass(frozen=True)
class AuthView:
    access_token: str
    token_type: str
    user: UserView


class MarketplaceService:
    ALLOWED_ROLES = {"openclaw", "admin"}
    OPENCLAW_SUBSCRIPTION_STATUSES = {"subscribed", "unsubscribed"}
    OPENCLAW_SERVICE_STATUSES = {"available", "busy", "offline", "paused"}
    NOTIFICATION_ACKABLE_STATUSES = {"pending", "sent", "failed"}
    AUTO_ASSIGNMENT_RECOVERABLE_CODES = {
        "OPENCLAW_NONE_AVAILABLE",
        "OPENCLAW_NOT_AVAILABLE",
        "OPENCLAW_NOT_SUBSCRIBED",
    }

    TASK_HIRE_FEES = {
        "research_brief": Decimal("1.00"),
        "content_draft": Decimal("2.00"),
        "code_fix_small_automation": Decimal("3.00"),
        "data_cleanup_analysis": Decimal("4.00"),
        "workflow_setup": Decimal("5.00"),
    }

    def __init__(self, db_url: str | None = None, usage_receipt_secret: str | None = None):
        self.db_url = (db_url or "").strip()
        if not (self.db_url.startswith("postgresql://") or self.db_url.startswith("postgres://")):
            raise ApiError(
                "PERSISTENCE_ERROR",
                500,
                "MARKETPLACE_DB_URL must be a PostgreSQL URL (postgresql:// or postgres://)",
            )
        if psycopg is None:
            raise ApiError("PERSISTENCE_ERROR", 500, "psycopg is required for PostgreSQL. Install dependencies first.")

        self.templates: dict[int, TaskTemplateView] = {}
        self.capability_packages: dict[int, CapabilityPackageView] = {}
        self.orders: dict[int, OrderView] = {}
        self.deliverables: dict[int, list[DeliverableView]] = {}
        self.disputes: dict[int, list[DisputeView]] = {}
        self.users: dict[int, UserView] = {}
        self.email_to_user_id: dict[str, int] = {}
        self.user_password_hashes: dict[int, str] = {}
        self.openclaws: dict[int, OpenClawView] = {}
        self.openclaw_profiles: dict[int, OpenClawProfileView] = {}
        self.notifications: dict[int, NotificationView] = {}
        self.settlement_fees_by_order_id: dict[int, SettlementFeeView] = {}
        self.usage_receipts: dict[int, TokenUsageReceiptView] = {}
        self.usage_receipt_secret = (usage_receipt_secret or "dev-only-receipt-secret").strip()

        self.template_seq = 1
        self.package_seq = 1
        self.order_seq = 1
        self.deliverable_seq = 1
        self.dispute_seq = 1
        self.user_seq = 1
        self.openclaw_seq = 1
        self.notification_seq = 1
        self.usage_receipt_seq = 1

        self._ensure_tables()
        self._seed_templates()
        self._load_runtime_from_db()

    def register(self, email: str, password: str, display_name: str, roles: list[str] | None, client_type: str | None) -> AuthView:
        normalized_email = email.strip().lower()
        if normalized_email in self.email_to_user_id:
            raise ApiError("AUTH_EMAIL_EXISTS", 409, "Email already exists")

        normalized_roles = self._normalize_roles(roles)
        if (client_type or "").strip().lower() == "openclaw" and "openclaw" not in normalized_roles:
            normalized_roles = [*normalized_roles, "openclaw"]

        now = self._now_iso()
        user = UserView(
            id=self.user_seq,
            email=normalized_email,
            display_name=display_name,
            status="active",
            roles=normalized_roles,
            created_at=now,
            updated_at=now,
        )
        self.users[user.id] = user
        self.email_to_user_id[user.email] = user.id
        self.user_password_hashes[user.id] = self._hash(password)
        self.user_seq += 1

        return AuthView(access_token=self._generate_token(user), token_type="Bearer", user=user)

    def login(self, email: str, password: str, as_role: str | None, client_type: str | None) -> AuthView:
        user_id = self.email_to_user_id.get(email.strip().lower())
        if user_id is None:
            raise ApiError("AUTH_INVALID_CREDENTIALS", 401, "Invalid email or password")

        if self.user_password_hashes.get(user_id) != self._hash(password):
            raise ApiError("AUTH_INVALID_CREDENTIALS", 401, "Invalid email or password")

        user = self.users[user_id]
        if as_role and as_role.lower() not in [r.lower() for r in user.roles]:
            raise ApiError("AUTH_ROLE_DENIED", 403, "User does not have requested role")

        if (client_type or "").strip().lower() == "openclaw" and "openclaw" not in [r.lower() for r in user.roles]:
            raise ApiError("AUTH_ROLE_DENIED", 403, "OpenClaw access requires openclaw role")

        return AuthView(access_token=self._generate_token(user), token_type="Bearer", user=user)

    def list_openclaws(self) -> list[OpenClawView]:
        return list(self.openclaws.values())

    def list_notifications(self, openclaw_id: int) -> list[NotificationView]:
        self._require_openclaw(openclaw_id)
        return sorted(
            [n for n in self.notifications.values() if n.openclaw_id == openclaw_id],
            key=lambda n: (n.created_at, n.id),
            reverse=True,
        )

    def register_openclaw(
        self,
        openclaw_id: int | None,
        name: str,
        capacity_per_week: int,
        service_config: dict[str, Any],
        subscription_status: str,
        service_status: str,
    ) -> OpenClawProfileView:
        real_id = openclaw_id or self.openclaw_seq
        self.openclaw_seq = max(self.openclaw_seq, real_id + 1)

        normalized_subscription = self._normalize_subscription(subscription_status)
        normalized_service = self._normalize_service_status(service_status)
        now = self._now_iso()

        runtime = OpenClawView(
            id=real_id,
            name=name,
            subscription_status=normalized_subscription,
            service_status=normalized_service,
            active_order_id=None,
            updated_at=now,
        )
        profile = OpenClawProfileView(
            id=real_id,
            name=name,
            capacity_per_week=capacity_per_week,
            service_config=service_config or {},
            subscription_status=normalized_subscription,
            service_status=normalized_service,
            updated_at=now,
        )

        self.openclaws[real_id] = runtime
        self.openclaw_profiles[real_id] = profile
        self._persist_openclaw_runtime(runtime)
        self._persist_openclaw_profile(profile)
        return profile

    def search_openclaws(self, keyword: str | None, page: int, size: int) -> list[OpenClawView]:
        q = (keyword or "").strip().lower()
        matched = [
            o
            for o in self.openclaws.values()
            if not q
            or q in o.name.lower()
            or q in o.subscription_status.lower()
            or q in o.service_status.lower()
            or q in str(o.id)
        ]
        matched.sort(key=lambda x: x.id)
        return self._page(matched, page, size)

    def update_openclaw_subscription(self, openclaw_id: int, subscription_status: str) -> OpenClawView:
        current = self._require_openclaw(openclaw_id)
        status = self._normalize_subscription(subscription_status)
        service_status = "available" if status == "subscribed" else "offline"
        updated = current.model_copy(
            update={
                "subscription_status": status,
                "service_status": service_status,
                "active_order_id": None,
                "updated_at": self._now_iso(),
            }
        )
        self.openclaws[openclaw_id] = updated
        self._persist_openclaw_runtime(updated)
        return updated

    def report_openclaw_service_status(self, openclaw_id: int, service_status: str, active_order_id: int | None) -> OpenClawView:
        current = self._require_openclaw(openclaw_id)
        if current.subscription_status != "subscribed":
            raise ApiError("OPENCLAW_NOT_SUBSCRIBED", 409, "OpenClaw is not subscribed")

        updated = current.model_copy(
            update={
                "service_status": self._normalize_service_status(service_status),
                "active_order_id": active_order_id,
                "updated_at": self._now_iso(),
            }
        )
        self.openclaws[openclaw_id] = updated
        self._persist_openclaw_runtime(updated)
        return updated

    def heartbeat_openclaw(self, openclaw_id: int, service_status: str) -> HeartbeatView:
        current = self._require_openclaw(openclaw_id)
        normalized_status = self._normalize_service_status(service_status)
        assigned_order: OrderView | None = None
        active_order_id = current.active_order_id

        if normalized_status == "available" and current.active_order_id is None and current.subscription_status == "subscribed":
            candidate_runtime = current.model_copy(
                update={
                    "service_status": normalized_status,
                    "active_order_id": active_order_id,
                    "updated_at": self._now_iso(),
                }
            )
            self.openclaws[openclaw_id] = candidate_runtime
            try:
                pending = self._find_pending_order_for_heartbeat(openclaw_id)
                if pending is not None:
                    assigned_order = self.assign_order(pending.id, openclaw_id)
                    active_order_id = assigned_order.id
                    normalized_status = "busy"
                current = candidate_runtime
            except Exception:
                self.openclaws[openclaw_id] = current
                raise

        updated = current.model_copy(
            update={
                "service_status": normalized_status,
                "active_order_id": active_order_id,
                "updated_at": self._now_iso(),
            }
        )
        self.openclaws[openclaw_id] = updated
        self._persist_openclaw_runtime(updated)
        return HeartbeatView(
            openclaw_id=openclaw_id,
            service_status=updated.service_status,
            active_order_id=updated.active_order_id,
            assigned_order=assigned_order,
            checked_at=self._now_iso(),
        )

    def acknowledge_notification(self, openclaw_id: int, notification_id: int) -> NotificationView:
        self._require_openclaw(openclaw_id)
        notification = self.notifications.get(notification_id)
        if notification is None:
            raise ApiError("NOTIFICATION_NOT_FOUND", 404, "Notification not found")
        if notification.openclaw_id != openclaw_id:
            raise ApiError("NOTIFICATION_OWNER_MISMATCH", 409, "Notification does not belong to this OpenClaw")
        if notification.status not in self.NOTIFICATION_ACKABLE_STATUSES:
            return notification

        updated = notification.model_copy(
            update={
                "status": "acked",
                "acked_at": self._now_iso(),
                "updated_at": self._now_iso(),
            }
        )
        self.notifications[notification_id] = updated
        self._persist_notification(updated)
        self._persist_result_event(updated.order_id, openclaw_id, "task_assignment_notification_acked", {"notification_id": updated.id})
        return updated

    def publish_order_by_openclaw(
        self,
        openclaw_id: int,
        task_template_id: int,
        capability_package_id: int | None,
        title: str,
        requirement_payload: dict[str, Any],
    ) -> OrderView:
        openclaw = self._require_openclaw(openclaw_id)
        if openclaw.subscription_status != "subscribed":
            raise ApiError("OPENCLAW_NOT_SUBSCRIBED", 409, "OpenClaw is not subscribed")
        return self.create_order(openclaw_id, task_template_id, capability_package_id, title, requirement_payload)

    def accept_order_by_openclaw(self, order_id: int, openclaw_id: int) -> OrderView:
        self._require_openclaw(openclaw_id)
        return self._accept_order(order_id, openclaw_id)

    def complete_order_by_openclaw(
        self,
        order_id: int,
        openclaw_id: int,
        delivery_note: str,
        deliverable_payload: dict[str, Any],
        result_summary: dict[str, Any],
    ) -> OrderView:
        if not delivery_note.strip():
            raise ApiError("DELIVERY_NOTE_REQUIRED", 400, "deliveryNote is required")
        if not result_summary:
            raise ApiError("RESULT_SUMMARY_REQUIRED", 400, "resultSummary is required")

        self.submit_deliverable(order_id, delivery_note, deliverable_payload, openclaw_id)
        return self.notify_result_ready(order_id, openclaw_id, result_summary)

    def notify_result_ready(self, order_id: int, executor_openclaw_id: int, result_summary: dict[str, Any]) -> OrderView:
        order = self._require_order(order_id)
        if order.executor_openclaw_id != executor_openclaw_id:
            raise ApiError("ORDER_EXECUTOR_MISMATCH", 409, "Order executor mismatch")
        if order.status not in {"delivered", "in_progress", "accepted"}:
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order cannot notify result in current status")

        updated = order.model_copy(update={"status": "result_ready", "updated_at": self._now_iso()})
        self.orders[order_id] = updated
        self._persist_order_snapshot(updated)
        self._persist_result_event(order_id, executor_openclaw_id, "result_ready_notified", result_summary)
        return updated

    def receive_result(self, order_id: int, requester_openclaw_id: int, checklist_result: dict[str, Any], note: str | None) -> OrderView:
        return self.approve_acceptance(order_id, requester_openclaw_id, checklist_result, note)

    def settle_order_by_token_usage(
        self,
        order_id: int,
        openclaw_id: int,
        token_used: int | None,
        usage_receipt_id: int | None = None,
    ) -> SettlementFeeView:
        self._require_openclaw(openclaw_id)
        order = self._require_order(order_id)

        if order.executor_openclaw_id != openclaw_id:
            raise ApiError("ORDER_OWNER_MISMATCH", 409, "Order is not owned by this OpenClaw")
        if order.status not in {"delivered", "approved", "in_progress"}:
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order cannot be settled in current status")

        resolved_token_used: int | None = None
        if usage_receipt_id is not None:
            receipt = self.usage_receipts.get(usage_receipt_id)
            if receipt is None:
                raise ApiError("USAGE_RECEIPT_NOT_FOUND", 404, "Usage receipt not found")
            if receipt.order_id != order_id:
                raise ApiError("USAGE_RECEIPT_ORDER_MISMATCH", 409, "Usage receipt does not belong to this order")
            if receipt.openclaw_id != openclaw_id:
                raise ApiError("USAGE_RECEIPT_OWNER_MISMATCH", 409, "Usage receipt does not belong to this OpenClaw")
            expected_sig = self._sign_receipt_commitment(receipt.receipt_commitment)
            if not hmac.compare_digest(expected_sig, receipt.signature):
                raise ApiError("USAGE_RECEIPT_INVALID_SIGNATURE", 409, "Usage receipt signature mismatch")
            resolved_token_used = receipt.total_tokens

        if token_used is not None:
            if token_used < 0:
                raise ApiError("TOKEN_USED_INVALID", 400, "tokenUsed must be >= 0")
            if resolved_token_used is not None and token_used != resolved_token_used:
                raise ApiError("TOKEN_USED_MISMATCH", 409, "tokenUsed does not match usage receipt")
            resolved_token_used = token_used

        if resolved_token_used is None:
            raise ApiError("TOKEN_USAGE_REQUIRED", 400, "Either tokenUsed or usageReceiptId is required")

        hire_fee = order.quoted_price
        token_fee = (Decimal(resolved_token_used) / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_fee = hire_fee + token_fee

        settlement = SettlementFeeView(
            order_id=order_id,
            openclaw_id=openclaw_id,
            hire_fee=hire_fee,
            token_used=resolved_token_used,
            token_fee=token_fee,
            total_fee=total_fee,
            currency=order.currency,
            settled_at=self._now_iso(),
        )
        self.settlement_fees_by_order_id[order_id] = settlement

        updated_order = order.model_copy(
            update={"status": "settled", "completed_at": self._now_iso(), "updated_at": self._now_iso()}
        )
        self.orders[order_id] = updated_order
        self._persist_order_snapshot(updated_order)

        openclaw = self._require_openclaw(openclaw_id)
        runtime = openclaw.model_copy(
            update={"service_status": "available", "active_order_id": None, "updated_at": self._now_iso()}
        )
        self.openclaws[openclaw_id] = runtime
        self._persist_openclaw_runtime(runtime)
        return settlement

    def create_token_usage_receipt(
        self,
        order_id: int,
        openclaw_id: int,
        provider: str,
        provider_request_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        measured_at: str | None,
    ) -> TokenUsageReceiptView:
        if prompt_tokens < 0 or completion_tokens < 0:
            raise ApiError("TOKEN_USED_INVALID", 400, "promptTokens and completionTokens must be >= 0")

        order = self._require_order(order_id)
        if order.executor_openclaw_id != openclaw_id:
            raise ApiError("ORDER_OWNER_MISMATCH", 409, "Order is not owned by this OpenClaw")
        if order.status not in {"accepted", "in_progress", "delivered", "result_ready", "approved"}:
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order cannot attach usage receipt in current status")

        provider_norm = (provider or "").strip()
        provider_request_norm = (provider_request_id or "").strip()
        model_norm = (model or "").strip()
        if not provider_norm:
            raise ApiError("USAGE_PROVIDER_REQUIRED", 400, "provider is required")
        if not provider_request_norm:
            raise ApiError("USAGE_PROVIDER_REQUEST_ID_REQUIRED", 400, "providerRequestId is required")
        if not model_norm:
            raise ApiError("USAGE_MODEL_REQUIRED", 400, "model is required")

        total_tokens = prompt_tokens + completion_tokens
        measured_at_final = measured_at or self._now_iso()
        commitment = self._build_receipt_commitment(
            order_id,
            openclaw_id,
            provider_norm,
            provider_request_norm,
            model_norm,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            measured_at_final,
        )
        signature = self._sign_receipt_commitment(commitment)
        created_at = self._now_iso()
        view = TokenUsageReceiptView(
            id=self.usage_receipt_seq,
            order_id=order_id,
            openclaw_id=openclaw_id,
            provider=provider_norm,
            provider_request_id=provider_request_norm,
            model=model_norm,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            measured_at=measured_at_final,
            receipt_commitment=commitment,
            signature=signature,
            created_at=created_at,
        )
        self.usage_receipts[view.id] = view
        self.usage_receipt_seq += 1
        self._persist_usage_receipt(view)
        return view

    def list_templates(self, page: int, size: int, sort: str) -> list[TaskTemplateView]:
        values = sorted(self.templates.values(), key=lambda x: x.id, reverse=sort.lower().endswith(",desc"))
        return self._page(values, page, size)

    def list_marketplace_packages(self, page: int, size: int, sort: str) -> list[CapabilityPackageView]:
        active = [p for p in self.capability_packages.values() if p.status.lower() == "active"]
        active.sort(key=lambda x: x.id, reverse=sort.lower().endswith(",desc"))
        return self._page(active, page, size)

    def create_owner_capability_package(
        self,
        owner_openclaw_id: int,
        title: str,
        summary: str,
        task_template_id: int,
        sample_deliverables: dict[str, Any] | None,
        price_min: Decimal | None,
        price_max: Decimal | None,
        capacity_per_week: int,
        status: str,
    ) -> CapabilityPackageView:
        if task_template_id not in self.templates:
            raise ApiError("TASK_TEMPLATE_NOT_FOUND", 404, "Task template not found")
        if price_min is not None and price_max is not None and price_min > price_max:
            raise ApiError("PRICE_RANGE_INVALID", 400, "priceMin cannot be greater than priceMax")

        now = self._now_iso()
        view = CapabilityPackageView(
            id=self.package_seq,
            owner_openclaw_id=owner_openclaw_id,
            title=title,
            summary=summary,
            task_template_id=task_template_id,
            sample_deliverables=sample_deliverables or {},
            price_min=price_min,
            price_max=price_max,
            capacity_per_week=capacity_per_week,
            status=status,
            created_at=now,
            updated_at=now,
        )
        self.capability_packages[view.id] = view
        self.package_seq += 1
        return view

    def create_order(
        self,
        requester_openclaw_id: int,
        task_template_id: int,
        capability_package_id: int | None,
        title: str,
        requirement_payload: dict[str, Any],
    ) -> OrderView:
        self._require_openclaw(requester_openclaw_id)
        template = self.templates.get(task_template_id)
        if template is None:
            raise ApiError("TASK_TEMPLATE_NOT_FOUND", 404, "Task template not found")

        executor_openclaw_id: int | None = None
        if capability_package_id is not None:
            pkg = self.capability_packages.get(capability_package_id)
            if pkg is None:
                raise ApiError("CAPABILITY_PACKAGE_NOT_FOUND", 404, "Capability package not found")
            executor_openclaw_id = pkg.owner_openclaw_id

        now = self._now_iso()
        view = OrderView(
            id=self.order_seq,
            order_no=f"OC{self.order_seq:08d}",
            requester_openclaw_id=requester_openclaw_id,
            executor_openclaw_id=executor_openclaw_id,
            task_template_id=task_template_id,
            capability_package_id=capability_package_id,
            title=title,
            status="created",
            quoted_price=self._resolve_hire_fee_by_task_type(template.task_type),
            currency="USD",
            sla_hours=template.sla_hours,
            requirement_payload=requirement_payload or {},
            accepted_at=None,
            delivered_at=None,
            completed_at=None,
            cancelled_at=None,
            created_at=now,
            updated_at=now,
        )

        self.orders[view.id] = view
        self._persist_order_snapshot(view)
        self.order_seq += 1

        try:
            return self.assign_order(view.id, executor_openclaw_id)
        except ApiError as ex:
            if ex.code in self.AUTO_ASSIGNMENT_RECOVERABLE_CODES:
                return self._require_order(view.id)
            raise

    def list_orders(self, page: int, size: int, sort: str) -> list[OrderView]:
        values = sorted(self.orders.values(), key=lambda x: x.id, reverse=sort.lower().endswith(",desc"))
        return self._page(values, page, size)

    def accept_order(self, order_id: int) -> OrderView:
        order = self._require_order(order_id)
        if order.status not in {"created", "submitted"}:
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order cannot be accepted in current status")

        updated = order.model_copy(
            update={
                "status": "accepted",
                "accepted_at": self._now_iso(),
                "updated_at": self._now_iso(),
            }
        )
        self.orders[order_id] = updated
        self._persist_order_snapshot(updated)
        return updated

    def assign_order(self, order_id: int, executor_openclaw_id: int | None) -> OrderView:
        order = self._require_order(order_id)
        if order.status not in {"created", "submitted"}:
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order cannot be assigned in current status")

        executor = (
            self._find_available_executor(order.requester_openclaw_id)
            if executor_openclaw_id is None
            else self._require_assignable_executor(executor_openclaw_id, order.requester_openclaw_id)
        )

        updated = order.model_copy(
            update={
                "executor_openclaw_id": executor.id,
                "status": "accepted",
                "accepted_at": self._now_iso(),
                "updated_at": self._now_iso(),
            }
        )
        self.orders[order_id] = updated
        self._persist_order_snapshot(updated)

        runtime = executor.model_copy(
            update={"service_status": "busy", "active_order_id": order_id, "updated_at": self._now_iso()}
        )
        self.openclaws[executor.id] = runtime
        self._persist_openclaw_runtime(runtime)
        self._create_assignment_notification(executor.id, updated)
        return updated

    def submit_deliverable(self, order_id: int, delivery_note: str, payload: dict[str, Any], submitted_by: int) -> DeliverableView:
        order = self._require_order(order_id)
        if order.status not in {"accepted", "in_progress"}:
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order cannot be delivered in current status")
        if order.executor_openclaw_id != submitted_by:
            raise ApiError("ORDER_EXECUTOR_MISMATCH", 409, "Only assigned executor OpenClaw can submit deliverable")

        versions = self.deliverables.setdefault(order_id, [])
        deliverable = DeliverableView(
            id=self.deliverable_seq,
            order_id=order_id,
            version_no=len(versions) + 1,
            delivery_note=delivery_note,
            deliverable_payload=payload or {},
            submitted_by=submitted_by,
            submitted_at=self._now_iso(),
        )
        versions.append(deliverable)
        self.deliverable_seq += 1

        updated = order.model_copy(update={"status": "delivered", "delivered_at": self._now_iso(), "updated_at": self._now_iso()})
        self.orders[order_id] = updated
        self._persist_order_snapshot(updated)
        self._persist_result_event(order_id, submitted_by, "result_delivered", payload or {})
        return deliverable

    def approve_acceptance(
        self,
        order_id: int,
        requester_openclaw_id: int,
        checklist_result: dict[str, Any],
        comment: str | None,
    ) -> OrderView:
        order = self._require_order(order_id)
        if order.status not in {"delivered", "result_ready"}:
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order cannot be approved in current status")
        if order.requester_openclaw_id != requester_openclaw_id:
            raise ApiError("ORDER_REQUESTER_MISMATCH", 409, "Only requester OpenClaw can approve result")
        if not checklist_result:
            raise ApiError("CHECKLIST_REQUIRED", 400, "checklistResult is required")

        updated = order.model_copy(update={"status": "approved", "completed_at": self._now_iso(), "updated_at": self._now_iso()})
        self.orders[order_id] = updated
        self._persist_order_snapshot(updated)
        self._persist_result_event(
            order_id,
            requester_openclaw_id,
            "result_received",
            {"checklist": checklist_result, "note": comment or ""},
        )
        return updated

    def create_dispute(self, order_id: int, opened_by_openclaw_id: int, reason_code: str, description: str) -> DisputeView:
        order = self._require_order(order_id)
        if order.status in {"settled", "refunded", "cancelled"}:
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order cannot be disputed in current status")

        dispute = DisputeView(
            id=self.dispute_seq,
            order_id=order_id,
            opened_by=opened_by_openclaw_id,
            reason_code=reason_code,
            description=description,
            status="open",
            created_at=self._now_iso(),
        )
        self.disputes.setdefault(order_id, []).append(dispute)
        self.dispute_seq += 1

        updated = order.model_copy(update={"status": "disputed", "updated_at": self._now_iso()})
        self.orders[order_id] = updated
        self._persist_order_snapshot(updated)
        self._persist_result_event(order_id, opened_by_openclaw_id, "order_disputed", {"reason_code": reason_code, "description": description})
        return dispute

    def _accept_order(self, order_id: int, openclaw_id: int) -> OrderView:
        order = self._require_order(order_id)
        if order.status not in {"created", "submitted"}:
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order cannot be accepted in current status")

        updated = order.model_copy(
            update={
                "executor_openclaw_id": openclaw_id,
                "status": "accepted",
                "accepted_at": self._now_iso(),
                "updated_at": self._now_iso(),
            }
        )
        self.orders[order_id] = updated
        self._persist_order_snapshot(updated)

        openclaw = self._require_openclaw(openclaw_id)
        runtime = openclaw.model_copy(update={"service_status": "busy", "active_order_id": order_id, "updated_at": self._now_iso()})
        self.openclaws[openclaw_id] = runtime
        self._persist_openclaw_runtime(runtime)
        return updated

    def _require_order(self, order_id: int) -> OrderView:
        order = self.orders.get(order_id)
        if order is None:
            raise ApiError("ORDER_NOT_FOUND", 404, "Order not found")
        return order

    def _require_openclaw(self, openclaw_id: int) -> OpenClawView:
        openclaw = self.openclaws.get(openclaw_id)
        if openclaw is None:
            raise ApiError("OPENCLAW_NOT_FOUND", 404, "OpenClaw not found")
        return openclaw

    def _require_assignable_executor(self, openclaw_id: int, requester_openclaw_id: int) -> OpenClawView:
        openclaw = self._require_openclaw(openclaw_id)
        if openclaw.id == requester_openclaw_id:
            raise ApiError("OPENCLAW_ASSIGNMENT_INVALID", 409, "Requester cannot be assigned as executor")
        if openclaw.subscription_status != "subscribed":
            raise ApiError("OPENCLAW_NOT_SUBSCRIBED", 409, "OpenClaw is not subscribed")
        if openclaw.service_status != "available":
            raise ApiError("OPENCLAW_NOT_AVAILABLE", 409, "OpenClaw is not available")
        return openclaw

    def _find_available_executor(self, requester_openclaw_id: int) -> OpenClawView:
        candidates = [
            o
            for o in self.openclaws.values()
            if o.id != requester_openclaw_id and o.subscription_status == "subscribed" and o.service_status == "available"
        ]
        if not candidates:
            raise ApiError("OPENCLAW_NONE_AVAILABLE", 409, "No available OpenClaw executor")
        return sorted(candidates, key=lambda x: x.id)[0]

    def _find_pending_order_for_heartbeat(self, executor_openclaw_id: int) -> OrderView | None:
        candidates = [
            o
            for o in self.orders.values()
            if o.status in {"created", "submitted"}
            and o.requester_openclaw_id != executor_openclaw_id
            and (o.executor_openclaw_id is None or o.executor_openclaw_id == executor_openclaw_id)
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda x: (x.created_at, x.id))[0]

    def _create_assignment_notification(self, openclaw_id: int, order: OrderView) -> NotificationView:
        profile = self.openclaw_profiles.get(openclaw_id)
        callback_url = (profile.service_config.get("callback_url") if profile else None) if profile else None
        payload = {
            "notification_type": "task_assigned",
            "order_id": order.id,
            "order_no": order.order_no,
            "executor_openclaw_id": openclaw_id,
            "requester_openclaw_id": order.requester_openclaw_id,
            "title": order.title,
        }
        notification = NotificationView(
            id=self.notification_seq,
            openclaw_id=openclaw_id,
            order_id=order.id,
            notification_type="task_assigned",
            status="pending",
            callback_url=callback_url,
            payload=payload,
            created_at=self._now_iso(),
            sent_at=None,
            acked_at=None,
            updated_at=self._now_iso(),
        )
        self.notifications[notification.id] = notification
        self.notification_seq += 1
        self._persist_notification(notification)

        dispatched = self._dispatch_notification(notification)
        self._persist_result_event(order.id, openclaw_id, f"task_assignment_notification_{dispatched.status}", {"notification_id": dispatched.id})
        return dispatched

    def _dispatch_notification(self, notification: NotificationView) -> NotificationView:
        callback_url = (notification.callback_url or "").strip()
        if not callback_url:
            return notification

        req = url_request.Request(
            callback_url,
            data=json.dumps(notification.payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with url_request.urlopen(req, timeout=2) as response:
                status = "sent" if 200 <= response.status < 300 else "failed"
        except (url_error.URLError, TimeoutError, ValueError):
            status = "failed"

        updated = notification.model_copy(
            update={
                "status": status,
                "sent_at": self._now_iso() if status == "sent" else None,
                "updated_at": self._now_iso(),
            }
        )
        self.notifications[updated.id] = updated
        self._persist_notification(updated)
        return updated

    def _normalize_subscription(self, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in self.OPENCLAW_SUBSCRIPTION_STATUSES:
            raise ApiError("OPENCLAW_SUBSCRIPTION_STATUS_INVALID", 400, "Unsupported subscription status")
        return normalized

    def _normalize_service_status(self, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in self.OPENCLAW_SERVICE_STATUSES:
            raise ApiError("OPENCLAW_SERVICE_STATUS_INVALID", 400, "Unsupported service status")
        return normalized

    def _resolve_hire_fee_by_task_type(self, task_type: str) -> Decimal:
        fee = self.TASK_HIRE_FEES.get(task_type)
        if fee is None:
            raise ApiError("TASK_TYPE_UNSUPPORTED", 400, f"Unsupported task type: {task_type}")
        return fee

    def _build_receipt_commitment(
        self,
        order_id: int,
        openclaw_id: int,
        provider: str,
        provider_request_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        measured_at: str,
    ) -> str:
        payload = {
            "order_id": order_id,
            "openclaw_id": openclaw_id,
            "provider": provider,
            "provider_request_id": provider_request_id,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "measured_at": measured_at,
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _sign_receipt_commitment(self, commitment: str) -> str:
        return hmac.new(
            self.usage_receipt_secret.encode("utf-8"),
            commitment.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _page(items: list[Any], page: int, size: int) -> list[Any]:
        start = max(page, 0) * max(size, 1)
        end = start + max(size, 1)
        return items[start:end]

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    def _normalize_roles(self, roles: list[str] | None) -> list[str]:
        source = roles if roles else ["openclaw"]
        normalized: list[str] = []
        for role in source:
            value = role.strip().lower()
            if value not in self.ALLOWED_ROLES:
                raise ApiError("AUTH_ROLE_INVALID", 400, f"Unsupported role: {role}")
            if value not in normalized:
                normalized.append(value)
        return normalized

    def _generate_token(self, user: UserView) -> str:
        raw = f"{user.id}:{user.email}:{uuid.uuid4()}"
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8").rstrip("=")

    @staticmethod
    def _hash(plain: str) -> str:
        return hashlib.sha256(plain.encode("utf-8")).hexdigest()

    def _connect(self):
        candidate_url = self.db_url
        for _ in range(5):
            try:
                return psycopg.connect(candidate_url, row_factory=dict_row)
            except psycopg.ProgrammingError as ex:
                match = re.search(r'invalid URI query parameter: "([^"]+)"', str(ex))
                if not match:
                    raise
                bad_param = match.group(1)
                next_url = self._strip_query_param(candidate_url, bad_param)
                if next_url == candidate_url:
                    raise
                candidate_url = next_url
        raise ApiError("PERSISTENCE_ERROR", 500, "Failed to parse PostgreSQL URI query parameters")

    @staticmethod
    def _strip_query_param(url: str, param_name: str) -> str:
        parts = urlsplit(url)
        pairs = parse_qsl(parts.query, keep_blank_values=True)
        filtered = [(k, v) for k, v in pairs if k != param_name]
        new_query = urlencode(filtered, doseq=True)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

    def _ensure_tables(self) -> None:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS openclaws (
                id BIGINT PRIMARY KEY,
                name TEXT NOT NULL,
                subscription_status TEXT NOT NULL,
                service_status TEXT NOT NULL,
                active_order_id BIGINT,
                token_rate_per_100 NUMERIC NOT NULL DEFAULT 1.00,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS openclaw_profiles (
                id BIGINT PRIMARY KEY,
                name TEXT NOT NULL,
                capacity_per_week INTEGER NOT NULL,
                service_config JSONB NOT NULL,
                subscription_status TEXT NOT NULL,
                service_status TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS openclaw_task_orders (
                id BIGINT PRIMARY KEY,
                order_no TEXT NOT NULL,
                requester_openclaw_id BIGINT NOT NULL,
                executor_openclaw_id BIGINT,
                task_template_id BIGINT NOT NULL,
                capability_package_id BIGINT,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                quoted_price NUMERIC NOT NULL,
                currency TEXT NOT NULL,
                sla_hours INTEGER NOT NULL,
                requirement_payload JSONB NOT NULL,
                accepted_at TEXT,
                delivered_at TEXT,
                completed_at TEXT,
                cancelled_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS openclaw_task_events (
                id BIGSERIAL PRIMARY KEY,
                order_id BIGINT NOT NULL,
                actor_openclaw_id BIGINT NOT NULL,
                event_type TEXT NOT NULL,
                event_payload JSONB NOT NULL,
                created_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS openclaw_notifications (
                id BIGINT PRIMARY KEY,
                openclaw_id BIGINT NOT NULL,
                order_id BIGINT NOT NULL,
                notification_type TEXT NOT NULL,
                status TEXT NOT NULL,
                callback_url TEXT,
                payload JSONB NOT NULL,
                created_at TEXT NOT NULL,
                sent_at TEXT,
                acked_at TEXT,
                updated_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS openclaw_usage_receipts (
                id BIGINT PRIMARY KEY,
                order_id BIGINT NOT NULL,
                openclaw_id BIGINT NOT NULL,
                provider TEXT NOT NULL,
                provider_request_id TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                measured_at TEXT NOT NULL,
                receipt_commitment TEXT NOT NULL,
                signature TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """,
        ]
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    for sql in statements:
                        cur.execute(sql)
                conn.commit()
            return
        except Exception as ex:
            raise ApiError("PERSISTENCE_ERROR", 500, f"Failed to initialize PostgreSQL tables: {ex}") from ex

    def _seed_templates(self) -> None:
        if self.templates:
            return

        def add(code: str, name: str, task_type: str, description: str, base_price: str, sla_hours: int) -> None:
            template = TaskTemplateView(
                id=self.template_seq,
                code=code,
                name=name,
                task_type=task_type,
                description=description,
                input_schema={"fields": []},
                output_schema={"format": "json"},
                acceptance_schema={"checklist": []},
                pricing_model="fixed",
                base_price=Decimal(base_price),
                sla_hours=sla_hours,
                status="active",
            )
            self.templates[template.id] = template
            self.template_seq += 1

        add("research_brief_basic", "Research Brief", "research_brief", "Structured market and product research brief", "1.00", 48)
        add("content_draft_standard", "Content Draft", "content_draft", "Draft SEO/article/content assets", "2.00", 24)
        add(
            "code_fix_small_automation_basic",
            "Code Fix Small Automation",
            "code_fix_small_automation",
            "Small fix, script, or automation",
            "3.00",
            48,
        )
        add("data_cleanup_analysis_basic", "Data Cleanup Analysis", "data_cleanup_analysis", "Data cleaning and structured analysis", "4.00", 36)
        add("workflow_setup_basic", "Workflow Setup", "workflow_setup", "Set up reusable workflow with docs", "5.00", 72)

    def _load_runtime_from_db(self) -> None:
        with self._connect() as conn:
            for row in conn.execute("SELECT id, name, subscription_status, service_status, active_order_id, updated_at FROM openclaws ORDER BY id"):
                updated_at = row["updated_at"] or self._now_iso()
                self.openclaws[row["id"]] = OpenClawView(
                    id=row["id"],
                    name=row["name"],
                    subscription_status=row["subscription_status"],
                    service_status=row["service_status"],
                    active_order_id=row["active_order_id"],
                    updated_at=updated_at,
                )

            for row in conn.execute("SELECT id, name, capacity_per_week, service_config, subscription_status, service_status, updated_at FROM openclaw_profiles ORDER BY id"):
                self.openclaw_profiles[row["id"]] = OpenClawProfileView(
                    id=row["id"],
                    name=row["name"],
                    capacity_per_week=row["capacity_per_week"],
                    service_config=self._load_json(row["service_config"]),
                    subscription_status=row["subscription_status"],
                    service_status=row["service_status"],
                    updated_at=row["updated_at"],
                )

            for row in conn.execute(
                """
                SELECT id, order_no, requester_openclaw_id, executor_openclaw_id, task_template_id, capability_package_id,
                       title, status, quoted_price, currency, sla_hours, requirement_payload,
                       accepted_at, delivered_at, completed_at, cancelled_at, created_at, updated_at
                FROM openclaw_task_orders ORDER BY id
                """
            ):
                order = OrderView(
                    id=row["id"],
                    order_no=row["order_no"],
                    requester_openclaw_id=row["requester_openclaw_id"],
                    executor_openclaw_id=row["executor_openclaw_id"],
                    task_template_id=row["task_template_id"],
                    capability_package_id=row["capability_package_id"],
                    title=row["title"],
                    status=row["status"],
                    quoted_price=Decimal(str(row["quoted_price"])),
                    currency=row["currency"],
                    sla_hours=row["sla_hours"],
                    requirement_payload=self._load_json(row["requirement_payload"]),
                    accepted_at=row["accepted_at"],
                    delivered_at=row["delivered_at"],
                    completed_at=row["completed_at"],
                    cancelled_at=row["cancelled_at"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                self.orders[order.id] = order

            for row in conn.execute(
                "SELECT id, openclaw_id, order_id, notification_type, status, callback_url, payload, created_at, sent_at, acked_at, updated_at FROM openclaw_notifications ORDER BY id"
            ):
                notification = NotificationView(
                    id=row["id"],
                    openclaw_id=row["openclaw_id"],
                    order_id=row["order_id"],
                    notification_type=row["notification_type"],
                    status=row["status"],
                    callback_url=row["callback_url"],
                    payload=self._load_json(row["payload"]),
                    created_at=row["created_at"],
                    sent_at=row["sent_at"],
                    acked_at=row["acked_at"],
                    updated_at=row["updated_at"],
                )
                self.notifications[notification.id] = notification

            for row in conn.execute(
                """
                SELECT id, order_id, openclaw_id, provider, provider_request_id, model,
                       prompt_tokens, completion_tokens, total_tokens, measured_at,
                       receipt_commitment, signature, created_at
                FROM openclaw_usage_receipts ORDER BY id
                """
            ):
                receipt = TokenUsageReceiptView(
                    id=row["id"],
                    order_id=row["order_id"],
                    openclaw_id=row["openclaw_id"],
                    provider=row["provider"],
                    provider_request_id=row["provider_request_id"],
                    model=row["model"],
                    prompt_tokens=row["prompt_tokens"],
                    completion_tokens=row["completion_tokens"],
                    total_tokens=row["total_tokens"],
                    measured_at=row["measured_at"],
                    receipt_commitment=row["receipt_commitment"],
                    signature=row["signature"],
                    created_at=row["created_at"],
                )
                self.usage_receipts[receipt.id] = receipt

        if self.openclaws:
            self.openclaw_seq = max(self.openclaws.keys()) + 1
        if self.orders:
            self.order_seq = max(self.orders.keys()) + 1
        if self.notifications:
            self.notification_seq = max(self.notifications.keys()) + 1
        if self.usage_receipts:
            self.usage_receipt_seq = max(self.usage_receipts.keys()) + 1

    def _persist_openclaw_runtime(self, runtime: OpenClawView) -> None:
        self._execute(
            """
            INSERT INTO openclaws (id, name, subscription_status, service_status, active_order_id, token_rate_per_100, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1.00, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                subscription_status = excluded.subscription_status,
                service_status = excluded.service_status,
                active_order_id = excluded.active_order_id,
                updated_at = excluded.updated_at
            """,
            (
                runtime.id,
                runtime.name,
                runtime.subscription_status,
                runtime.service_status,
                runtime.active_order_id,
                runtime.updated_at,
                runtime.updated_at,
            ),
        )

    def _persist_openclaw_profile(self, profile: OpenClawProfileView) -> None:
        self._execute(
            """
            INSERT INTO openclaw_profiles (id, name, capacity_per_week, service_config, subscription_status, service_status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                capacity_per_week = excluded.capacity_per_week,
                service_config = excluded.service_config,
                subscription_status = excluded.subscription_status,
                service_status = excluded.service_status,
                updated_at = excluded.updated_at
            """,
            (
                profile.id,
                profile.name,
                profile.capacity_per_week,
                json.dumps(profile.service_config),
                profile.subscription_status,
                profile.service_status,
                profile.updated_at,
            ),
        )

    def _persist_order_snapshot(self, order: OrderView) -> None:
        self._execute(
            """
            INSERT INTO openclaw_task_orders (
                id, order_no, requester_openclaw_id, executor_openclaw_id, task_template_id, capability_package_id,
                title, status, quoted_price, currency, sla_hours, requirement_payload,
                accepted_at, delivered_at, completed_at, cancelled_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                requester_openclaw_id = excluded.requester_openclaw_id,
                executor_openclaw_id = excluded.executor_openclaw_id,
                task_template_id = excluded.task_template_id,
                capability_package_id = excluded.capability_package_id,
                title = excluded.title,
                status = excluded.status,
                quoted_price = excluded.quoted_price,
                currency = excluded.currency,
                sla_hours = excluded.sla_hours,
                requirement_payload = excluded.requirement_payload,
                accepted_at = excluded.accepted_at,
                delivered_at = excluded.delivered_at,
                completed_at = excluded.completed_at,
                cancelled_at = excluded.cancelled_at,
                updated_at = excluded.updated_at
            """,
            (
                order.id,
                order.order_no,
                order.requester_openclaw_id,
                order.executor_openclaw_id,
                order.task_template_id,
                order.capability_package_id,
                order.title,
                order.status,
                str(order.quoted_price),
                order.currency,
                order.sla_hours,
                json.dumps(order.requirement_payload),
                order.accepted_at,
                order.delivered_at,
                order.completed_at,
                order.cancelled_at,
                order.created_at,
                order.updated_at,
            ),
        )

    def _persist_result_event(self, order_id: int, actor_openclaw_id: int, event_type: str, payload: dict[str, Any]) -> None:
        self._execute(
            "INSERT INTO openclaw_task_events (order_id, actor_openclaw_id, event_type, event_payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (order_id, actor_openclaw_id, event_type, json.dumps(payload or {}), self._now_iso()),
        )

    def _persist_notification(self, notification: NotificationView) -> None:
        self._execute(
            """
            INSERT INTO openclaw_notifications (
                id, openclaw_id, order_id, notification_type, status, callback_url,
                payload, created_at, sent_at, acked_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                callback_url = excluded.callback_url,
                payload = excluded.payload,
                sent_at = excluded.sent_at,
                acked_at = excluded.acked_at,
                updated_at = excluded.updated_at
            """,
            (
                notification.id,
                notification.openclaw_id,
                notification.order_id,
                notification.notification_type,
                notification.status,
                notification.callback_url,
                json.dumps(notification.payload),
                notification.created_at,
                notification.sent_at,
                notification.acked_at,
                notification.updated_at,
            ),
        )

    def _persist_usage_receipt(self, receipt: TokenUsageReceiptView) -> None:
        self._execute(
            """
            INSERT INTO openclaw_usage_receipts (
                id, order_id, openclaw_id, provider, provider_request_id, model,
                prompt_tokens, completion_tokens, total_tokens, measured_at,
                receipt_commitment, signature, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                provider = excluded.provider,
                provider_request_id = excluded.provider_request_id,
                model = excluded.model,
                prompt_tokens = excluded.prompt_tokens,
                completion_tokens = excluded.completion_tokens,
                total_tokens = excluded.total_tokens,
                measured_at = excluded.measured_at,
                receipt_commitment = excluded.receipt_commitment,
                signature = excluded.signature,
                created_at = excluded.created_at
            """,
            (
                receipt.id,
                receipt.order_id,
                receipt.openclaw_id,
                receipt.provider,
                receipt.provider_request_id,
                receipt.model,
                receipt.prompt_tokens,
                receipt.completion_tokens,
                receipt.total_tokens,
                receipt.measured_at,
                receipt.receipt_commitment,
                receipt.signature,
                receipt.created_at,
            ),
        )

    def _execute(self, sql: str, params: tuple[Any, ...]) -> None:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(self._adapt_sql(sql), params)
                conn.commit()
        except Exception as ex:
            raise ApiError("PERSISTENCE_ERROR", 500, f"Persistence write failed: {ex}") from ex

    def _adapt_sql(self, sql: str) -> str:
        return sql.replace("?", "%s")

    @staticmethod
    def _load_json(raw: Any) -> dict[str, Any]:
        if not raw:
            return {}
        if isinstance(raw, dict):
            return raw
        try:
            value = json.loads(raw)
            return value if isinstance(value, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
