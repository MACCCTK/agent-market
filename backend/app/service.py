from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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
    NotificationAlertSummary,
    NotificationDeliveryMetrics,
    NotificationRetryProcessSummary,
    NotificationView,
    OpenClawCapabilityView,
    OpenClawDetail,
    OpenClawIdentityView,
    OpenClawProfileDetail,
    OpenClawProfileView,
    OpenClawReputationView,
    OpenClawRuntimeView,
    OpenClawView,
    OrderView,
    SettlementFeeView,
    TaskTemplateView,
    TokenUsageReceiptView,
)


@dataclass(frozen=True)
class AuthView:
    access_token: str
    token_type: str
    user: OpenClawIdentityView


class MarketplaceService:
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

        self.templates: dict[uuid.UUID, TaskTemplateView] = {}
        self.capability_packages: dict[uuid.UUID, CapabilityPackageView] = {}
        self.orders: dict[uuid.UUID, OrderView] = {}
        self.deliverables: dict[uuid.UUID, list[DeliverableView]] = {}
        self.disputes: dict[uuid.UUID, list[DisputeView]] = {}
        self.users: dict[uuid.UUID, OpenClawIdentityView] = {}
        self.email_to_user_id: dict[str, uuid.UUID] = {}
        self.user_password_hashes: dict[uuid.UUID, str] = {}
        self.openclaws: dict[uuid.UUID, OpenClawView] = {}
        self.openclaw_profiles: dict[uuid.UUID, OpenClawProfileView] = {}
        self.notifications: dict[uuid.UUID, NotificationView] = {}
        self.settlement_fees_by_order_id: dict[uuid.UUID, SettlementFeeView] = {}
        self.usage_receipts: dict[uuid.UUID, TokenUsageReceiptView] = {}
        self.usage_receipt_secret = (usage_receipt_secret or "dev-only-receipt-secret").strip()
        self._openclaws_has_identity_columns = False
        self._openclaw_profiles_has_modern_columns = False
        self._deadline_worker_stop_event = threading.Event()
        self._deadline_worker_thread: threading.Thread | None = None
        self._deadline_worker_interval_seconds = self._load_deadline_worker_interval_seconds()
        self._notification_retry_worker_stop_event = threading.Event()
        self._notification_retry_worker_thread: threading.Thread | None = None
        self._notification_retry_interval_seconds = self._load_notification_retry_interval_seconds()
        self._notification_retry_backoff_seconds = self._load_notification_retry_backoff_seconds()
        self._notification_max_retries = self._load_notification_max_retries()

        self._ensure_tables()
        self._seed_templates()
        self._load_runtime_from_db()

    def register(
        self,
        email: str,
        password: str,
        display_name: str,
        capacity_per_week: int = 1,
        service_config: dict[str, Any] | None = None,
        subscription_status: str = "unsubscribed",
        service_status: str = "offline",
        profile_detail: dict[str, Any] | None = None,
        capabilities: dict[str, Any] | None = None,
    ) -> AuthView:
        normalized_email = email.strip().lower()
        if normalized_email in self.email_to_user_id:
            raise ApiError("AUTH_EMAIL_EXISTS", 409, "Email already exists")

        now = self._now_iso()
        normalized_subscription = self._normalize_subscription(subscription_status)
        normalized_service = self._normalize_service_status(service_status)
        normalized_profile_detail = self._normalize_profile_detail(profile_detail)
        normalized_service_config = self._normalize_service_config(service_config, normalized_profile_detail)
        user = OpenClawIdentityView(
            id=uuid.uuid4(),
            email=normalized_email,
            display_name=display_name,
            user_status="active",
            created_at=now,
            updated_at=now,
        )
        self.users[user.id] = user
        self.email_to_user_id[user.email] = user.id
        password_hash = self._hash(password)
        self.user_password_hashes[user.id] = password_hash

        runtime = OpenClawView(
            id=user.id,
            name=user.display_name,
            subscription_status=normalized_subscription,
            service_status=normalized_service,
            active_order_id=None,
            updated_at=now,
        )
        profile = OpenClawProfileView(
            id=user.id,
            name=user.display_name,
            capacity_per_week=capacity_per_week,
            service_config=normalized_service_config,
            subscription_status=normalized_subscription,
            service_status=normalized_service,
            updated_at=now,
        )
        self.openclaws[user.id] = runtime
        self.openclaw_profiles[user.id] = profile

        self._persist_user_identity(user, password_hash, normalized_subscription, normalized_service, None)
        self._persist_openclaw_profile(profile, normalized_profile_detail)
        self._persist_openclaw_capabilities(user.id, capabilities, now)
        self._persist_openclaw_reputation_defaults(user.id)

        return AuthView(access_token=self._generate_token(user), token_type="Bearer", user=user)

    def login(self, email: str, password: str, as_role: str | None = None, client_type: str | None = None) -> AuthView:
        user_id = self.email_to_user_id.get(email.strip().lower())
        if user_id is None:
            raise ApiError("AUTH_INVALID_CREDENTIALS", 401, "Invalid email or password")

        if self.user_password_hashes.get(user_id) != self._hash(password):
            raise ApiError("AUTH_INVALID_CREDENTIALS", 401, "Invalid email or password")

        user = self.users[user_id]
        return AuthView(access_token=self._generate_token(user), token_type="Bearer", user=user)

    def authenticate_token(self, token: str) -> OpenClawIdentityView:
        raw_token = (token or "").strip()
        if not raw_token:
            raise ApiError("AUTH_TOKEN_REQUIRED", 401, "Bearer token is required")

        try:
            padded = raw_token + "=" * (-len(raw_token) % 4)
            decoded = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
            user_id_text, issued_at, signature = decoded.split("|", 2)
            payload = f"{user_id_text}|{issued_at}"
        except Exception as ex:
            raise ApiError("AUTH_TOKEN_INVALID", 401, "Invalid bearer token") from ex

        expected_signature = hmac.new(self._token_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            raise ApiError("AUTH_TOKEN_INVALID", 401, "Invalid bearer token")

        try:
            user_id = uuid.UUID(user_id_text)
        except ValueError as ex:
            raise ApiError("AUTH_TOKEN_INVALID", 401, "Invalid bearer token") from ex

        user = self.users.get(user_id)
        if user is None:
            raise ApiError("AUTH_TOKEN_INVALID", 401, "Invalid bearer token")
        return user

    def require_order_requester(self, order_id: uuid.UUID, openclaw_id: uuid.UUID) -> OrderView:
        order = self._require_order(order_id)
        if order.requester_openclaw_id != openclaw_id:
            raise ApiError("AUTH_FORBIDDEN", 403, "Authenticated OpenClaw cannot operate on this requester resource")
        return order

    def require_order_executor(self, order_id: uuid.UUID, openclaw_id: uuid.UUID) -> OrderView:
        order = self._require_order(order_id)
        if order.executor_openclaw_id is None:
            raise ApiError("ORDER_EXECUTOR_REQUIRED", 409, "Order executor is required before this action")
        if order.executor_openclaw_id != openclaw_id:
            raise ApiError("AUTH_FORBIDDEN", 403, "Authenticated OpenClaw cannot operate on this executor resource")
        return order

    def list_openclaws(self) -> list[OpenClawView]:
        return list(self.openclaws.values())

    def get_openclaw_detail(self, openclaw_id: uuid.UUID) -> OpenClawDetail:
        runtime = self._require_openclaw(openclaw_id)
        identity = self.users.get(openclaw_id)
        if identity is None:
            raise ApiError("OPENCLAW_NOT_FOUND", 404, "OpenClaw not found")

        return OpenClawDetail(
            id=identity.id,
            email=identity.email,
            display_name=identity.display_name,
            user_status=identity.user_status,
            runtime=OpenClawRuntimeView(
                id=runtime.id,
                subscription_status=runtime.subscription_status,
                service_status=runtime.service_status,
                last_heartbeat_at=self._load_last_heartbeat_at(openclaw_id),
                updated_at=runtime.updated_at,
            ),
            profile=self._load_openclaw_profile_detail(openclaw_id),
            capabilities=self._load_openclaw_capability_view(openclaw_id),
            reputation=self._load_openclaw_reputation_view(openclaw_id),
            created_at=identity.created_at,
            updated_at=identity.updated_at,
        )

    def update_openclaw_profile(self, openclaw_id: uuid.UUID, updates: dict[str, Any]) -> OpenClawDetail:
        runtime = self._require_openclaw(openclaw_id)
        current_profile = self.openclaw_profiles.get(openclaw_id)
        if current_profile is None:
            raise ApiError("OPENCLAW_NOT_FOUND", 404, "OpenClaw not found")

        current_profile_detail = self._load_openclaw_profile_detail(openclaw_id).model_dump()
        merged_profile_detail = {
            **current_profile_detail,
            **{key: value for key, value in (updates or {}).items() if key in current_profile_detail},
        }
        next_capacity_per_week = updates.get("capacity_per_week", current_profile.capacity_per_week)
        next_service_config = dict(updates.get("service_config", current_profile.service_config or {}))

        next_profile = current_profile.model_copy(
            update={
                "capacity_per_week": next_capacity_per_week,
                "service_config": self._normalize_service_config(next_service_config, merged_profile_detail),
                "subscription_status": runtime.subscription_status,
                "service_status": runtime.service_status,
                "updated_at": self._now_iso(),
            }
        )
        self.openclaw_profiles[openclaw_id] = next_profile
        self._persist_openclaw_profile(next_profile, merged_profile_detail)
        return self.get_openclaw_detail(openclaw_id)

    def update_openclaw_capabilities(self, openclaw_id: uuid.UUID, updates: dict[str, Any]) -> OpenClawDetail:
        self._require_openclaw(openclaw_id)
        current_capabilities = self._load_openclaw_capability_view(openclaw_id).model_dump()
        merged_capabilities = {**current_capabilities, **(updates or {})}
        self._persist_openclaw_capabilities(openclaw_id, merged_capabilities, self._now_iso())
        return self.get_openclaw_detail(openclaw_id)

    def list_notifications(self, openclaw_id: uuid.UUID) -> list[NotificationView]:
        self._require_openclaw(openclaw_id)
        return sorted(
            [n for n in self.notifications.values() if n.openclaw_id == openclaw_id],
            key=lambda n: (n.created_at, n.id),
            reverse=True,
        )

    def list_notification_operations(
        self,
        statuses: list[str] | None = None,
        openclaw_id: uuid.UUID | None = None,
        order_id: uuid.UUID | None = None,
    ) -> list[NotificationView]:
        normalized_statuses = {(status or "").strip() for status in (statuses or []) if (status or "").strip()}
        values = list(self.notifications.values())
        if normalized_statuses:
            values = [item for item in values if item.status in normalized_statuses]
        if openclaw_id is not None:
            values = [item for item in values if item.openclaw_id == openclaw_id]
        if order_id is not None:
            values = [item for item in values if item.order_id == order_id]
        return sorted(values, key=lambda item: (item.updated_at, item.id), reverse=True)

    def get_notification_delivery_metrics(
        self,
        openclaw_id: uuid.UUID | None = None,
        order_id: uuid.UUID | None = None,
    ) -> NotificationDeliveryMetrics:
        notifications = self._filter_notifications(openclaw_id=openclaw_id, order_id=order_id)
        callback_notifications = [item for item in notifications if (item.callback_url or "").strip()]
        callback_success_total = sum(1 for item in callback_notifications if item.status in {"sent", "acked"})
        callback_failure_total = sum(1 for item in callback_notifications if item.status in {"retry_scheduled", "dead_letter"})
        callback_success_rate = (
            round((callback_success_total / len(callback_notifications)) * 100, 2)
            if callback_notifications
            else 0.0
        )
        return NotificationDeliveryMetrics(
            total_notifications=len(notifications),
            callback_configured_total=len(callback_notifications),
            callback_success_total=callback_success_total,
            callback_failure_total=callback_failure_total,
            callback_success_rate=callback_success_rate,
            pending_total=sum(1 for item in notifications if item.status == "pending"),
            sent_total=sum(1 for item in notifications if item.status == "sent"),
            acked_total=sum(1 for item in notifications if item.status == "acked"),
            retry_scheduled_total=sum(1 for item in notifications if item.status == "retry_scheduled"),
            dead_letter_total=sum(1 for item in notifications if item.status == "dead_letter"),
        )

    def get_notification_alert_summary(
        self,
        openclaw_id: uuid.UUID | None = None,
        order_id: uuid.UUID | None = None,
    ) -> NotificationAlertSummary:
        retry_scheduled_notifications = self.list_notification_operations(
            statuses=["retry_scheduled"],
            openclaw_id=openclaw_id,
            order_id=order_id,
        )
        dead_letter_notifications = self.list_notification_operations(
            statuses=["dead_letter"],
            openclaw_id=openclaw_id,
            order_id=order_id,
        )
        callback_failure_total = len(retry_scheduled_notifications) + len(dead_letter_notifications)
        return NotificationAlertSummary(
            has_alerts=callback_failure_total > 0,
            retry_scheduled_total=len(retry_scheduled_notifications),
            dead_letter_total=len(dead_letter_notifications),
            callback_failure_total=callback_failure_total,
            retry_scheduled_notifications=retry_scheduled_notifications,
            dead_letter_notifications=dead_letter_notifications,
        )

    def register_openclaw(
        self,
        openclaw_id: uuid.UUID | None,
        name: str,
        capacity_per_week: int,
        service_config: dict[str, Any],
        subscription_status: str,
        service_status: str,
    ) -> OpenClawProfileView:
        real_id = openclaw_id or uuid.uuid4()
        user = self.users.get(real_id)
        if user is None:
            user = self._bootstrap_openclaw_identity(real_id, name)
        elif user.display_name != name:
            user = user.model_copy(update={"display_name": name, "updated_at": self._now_iso()})
            self.users[real_id] = user

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
        self._persist_openclaw_capability_defaults(real_id)
        self._persist_openclaw_reputation_defaults(real_id)
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

    def update_openclaw_subscription(self, openclaw_id: uuid.UUID, subscription_status: str) -> OpenClawView:
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

    def report_openclaw_service_status(self, openclaw_id: uuid.UUID, service_status: str, active_order_id: uuid.UUID | None) -> OpenClawView:
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

    def heartbeat_openclaw(self, openclaw_id: uuid.UUID, service_status: str) -> HeartbeatView:
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
        self._persist_openclaw_runtime(updated, last_heartbeat_at=self._now_iso())
        return HeartbeatView(
            openclaw_id=openclaw_id,
            service_status=updated.service_status,
            active_order_id=updated.active_order_id,
            assigned_order=assigned_order,
            checked_at=self._now_iso(),
        )

    def acknowledge_notification(self, openclaw_id: uuid.UUID, notification_id: uuid.UUID) -> NotificationView:
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

    def process_notification_retries(self, now: str | None = None) -> NotificationRetryProcessSummary:
        reference_time = self._parse_iso_datetime(now or self._now_iso())
        due_notifications = [
            notification
            for notification in sorted(self.notifications.values(), key=lambda item: (item.updated_at, item.id))
            if notification.status == "retry_scheduled"
            and self._is_deadline_due(notification.next_retry_at, reference_time)
        ]

        attempted = 0
        sent = 0
        retry_scheduled = 0
        dead_letter = 0
        for notification in due_notifications:
            current = self.notifications.get(notification.id)
            if current is None or current.status != "retry_scheduled":
                continue
            attempted += 1
            updated = self._dispatch_notification(current)
            if updated.status == "sent":
                sent += 1
            elif updated.status == "retry_scheduled":
                retry_scheduled += 1
            elif updated.status == "dead_letter":
                dead_letter += 1

        return NotificationRetryProcessSummary(
            attempted=attempted,
            sent=sent,
            retry_scheduled=retry_scheduled,
            dead_letter=dead_letter,
        )

    def publish_order_by_openclaw(
        self,
        openclaw_id: uuid.UUID,
        task_template_id: uuid.UUID,
        capability_package_id: uuid.UUID | None,
        title: str,
        requirement_payload: dict[str, Any],
    ) -> OrderView:
        openclaw = self._require_openclaw(openclaw_id)
        if openclaw.subscription_status != "subscribed":
            raise ApiError("OPENCLAW_NOT_SUBSCRIBED", 409, "OpenClaw is not subscribed")
        return self.create_order(openclaw_id, task_template_id, capability_package_id, title, requirement_payload)

    def accept_order_by_openclaw(self, order_id: uuid.UUID, openclaw_id: uuid.UUID) -> OrderView:
        self._require_openclaw(openclaw_id)
        return self._accept_order(order_id, openclaw_id)

    def complete_order_by_openclaw(
        self,
        order_id: uuid.UUID,
        openclaw_id: uuid.UUID,
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

    def notify_result_ready(self, order_id: uuid.UUID, executor_openclaw_id: uuid.UUID, result_summary: dict[str, Any]) -> OrderView:
        order = self._require_order(order_id)
        if order.executor_openclaw_id != executor_openclaw_id:
            raise ApiError("ORDER_EXECUTOR_MISMATCH", 409, "Order executor mismatch")
        if order.status not in {"delivered", "in_progress", "acknowledged"}:
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order cannot notify result in current status")

        now = self._now_iso()
        updated = order.model_copy(
            update={
                "status": "reviewing",
                "review_started_at": order.review_started_at or now,
                "review_expires_at": order.review_expires_at or self._offset_iso(24 * 60 * 60),
                "updated_at": now,
            }
        )
        self.orders[order_id] = updated
        self._persist_order_snapshot(updated)
        self._persist_result_event(order_id, executor_openclaw_id, "result_ready_notified", result_summary)
        self._create_notification(
            order.requester_openclaw_id,
            updated,
            "result_ready",
            {"result_summary": result_summary, "executor_openclaw_id": executor_openclaw_id},
        )
        return updated

    def receive_result(self, order_id: uuid.UUID, requester_openclaw_id: uuid.UUID, checklist_result: dict[str, Any], note: str | None) -> OrderView:
        return self.approve_acceptance(order_id, requester_openclaw_id, checklist_result, note)

    def settle_order_by_token_usage(
        self,
        order_id: uuid.UUID,
        openclaw_id: uuid.UUID,
        token_used: int | None,
        usage_receipt_id: uuid.UUID | None = None,
    ) -> SettlementFeeView:
        self._require_openclaw(openclaw_id)
        order = self._require_order(order_id)

        if order.executor_openclaw_id != openclaw_id:
            raise ApiError("ORDER_OWNER_MISMATCH", 409, "Order is not owned by this OpenClaw")
        if order.status != "approved":
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

        now = self._now_iso()
        updated_order = order.model_copy(update={"status": "settled", "settled_at": now, "updated_at": now})
        self.orders[order_id] = updated_order
        self._persist_order_snapshot(updated_order)
        self._persist_settlement(order, settlement)
        self._persist_reputation_feedback(order, resolved_token_used, settlement.settled_at)
        self._create_notification(
            order.requester_openclaw_id,
            updated_order,
            "settlement_completed",
            {"executor_openclaw_id": openclaw_id, "total_fee": str(total_fee)},
        )

        self._sync_openclaw_runtime_state(openclaw_id)
        return settlement

    def create_token_usage_receipt(
        self,
        order_id: uuid.UUID,
        openclaw_id: uuid.UUID,
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
            id=uuid.uuid4(),
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
        owner_openclaw_id: uuid.UUID,
        title: str,
        summary: str,
        task_template_id: uuid.UUID,
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
            id=uuid.uuid4(),
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
        self._persist_capability_package(view)
        return view

    def create_order(
        self,
        requester_openclaw_id: uuid.UUID,
        task_template_id: uuid.UUID,
        capability_package_id: uuid.UUID | None,
        title: str,
        requirement_payload: dict[str, Any],
    ) -> OrderView:
        self._require_openclaw(requester_openclaw_id)
        template = self.templates.get(task_template_id)
        if template is None:
            raise ApiError("TASK_TEMPLATE_NOT_FOUND", 404, "Task template not found")

        executor_openclaw_id: uuid.UUID | None = None
        if capability_package_id is not None:
            pkg = self.capability_packages.get(capability_package_id)
            if pkg is None:
                raise ApiError("CAPABILITY_PACKAGE_NOT_FOUND", 404, "Capability package not found")
            executor_openclaw_id = pkg.owner_openclaw_id

        now = self._now_iso()
        view = OrderView(
            id=uuid.uuid4(),
            order_no=f"OC-{uuid.uuid4().hex[:12].upper()}",
            requester_openclaw_id=requester_openclaw_id,
            executor_openclaw_id=executor_openclaw_id,
            task_template_id=task_template_id,
            capability_package_id=capability_package_id,
            title=title,
            status="published",
            quoted_price=self._resolve_hire_fee_by_task_type(template.task_type),
            currency="USD",
            sla_seconds=template.default_sla_seconds,
            requirement_payload=requirement_payload or {},
            published_at=now,
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
            created_at=now,
            updated_at=now,
        )

        self.orders[view.id] = view
        self._persist_order_snapshot(view)

        try:
            return self.assign_order(view.id, executor_openclaw_id)
        except ApiError as ex:
            if ex.code in self.AUTO_ASSIGNMENT_RECOVERABLE_CODES:
                return self._require_order(view.id)
            raise

    def list_orders(self, page: int, size: int, sort: str) -> list[OrderView]:
        values = sorted(self.orders.values(), key=lambda x: x.id, reverse=sort.lower().endswith(",desc"))
        return self._page(values, page, size)

    def accept_order(self, order_id: uuid.UUID) -> OrderView:
        order = self._require_order(order_id)
        if order.status != "assigned":
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order cannot be accepted in current status")
        if order.executor_openclaw_id is None:
            raise ApiError("ORDER_EXECUTOR_REQUIRED", 409, "Order executor is required before acknowledgement")

        now = self._now_iso()
        updated = order.model_copy(update={"status": "acknowledged", "acknowledged_at": now, "updated_at": now})
        self.orders[order_id] = updated
        self._persist_order_snapshot(updated)
        return updated

    def cancel_order(self, order_id: uuid.UUID, requester_openclaw_id: uuid.UUID, reason: str | None) -> OrderView:
        order = self._require_order(order_id)
        if order.requester_openclaw_id != requester_openclaw_id:
            raise ApiError("ORDER_REQUESTER_MISMATCH", 409, "Only requester OpenClaw can cancel order")
        if order.status not in {"published", "assigned", "acknowledged"}:
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order cannot be cancelled in current status")

        now = self._now_iso()
        updated = order.model_copy(
            update={
                "status": "cancelled",
                "cancelled_at": now,
                "updated_at": now,
            }
        )
        self.orders[order_id] = updated
        self._persist_order_snapshot(updated)
        self._persist_result_event(
            order_id,
            requester_openclaw_id,
            "order_cancelled",
            {"reason": (reason or "").strip()},
        )

        if order.executor_openclaw_id is not None:
            self._sync_openclaw_runtime_state(order.executor_openclaw_id)
            self._create_notification(
                order.executor_openclaw_id,
                updated,
                "task_cancelled",
                {"requester_openclaw_id": requester_openclaw_id, "reason": (reason or "").strip()},
            )
        return updated

    def expire_order_assignment(self, order_id: uuid.UUID) -> OrderView:
        order = self._require_order(order_id)
        if order.status != "assigned":
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order assignment cannot be expired in current status")
        if order.executor_openclaw_id is None:
            raise ApiError("ORDER_EXECUTOR_REQUIRED", 409, "Assigned order requires executor")

        previous_executor_id = order.executor_openclaw_id
        self._persist_result_event(
            order_id,
            previous_executor_id,
            "assignment_expired",
            {"previous_executor_openclaw_id": previous_executor_id},
        )

        republished_at = self._now_iso()
        republished = order.model_copy(
            update={
                "executor_openclaw_id": None,
                "status": "published",
                "assigned_at": None,
                "assignment_expires_at": None,
                "updated_at": republished_at,
            }
        )
        self.orders[order_id] = republished
        self._persist_order_snapshot(republished)
        self._sync_openclaw_runtime_state(previous_executor_id)
        self._create_notification(
            previous_executor_id,
            republished,
            "assignment_expired",
            {"requester_openclaw_id": order.requester_openclaw_id},
        )

        try:
            replacement = self._find_available_executor(
                order.requester_openclaw_id,
                exclude_openclaw_ids={previous_executor_id},
            )
        except ApiError as ex:
            if ex.code != "OPENCLAW_NONE_AVAILABLE":
                raise

            expired_at = self._now_iso()
            expired = republished.model_copy(
                update={
                    "status": "expired",
                    "expired_at": expired_at,
                    "updated_at": expired_at,
                }
            )
            self.orders[order_id] = expired
            self._persist_order_snapshot(expired)
            self._create_notification(
                order.requester_openclaw_id,
                expired,
                "assignment_expired",
                {"previous_executor_openclaw_id": previous_executor_id, "reassigned": False},
            )
            return expired

        self._create_notification(
            order.requester_openclaw_id,
            republished,
            "assignment_expired",
            {
                "previous_executor_openclaw_id": previous_executor_id,
                "reassigned": True,
                "next_executor_openclaw_id": replacement.id,
            },
        )
        return self.assign_order(order_id, replacement.id)

    def expire_order_review(self, order_id: uuid.UUID) -> OrderView:
        order = self._require_order(order_id)
        if order.status != "reviewing":
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order review cannot be expired in current status")

        now = self._now_iso()
        updated = order.model_copy(
            update={
                "status": "expired",
                "expired_at": now,
                "updated_at": now,
            }
        )
        self.orders[order_id] = updated
        self._persist_order_snapshot(updated)
        actor_openclaw_id = order.executor_openclaw_id or order.requester_openclaw_id
        self._persist_result_event(order_id, actor_openclaw_id, "review_expired", {})

        recipients = [order.requester_openclaw_id]
        if order.executor_openclaw_id is not None:
            recipients.append(order.executor_openclaw_id)
            self._sync_openclaw_runtime_state(order.executor_openclaw_id)
        for recipient_openclaw_id in recipients:
            self._create_notification(
                recipient_openclaw_id,
                updated,
                "review_expired",
                {"executor_openclaw_id": order.executor_openclaw_id},
            )
        return updated

    def fail_order(
        self,
        order_id: uuid.UUID,
        executor_openclaw_id: uuid.UUID,
        failure_code: str,
        failure_note: str | None,
    ) -> OrderView:
        order = self._require_order(order_id)
        if order.status not in {"assigned", "acknowledged", "in_progress"}:
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order cannot be failed in current status")
        if order.executor_openclaw_id != executor_openclaw_id:
            raise ApiError("ORDER_EXECUTOR_MISMATCH", 409, "Only assigned executor OpenClaw can fail order")

        normalized_failure_code = (failure_code or "").strip()
        if not normalized_failure_code:
            raise ApiError("FAILURE_CODE_REQUIRED", 400, "failureCode is required")

        normalized_failure_note = (failure_note or "").strip() or None
        now = self._now_iso()
        updated = order.model_copy(
            update={
                "status": "failed",
                "failed_at": now,
                "latest_failure_code": normalized_failure_code,
                "latest_failure_note": normalized_failure_note,
                "updated_at": now,
            }
        )
        self.orders[order_id] = updated
        self._persist_order_snapshot(updated)
        self._persist_result_event(
            order_id,
            executor_openclaw_id,
            "order_failed",
            {"failure_code": normalized_failure_code, "failure_note": normalized_failure_note or ""},
        )
        self._sync_openclaw_runtime_state(executor_openclaw_id)
        self._create_notification(
            order.requester_openclaw_id,
            updated,
            "order_failed",
            {
                "executor_openclaw_id": executor_openclaw_id,
                "failure_code": normalized_failure_code,
                "failure_note": normalized_failure_note,
            },
        )
        return updated

    def process_due_order_deadlines(self, now: str | None = None) -> dict[str, int]:
        reference_time = self._parse_iso_datetime(now or self._now_iso())
        due_assignment_order_ids = [
            order.id
            for order in sorted(self.orders.values(), key=lambda item: (item.updated_at, item.id))
            if order.status == "assigned"
            and self._is_deadline_due(order.assignment_expires_at, reference_time)
        ]
        due_review_order_ids = [
            order.id
            for order in sorted(self.orders.values(), key=lambda item: (item.updated_at, item.id))
            if order.status == "reviewing"
            and self._is_deadline_due(order.review_expires_at, reference_time)
        ]

        assignment_processed = 0
        review_processed = 0
        for order_id in due_assignment_order_ids:
            current = self.orders.get(order_id)
            if current is None or current.status != "assigned":
                continue
            self.expire_order_assignment(order_id)
            assignment_processed += 1

        for order_id in due_review_order_ids:
            current = self.orders.get(order_id)
            if current is None or current.status != "reviewing":
                continue
            self.expire_order_review(order_id)
            review_processed += 1

        return {
            "assignment_processed": assignment_processed,
            "review_processed": review_processed,
        }

    def start_deadline_worker(self) -> None:
        if self._deadline_worker_thread is not None and self._deadline_worker_thread.is_alive():
            return
        self._deadline_worker_stop_event.clear()
        self._deadline_worker_thread = threading.Thread(
            target=self._deadline_worker_loop,
            name="marketplace-deadline-worker",
            daemon=True,
        )
        self._deadline_worker_thread.start()

    def stop_deadline_worker(self) -> None:
        self._deadline_worker_stop_event.set()
        if self._deadline_worker_thread is not None and self._deadline_worker_thread.is_alive():
            self._deadline_worker_thread.join(timeout=max(1.0, self._deadline_worker_interval_seconds + 1.0))
        self._deadline_worker_thread = None

    def start_notification_retry_worker(self) -> None:
        if self._notification_retry_worker_thread is not None and self._notification_retry_worker_thread.is_alive():
            return
        self._notification_retry_worker_stop_event.clear()
        self._notification_retry_worker_thread = threading.Thread(
            target=self._notification_retry_worker_loop,
            name="marketplace-notification-retry-worker",
            daemon=True,
        )
        self._notification_retry_worker_thread.start()

    def stop_notification_retry_worker(self) -> None:
        self._notification_retry_worker_stop_event.set()
        if self._notification_retry_worker_thread is not None and self._notification_retry_worker_thread.is_alive():
            self._notification_retry_worker_thread.join(timeout=max(1.0, self._notification_retry_interval_seconds + 1.0))
        self._notification_retry_worker_thread = None

    def assign_order(self, order_id: uuid.UUID, executor_openclaw_id: uuid.UUID | None) -> OrderView:
        order = self._require_order(order_id)
        if order.status != "published":
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order cannot be assigned in current status")

        executor = (
            self._find_available_executor(order.requester_openclaw_id)
            if executor_openclaw_id is None
            else self._require_assignable_executor(executor_openclaw_id, order.requester_openclaw_id)
        )

        now = self._now_iso()
        updated = order.model_copy(
            update={
                "executor_openclaw_id": executor.id,
                "status": "assigned",
                "assigned_at": now,
                "assignment_expires_at": self._offset_iso(15 * 60),
                "assignment_attempt_count": order.assignment_attempt_count + 1,
                "updated_at": now,
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

    def submit_deliverable(self, order_id: uuid.UUID, delivery_note: str, payload: dict[str, Any], submitted_by: uuid.UUID) -> DeliverableView:
        order = self._require_order(order_id)
        if order.status not in {"acknowledged", "in_progress", "changes_requested"}:
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order cannot be delivered in current status")
        if order.executor_openclaw_id != submitted_by:
            raise ApiError("ORDER_EXECUTOR_MISMATCH", 409, "Only assigned executor OpenClaw can submit deliverable")

        versions = self.deliverables.setdefault(order_id, [])
        deliverable = DeliverableView(
            id=uuid.uuid4(),
            order_id=order_id,
            version_no=len(versions) + 1,
            delivery_note=delivery_note,
            deliverable_payload=payload or {},
            submitted_by=submitted_by,
            submitted_at=self._now_iso(),
        )
        versions.append(deliverable)
        self._persist_deliverable(deliverable)

        now = self._now_iso()
        updated = order.model_copy(
            update={
                "status": "delivered",
                "started_at": order.started_at or now,
                "delivered_at": now,
                "review_started_at": None,
                "review_expires_at": None,
                "approved_at": None,
                "updated_at": now,
            }
        )
        self.orders[order_id] = updated
        self._persist_order_snapshot(updated)
        self._persist_result_event(order_id, submitted_by, "result_delivered", payload or {})
        return deliverable

    def approve_acceptance(
        self,
        order_id: uuid.UUID,
        requester_openclaw_id: uuid.UUID,
        checklist_result: dict[str, Any],
        comment: str | None,
    ) -> OrderView:
        return self.review_acceptance(order_id, requester_openclaw_id, "approved", checklist_result, comment)

    def review_acceptance(
        self,
        order_id: uuid.UUID,
        requester_openclaw_id: uuid.UUID,
        decision: str,
        checklist_result: dict[str, Any],
        comment: str | None,
    ) -> OrderView:
        order = self._require_order(order_id)
        if order.status not in {"delivered", "reviewing"}:
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order cannot be reviewed in current status")
        if order.requester_openclaw_id != requester_openclaw_id:
            raise ApiError("ORDER_REQUESTER_MISMATCH", 409, "Only requester OpenClaw can review result")
        if not checklist_result:
            raise ApiError("CHECKLIST_REQUIRED", 400, "checklistResult is required")

        normalized_decision = self._normalize_review_decision(decision)
        now = self._now_iso()
        if normalized_decision == "approved":
            updated = order.model_copy(
                update={
                    "status": "approved",
                    "review_started_at": order.review_started_at or now,
                    "approved_at": now,
                    "updated_at": now,
                }
            )
            event_type = "result_approved"
            notification_type = "result_approved"
        elif normalized_decision == "request_changes":
            updated = order.model_copy(
                update={
                    "status": "changes_requested",
                    "review_started_at": order.review_started_at or now,
                    "review_expires_at": None,
                    "approved_at": None,
                    "updated_at": now,
                }
            )
            event_type = "result_changes_requested"
            notification_type = "result_changes_requested"
        else:
            updated = order.model_copy(
                update={
                    "status": "rejected",
                    "review_started_at": order.review_started_at or now,
                    "review_expires_at": None,
                    "approved_at": None,
                    "updated_at": now,
                }
            )
            event_type = "result_rejected"
            notification_type = "result_rejected"
        self.orders[order_id] = updated
        self._persist_order_snapshot(updated)
        self._persist_review(order_id, requester_openclaw_id, normalized_decision, checklist_result, comment)
        self._persist_result_event(
            order_id,
            requester_openclaw_id,
            event_type,
            {"decision": normalized_decision, "checklist": checklist_result, "note": comment or ""},
        )
        if order.executor_openclaw_id is not None:
            if normalized_decision in {"request_changes", "rejected"}:
                self._sync_openclaw_runtime_state(order.executor_openclaw_id)
            self._create_notification(
                order.executor_openclaw_id,
                updated,
                notification_type,
                {
                    "requester_openclaw_id": requester_openclaw_id,
                    "decision": normalized_decision,
                    "comment": comment or "",
                },
            )
        return updated

    def create_dispute(self, order_id: uuid.UUID, opened_by_openclaw_id: uuid.UUID, reason_code: str, description: str) -> DisputeView:
        order = self._require_order(order_id)
        if order.status in {"settled", "cancelled", "expired", "failed"}:
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order cannot be disputed in current status")

        dispute = DisputeView(
            id=uuid.uuid4(),
            order_id=order_id,
            opened_by=opened_by_openclaw_id,
            reason_code=reason_code,
            description=description,
            status="open",
            created_at=self._now_iso(),
            resolution_payload={},
            updated_at=self._now_iso(),
        )
        self.disputes.setdefault(order_id, []).append(dispute)
        self._persist_dispute(dispute)

        updated = order.model_copy(update={"status": "disputed", "updated_at": self._now_iso()})
        self.orders[order_id] = updated
        self._persist_order_snapshot(updated)
        self._persist_result_event(order_id, opened_by_openclaw_id, "order_disputed", {"reason_code": reason_code, "description": description})
        if order.executor_openclaw_id is not None:
            self._sync_openclaw_runtime_state(order.executor_openclaw_id)
        counterparty_id = (
            order.executor_openclaw_id
            if opened_by_openclaw_id == order.requester_openclaw_id
            else order.requester_openclaw_id
        )
        if counterparty_id is not None:
            self._create_notification(
                counterparty_id,
                updated,
                "task_disputed",
                {"opened_by_openclaw_id": opened_by_openclaw_id, "reason_code": reason_code},
            )
        return dispute

    def list_disputes(self, status: list[str] | None = None, order_id: uuid.UUID | None = None) -> list[DisputeView]:
        normalized_statuses = {(item or "").strip() for item in (status or []) if (item or "").strip()}
        disputes = [dispute for values in self.disputes.values() for dispute in values]
        if normalized_statuses:
            disputes = [item for item in disputes if item.status in normalized_statuses]
        if order_id is not None:
            disputes = [item for item in disputes if item.order_id == order_id]
        return sorted(disputes, key=lambda item: (item.updated_at or item.created_at, item.id), reverse=True)

    def resolve_dispute(
        self,
        order_id: uuid.UUID,
        dispute_id: uuid.UUID,
        decision: str,
        operator_note: str | None,
        token_used: int | None,
    ) -> DisputeView:
        dispute = self._require_dispute(order_id, dispute_id)
        if dispute.status not in {"open", "under_review"}:
            raise ApiError("DISPUTE_INVALID_STATUS", 409, "Dispute cannot be resolved in current status")

        order = self._require_order(order_id)
        if order.status != "disputed":
            raise ApiError("ORDER_INVALID_STATUS", 409, "Only disputed orders can be resolved")

        normalized_decision = (decision or "").strip().lower()
        normalized_note = (operator_note or "").strip()
        now = self._now_iso()
        resolution_payload = {
            "decision": normalized_decision,
            "operator_note": normalized_note,
            "resolved_at": now,
        }

        if normalized_decision == "refund_requester":
            updated_order = order.model_copy(update={"status": "cancelled", "cancelled_at": now, "updated_at": now})
            self.orders[order_id] = updated_order
            self._persist_order_snapshot(updated_order)
            if order.executor_openclaw_id is not None:
                self._sync_openclaw_runtime_state(order.executor_openclaw_id)
        elif normalized_decision == "release_executor":
            if order.executor_openclaw_id is None:
                raise ApiError("ORDER_EXECUTOR_REQUIRED", 409, "Resolved settlement requires executor")
            approved_order = order.model_copy(update={"status": "approved", "approved_at": now, "updated_at": now})
            self.orders[order_id] = approved_order
            self._persist_order_snapshot(approved_order)
            self.settle_order_by_token_usage(order_id, order.executor_openclaw_id, token_used or 0)
            updated_order = self._require_order(order_id)
            resolution_payload["token_used"] = token_used or 0
        else:
            raise ApiError("DISPUTE_DECISION_INVALID", 400, "Unsupported dispute decision")

        updated_dispute = dispute.model_copy(
            update={
                "status": "resolved",
                "resolution_payload": resolution_payload,
                "updated_at": now,
            }
        )
        entries = self.disputes.get(order_id, [])
        self.disputes[order_id] = [updated_dispute if item.id == dispute_id else item for item in entries]
        self._persist_dispute(updated_dispute)
        actor_openclaw_id = order.requester_openclaw_id
        self._persist_result_event(order_id, actor_openclaw_id, "dispute_resolved", resolution_payload)

        recipients = {order.requester_openclaw_id}
        if order.executor_openclaw_id is not None:
            recipients.add(order.executor_openclaw_id)
        for recipient_openclaw_id in recipients:
            self._create_notification(recipient_openclaw_id, updated_order, "dispute_resolved", resolution_payload)
        return updated_dispute

    def _accept_order(self, order_id: uuid.UUID, openclaw_id: uuid.UUID) -> OrderView:
        order = self._require_order(order_id)
        if order.status != "assigned":
            raise ApiError("ORDER_INVALID_STATUS", 409, "Order cannot be accepted in current status")
        if order.executor_openclaw_id != openclaw_id:
            raise ApiError("ORDER_EXECUTOR_MISMATCH", 409, "Only assigned executor OpenClaw can acknowledge order")

        now = self._now_iso()
        updated = order.model_copy(update={"status": "acknowledged", "acknowledged_at": now, "updated_at": now})
        self.orders[order_id] = updated
        self._persist_order_snapshot(updated)

        openclaw = self._require_openclaw(openclaw_id)
        runtime = openclaw.model_copy(update={"service_status": "busy", "active_order_id": order_id, "updated_at": self._now_iso()})
        self.openclaws[openclaw_id] = runtime
        self._persist_openclaw_runtime(runtime)
        return updated

    def _require_order(self, order_id: uuid.UUID) -> OrderView:
        order = self.orders.get(order_id)
        if order is None:
            raise ApiError("ORDER_NOT_FOUND", 404, "Order not found")
        return order

    def _require_dispute(self, order_id: uuid.UUID, dispute_id: uuid.UUID) -> DisputeView:
        for dispute in self.disputes.get(order_id, []):
            if dispute.id == dispute_id:
                return dispute
        raise ApiError("DISPUTE_NOT_FOUND", 404, "Dispute not found")

    def _require_openclaw(self, openclaw_id: uuid.UUID) -> OpenClawView:
        openclaw = self.openclaws.get(openclaw_id)
        if openclaw is None:
            raise ApiError("OPENCLAW_NOT_FOUND", 404, "OpenClaw not found")
        return openclaw

    def _require_assignable_executor(self, openclaw_id: uuid.UUID, requester_openclaw_id: uuid.UUID) -> OpenClawView:
        openclaw = self._require_openclaw(openclaw_id)
        if openclaw.id == requester_openclaw_id:
            raise ApiError("OPENCLAW_ASSIGNMENT_INVALID", 409, "Requester cannot be assigned as executor")
        if openclaw.subscription_status != "subscribed":
            raise ApiError("OPENCLAW_NOT_SUBSCRIBED", 409, "OpenClaw is not subscribed")
        if openclaw.service_status != "available":
            raise ApiError("OPENCLAW_NOT_AVAILABLE", 409, "OpenClaw is not available")
        return openclaw

    def _find_available_executor(
        self,
        requester_openclaw_id: uuid.UUID,
        exclude_openclaw_ids: set[uuid.UUID] | None = None,
    ) -> OpenClawView:
        excluded = exclude_openclaw_ids or set()
        candidates = [
            o
            for o in self.openclaws.values()
            if o.id != requester_openclaw_id
            and o.id not in excluded
            and o.subscription_status == "subscribed"
            and o.service_status == "available"
        ]
        if not candidates:
            raise ApiError("OPENCLAW_NONE_AVAILABLE", 409, "No available OpenClaw executor")
        return sorted(candidates, key=lambda x: x.id)[0]

    def _sync_openclaw_runtime_state(self, openclaw_id: uuid.UUID) -> OpenClawView:
        openclaw = self._require_openclaw(openclaw_id)
        active_order_id = self._find_active_order_id_for_openclaw(openclaw_id)
        next_service_status = "busy" if active_order_id is not None else (
            "available" if openclaw.subscription_status == "subscribed" else "offline"
        )
        runtime = openclaw.model_copy(
            update={
                "service_status": next_service_status,
                "active_order_id": active_order_id,
                "updated_at": self._now_iso(),
            }
        )
        self.openclaws[openclaw_id] = runtime
        self._persist_openclaw_runtime(runtime)
        return runtime

    def _deadline_worker_loop(self) -> None:
        while not self._deadline_worker_stop_event.is_set():
            try:
                self.process_due_order_deadlines()
            except Exception:
                # Keep the worker alive; persistence and API paths still surface concrete errors.
                pass
            self._deadline_worker_stop_event.wait(self._deadline_worker_interval_seconds)

    def _notification_retry_worker_loop(self) -> None:
        while not self._notification_retry_worker_stop_event.is_set():
            try:
                self.process_notification_retries()
            except Exception:
                pass
            self._notification_retry_worker_stop_event.wait(self._notification_retry_interval_seconds)

    @staticmethod
    def _load_deadline_worker_interval_seconds() -> float:
        raw = (os.getenv("MARKETPLACE_DEADLINE_WORKER_INTERVAL_SECONDS") or "15").strip()
        try:
            value = float(raw)
        except ValueError:
            return 15.0
        return value if value > 0 else 15.0

    @staticmethod
    def _load_notification_retry_interval_seconds() -> float:
        raw = (os.getenv("MARKETPLACE_NOTIFICATION_RETRY_INTERVAL_SECONDS") or "15").strip()
        try:
            value = float(raw)
        except ValueError:
            return 15.0
        return value if value > 0 else 15.0

    @staticmethod
    def _load_notification_retry_backoff_seconds() -> int:
        raw = (os.getenv("MARKETPLACE_NOTIFICATION_RETRY_BACKOFF_SECONDS") or "30").strip()
        try:
            value = int(raw)
        except ValueError:
            return 30
        return value if value > 0 else 30

    @staticmethod
    def _load_notification_max_retries() -> int:
        raw = (os.getenv("MARKETPLACE_NOTIFICATION_MAX_RETRIES") or "3").strip()
        try:
            value = int(raw)
        except ValueError:
            return 3
        return value if value > 0 else 3

    @staticmethod
    def _parse_iso_datetime(raw: str) -> datetime:
        normalized = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).astimezone(UTC)

    def _is_deadline_due(self, raw_deadline: str | None, reference_time: datetime) -> bool:
        if raw_deadline is None:
            return False
        return self._parse_iso_datetime(raw_deadline) <= reference_time

    def _find_pending_order_for_heartbeat(self, executor_openclaw_id: uuid.UUID) -> OrderView | None:
        candidates = [
            o
            for o in self.orders.values()
            if o.status == "published"
            and o.requester_openclaw_id != executor_openclaw_id
            and (o.executor_openclaw_id is None or o.executor_openclaw_id == executor_openclaw_id)
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda x: (x.created_at, x.id))[0]

    def _create_assignment_notification(self, openclaw_id: uuid.UUID, order: OrderView) -> NotificationView:
        return self._create_notification(
            openclaw_id,
            order,
            "task_assigned",
            {
                "executor_openclaw_id": openclaw_id,
                "requester_openclaw_id": order.requester_openclaw_id,
                "title": order.title,
            },
        )

    def _create_notification(
        self,
        openclaw_id: uuid.UUID,
        order: OrderView,
        notification_type: str,
        payload: dict[str, Any],
    ) -> NotificationView:
        profile = self.openclaw_profiles.get(openclaw_id)
        callback_url = (profile.service_config.get("callback_url") if profile else None) if profile else None
        body = {
            "notification_type": notification_type,
            "order_id": order.id,
            "order_no": order.order_no,
            "requester_openclaw_id": order.requester_openclaw_id,
            "executor_openclaw_id": order.executor_openclaw_id,
            "title": order.title,
            **(payload or {}),
        }
        notification = NotificationView(
            id=uuid.uuid4(),
            openclaw_id=openclaw_id,
            order_id=order.id,
            notification_type=notification_type,
            status="pending",
            callback_url=callback_url,
            payload=body,
            retry_count=0,
            last_error=None,
            next_retry_at=None,
            created_at=self._now_iso(),
            sent_at=None,
            acked_at=None,
            updated_at=self._now_iso(),
        )
        self.notifications[notification.id] = notification
        self._persist_notification(notification)

        dispatched = self._dispatch_notification(notification)
        self._persist_result_event(
            order.id,
            openclaw_id,
            f"{notification_type}_notification_{dispatched.status}",
            {"notification_id": dispatched.id},
        )
        return dispatched

    def _dispatch_notification(self, notification: NotificationView) -> NotificationView:
        callback_url = (notification.callback_url or "").strip()
        if not callback_url:
            return notification

        error_message: str | None = None
        req = url_request.Request(
            callback_url,
            data=self._dump_json(notification.payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with url_request.urlopen(req, timeout=2) as response:
                status = "sent" if 200 <= response.status < 300 else "failed"
                if status == "failed":
                    error_message = f"http_status_{response.status}"
        except (url_error.URLError, TimeoutError, ValueError) as ex:
            status = "failed"
            error_message = str(ex) or ex.__class__.__name__

        now = self._now_iso()
        if status == "sent":
            updated = notification.model_copy(
                update={
                    "status": "sent",
                    "sent_at": now,
                    "last_error": None,
                    "next_retry_at": None,
                    "updated_at": now,
                }
            )
        else:
            next_retry_count = notification.retry_count + 1
            should_dead_letter = next_retry_count >= self._notification_max_retries
            updated = notification.model_copy(
                update={
                    "status": "dead_letter" if should_dead_letter else "retry_scheduled",
                    "retry_count": next_retry_count,
                    "last_error": error_message or "delivery_failed",
                    "next_retry_at": None if should_dead_letter else self._offset_iso(self._notification_retry_backoff_seconds),
                    "updated_at": now,
                }
            )
        self.notifications[updated.id] = updated
        self._persist_notification(updated)
        return updated

    @staticmethod
    def _normalize_review_decision(value: str) -> str:
        normalized = (value or "").strip().lower()
        aliases = {
            "approve": "approved",
            "approved": "approved",
            "request_changes": "request_changes",
            "changes_requested": "request_changes",
            "reject": "rejected",
            "rejected": "rejected",
        }
        resolved = aliases.get(normalized)
        if resolved is None:
            raise ApiError("ORDER_REVIEW_DECISION_INVALID", 400, "decision must be approved, request_changes, or reject")
        return resolved

    def _filter_notifications(
        self,
        openclaw_id: uuid.UUID | None = None,
        order_id: uuid.UUID | None = None,
    ) -> list[NotificationView]:
        values = list(self.notifications.values())
        if openclaw_id is not None:
            values = [item for item in values if item.openclaw_id == openclaw_id]
        if order_id is not None:
            values = [item for item in values if item.order_id == order_id]
        return values

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

    @staticmethod
    def _normalize_profile_detail(profile_detail: dict[str, Any] | None) -> dict[str, str]:
        if not isinstance(profile_detail, dict):
            return {}

        normalized: dict[str, str] = {}
        for key in ("bio", "geo_location", "timezone_name", "callback_url"):
            value = profile_detail.get(key)
            if value is None:
                continue
            normalized[key] = value.strip() if isinstance(value, str) else str(value)
        return normalized

    @staticmethod
    def _normalize_service_config(
        service_config: dict[str, Any] | None,
        profile_detail: dict[str, str] | None,
    ) -> dict[str, Any]:
        normalized = dict(service_config or {})
        callback_url = (profile_detail or {}).get("callback_url")
        if callback_url:
            normalized["callback_url"] = callback_url
        elif not str(normalized.get("callback_url", "")).strip():
            normalized.pop("callback_url", None)
        return normalized

    def _resolve_hire_fee_by_task_type(self, task_type: str) -> Decimal:
        fee = self.TASK_HIRE_FEES.get(task_type)
        if fee is None:
            raise ApiError("TASK_TYPE_UNSUPPORTED", 400, f"Unsupported task type: {task_type}")
        return fee

    def _build_receipt_commitment(
        self,
        order_id: uuid.UUID,
        openclaw_id: uuid.UUID,
        provider: str,
        provider_request_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        measured_at: str,
    ) -> str:
        payload = {
            "order_id": str(order_id),
            "openclaw_id": str(openclaw_id),
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

    @staticmethod
    def _offset_iso(seconds: int) -> str:
        return (datetime.now(UTC) + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")

    def _bootstrap_openclaw_identity(self, openclaw_id: uuid.UUID, display_name: str) -> OpenClawIdentityView:
        now = self._now_iso()
        email = f"bootstrap+{openclaw_id.hex[:16]}@openclaw.local"
        user = OpenClawIdentityView(
            id=openclaw_id,
            email=email,
            display_name=display_name,
            user_status="active",
            created_at=now,
            updated_at=now,
        )
        password_hash = self._hash(str(openclaw_id))
        self.users[user.id] = user
        self.email_to_user_id[user.email] = user.id
        self.user_password_hashes[user.id] = password_hash
        self._persist_user_identity(user, password_hash, "unsubscribed", "offline", None)
        return user

    def _generate_token(self, user: OpenClawIdentityView) -> str:
        issued_at = self._now_iso()
        payload = f"{user.id}|{issued_at}"
        signature = hmac.new(self._token_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        raw = f"{payload}|{signature}"
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8").rstrip("=")

    def _token_secret(self) -> bytes:
        return hashlib.sha256(self.db_url.encode("utf-8")).digest()

    def _load_last_heartbeat_at(self, openclaw_id: uuid.UUID) -> str | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT last_heartbeat_at FROM openclaws WHERE id = %s", (openclaw_id,))
                row = cur.fetchone()
        if row is None:
            return None
        return self._as_iso(row["last_heartbeat_at"])

    def _load_openclaw_profile_detail(self, openclaw_id: uuid.UUID) -> OpenClawProfileDetail:
        if not self._openclaw_profiles_has_modern_columns:
            return OpenClawProfileDetail()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT bio, geo_location, timezone_name, callback_url
                    FROM openclaw_profiles
                    WHERE openclaw_id = %s
                    """,
                    (openclaw_id,),
                )
                row = cur.fetchone()
        if row is None:
            return OpenClawProfileDetail()
        return OpenClawProfileDetail(
            bio=row["bio"],
            geo_location=row["geo_location"],
            timezone_name=row["timezone_name"],
            callback_url=row["callback_url"],
        )

    def _load_openclaw_capability_view(self, openclaw_id: uuid.UUID) -> OpenClawCapabilityView:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT gpu_vram, cpu_threads, system_ram, max_concurrency, network_speed, disk_iops,
                           env_sandbox, internet_access, skill_tags, pre_installed_tools, external_auths
                    FROM openclaw_capabilities
                    WHERE openclaw_id = %s
                    """,
                    (openclaw_id,),
                )
                row = cur.fetchone()
        if row is None:
            return OpenClawCapabilityView()
        return OpenClawCapabilityView(
            gpu_vram=row["gpu_vram"],
            cpu_threads=row["cpu_threads"],
            system_ram=row["system_ram"],
            max_concurrency=row["max_concurrency"],
            network_speed=row["network_speed"],
            disk_iops=row["disk_iops"],
            env_sandbox=row["env_sandbox"],
            internet_access=row["internet_access"],
            skill_tags=row["skill_tags"] or [],
            pre_installed_tools=row["pre_installed_tools"] or [],
            external_auths=row["external_auths"] or [],
        )

    def _load_openclaw_reputation_view(self, openclaw_id: uuid.UUID) -> OpenClawReputationView:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT total_completed_tasks, average_rating, positive_rate, reliability_score, latest_feedback
                    FROM openclaw_reputation_stats
                    WHERE openclaw_id = %s
                    """,
                    (openclaw_id,),
                )
                row = cur.fetchone()
        if row is None:
            return OpenClawReputationView()
        return OpenClawReputationView(
            total_completed_tasks=row["total_completed_tasks"],
            average_rating=float(row["average_rating"] or 0),
            positive_rate=float(row["positive_rate"] or 0),
            reliability_score=row["reliability_score"],
            latest_feedback=row["latest_feedback"],
        )

    def _persist_reputation_feedback(self, order: OrderView, token_used: int, settled_at: str) -> None:
        executor_openclaw_id = order.executor_openclaw_id
        if executor_openclaw_id is None:
            return

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT decision, checklist_result, comment
                    FROM order_reviews
                    WHERE order_id = %s
                    """,
                    (order.id,),
                )
                review_row = cur.fetchone()
                if review_row is None or (review_row["decision"] or "").lower() != "approved":
                    conn.rollback()
                    return

                checklist_result = self._load_json(review_row["checklist_result"])
                rating = self._extract_feedback_rating(checklist_result)
                if rating is None:
                    conn.rollback()
                    return

                cur.execute(
                    """
                    INSERT INTO openclaw_reputation_stats (openclaw_id)
                    VALUES (%s)
                    ON CONFLICT(openclaw_id) DO NOTHING
                    """,
                    (executor_openclaw_id,),
                )
                cur.execute(
                    """
                    SELECT total_completed_tasks, average_rating, positive_rate,
                           avg_completion_time_seconds, avg_token_consumption, latest_feedback
                    FROM openclaw_reputation_stats
                    WHERE openclaw_id = %s
                    FOR UPDATE
                    """,
                    (executor_openclaw_id,),
                )
                stats_row = cur.fetchone()
                if stats_row is None:
                    raise ApiError("PERSISTENCE_ERROR", 500, "OpenClaw reputation row missing after initialization")

                completed_before = int(stats_row["total_completed_tasks"] or 0)
                completed_after = completed_before + 1
                average_rating_before = Decimal(str(stats_row["average_rating"] or "0"))
                positive_rate_before = Decimal(str(stats_row["positive_rate"] or "0"))
                avg_completion_before = int(stats_row["avg_completion_time_seconds"] or 0)
                avg_token_before = int(stats_row["avg_token_consumption"] or 0)

                rating_sum_after = (average_rating_before * completed_before) + rating
                positive_count_before = (positive_rate_before / Decimal("100")) * completed_before
                positive_count_after = positive_count_before + (Decimal("1") if rating >= Decimal("4.00") else Decimal("0"))
                average_rating_after = (rating_sum_after / completed_after).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                positive_rate_after = ((positive_count_after / completed_after) * Decimal("100")).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )
                completion_seconds = self._estimate_completion_seconds(order, settled_at)
                avg_completion_after = round(
                    ((avg_completion_before * completed_before) + completion_seconds) / completed_after
                )
                avg_token_after = round(((avg_token_before * completed_before) + token_used) / completed_after)
                latest_feedback = (review_row["comment"] or "").strip() or stats_row["latest_feedback"]

                cur.execute(
                    """
                    UPDATE openclaw_reputation_stats
                    SET total_completed_tasks = %s,
                        average_rating = %s,
                        positive_rate = %s,
                        avg_completion_time_seconds = %s,
                        avg_token_consumption = %s,
                        latest_feedback = %s,
                        updated_at = %s::timestamptz
                    WHERE openclaw_id = %s
                    """,
                    (
                        completed_after,
                        average_rating_after,
                        positive_rate_after,
                        avg_completion_after,
                        avg_token_after,
                        latest_feedback,
                        settled_at,
                        executor_openclaw_id,
                    ),
                )
            conn.commit()

    @staticmethod
    def _extract_feedback_rating(checklist_result: dict[str, Any]) -> Decimal | None:
        raw_rating = checklist_result.get("rating")
        if raw_rating is None and checklist_result.get("all_passed") is True:
            raw_rating = 5
        if raw_rating is None:
            return None
        try:
            rating = Decimal(str(raw_rating))
        except Exception:
            return None
        if rating < Decimal("1.00") or rating > Decimal("5.00"):
            return None
        return rating.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _estimate_completion_seconds(self, order: OrderView, settled_at: str) -> int:
        started_at = order.started_at or order.acknowledged_at or order.assigned_at or order.published_at
        if started_at is None:
            return 0
        return max(0, int((self._parse_iso_datetime(settled_at) - self._parse_iso_datetime(started_at)).total_seconds()))

    @staticmethod
    def _hash(plain: str) -> str:
        return hashlib.sha256(plain.encode("utf-8")).hexdigest()

    @staticmethod
    def _json_default(value: Any) -> Any:
        if isinstance(value, uuid.UUID):
            return str(value)
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, datetime):
            return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
        raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")

    def _dump_json(self, value: Any) -> str:
        return json.dumps(value, default=self._json_default)

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
                id UUID PRIMARY KEY,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                user_status TEXT NOT NULL DEFAULT 'active',
                subscription_status TEXT NOT NULL DEFAULT 'unsubscribed',
                service_status TEXT NOT NULL DEFAULT 'offline',
                last_heartbeat_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS openclaw_profiles (
                openclaw_id UUID PRIMARY KEY,
                bio TEXT,
                geo_location TEXT,
                timezone_name TEXT,
                callback_url TEXT,
                routing_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS openclaw_capabilities (
                openclaw_id UUID PRIMARY KEY,
                gpu_vram INTEGER NOT NULL DEFAULT 0,
                cpu_threads INTEGER NOT NULL DEFAULT 0,
                system_ram INTEGER NOT NULL DEFAULT 0,
                max_concurrency INTEGER NOT NULL DEFAULT 1,
                network_speed INTEGER NOT NULL DEFAULT 0,
                disk_iops INTEGER NOT NULL DEFAULT 0,
                env_sandbox TEXT NOT NULL DEFAULT 'linux_shell',
                internet_access BOOLEAN NOT NULL DEFAULT FALSE,
                skill_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
                pre_installed_tools TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
                external_auths TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
                capability_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS openclaw_reputation_stats (
                openclaw_id UUID PRIMARY KEY,
                total_completed_tasks INTEGER NOT NULL DEFAULT 0,
                average_rating NUMERIC(3, 2) NOT NULL DEFAULT 0.00,
                positive_rate NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
                avg_completion_time_seconds INTEGER NOT NULL DEFAULT 0,
                avg_token_consumption INTEGER NOT NULL DEFAULT 0,
                task_difficulty_cap TEXT NOT NULL DEFAULT 'easy',
                reliability_score INTEGER NOT NULL DEFAULT 0,
                latest_feedback TEXT,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS task_templates (
                id UUID PRIMARY KEY,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                task_type TEXT NOT NULL,
                description TEXT NOT NULL,
                input_schema JSONB NOT NULL DEFAULT '{}'::JSONB,
                output_schema JSONB NOT NULL DEFAULT '{}'::JSONB,
                acceptance_schema JSONB NOT NULL DEFAULT '{}'::JSONB,
                pricing_model TEXT NOT NULL DEFAULT 'fixed',
                default_price NUMERIC(12, 2),
                default_sla_seconds INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS capability_packages (
                id UUID PRIMARY KEY,
                owner_openclaw_id UUID NOT NULL,
                task_template_id UUID NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                sample_deliverables JSONB NOT NULL DEFAULT '{}'::JSONB,
                price_min NUMERIC(12, 2),
                price_max NUMERIC(12, 2),
                capacity_per_week INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS orders (
                id UUID PRIMARY KEY,
                order_no TEXT NOT NULL,
                requester_openclaw_id UUID NOT NULL,
                executor_openclaw_id UUID,
                task_template_id UUID NOT NULL,
                capability_package_id UUID,
                title TEXT NOT NULL,
                requirement_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
                quoted_price NUMERIC NOT NULL,
                currency TEXT NOT NULL,
                sla_seconds INTEGER NOT NULL,
                status TEXT NOT NULL,
                published_at TIMESTAMPTZ,
                assigned_at TIMESTAMPTZ,
                assignment_expires_at TIMESTAMPTZ,
                acknowledged_at TIMESTAMPTZ,
                started_at TIMESTAMPTZ,
                delivered_at TIMESTAMPTZ,
                review_started_at TIMESTAMPTZ,
                review_expires_at TIMESTAMPTZ,
                approved_at TIMESTAMPTZ,
                settled_at TIMESTAMPTZ,
                cancelled_at TIMESTAMPTZ,
                expired_at TIMESTAMPTZ,
                failed_at TIMESTAMPTZ,
                assignment_attempt_count INTEGER NOT NULL DEFAULT 0,
                latest_failure_code TEXT,
                latest_failure_note TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS order_deliverables (
                id UUID PRIMARY KEY,
                order_id UUID NOT NULL,
                version_no INTEGER NOT NULL,
                submitted_by_openclaw_id UUID NOT NULL,
                delivery_note TEXT NOT NULL,
                deliverable_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
                submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS order_reviews (
                id UUID PRIMARY KEY,
                order_id UUID NOT NULL UNIQUE,
                reviewed_by_openclaw_id UUID NOT NULL,
                decision TEXT NOT NULL,
                checklist_result JSONB NOT NULL DEFAULT '{}'::JSONB,
                comment TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS order_disputes (
                id UUID PRIMARY KEY,
                order_id UUID NOT NULL,
                opened_by_openclaw_id UUID NOT NULL,
                reason_code TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                resolution_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS order_events (
                id BIGSERIAL PRIMARY KEY,
                order_id UUID NOT NULL,
                actor_kind TEXT NOT NULL,
                actor_openclaw_id UUID,
                event_type TEXT NOT NULL,
                from_status TEXT,
                to_status TEXT,
                payload JSONB NOT NULL DEFAULT '{}'::JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_status') THEN
                    ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'changes_requested';
                    ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'rejected';
                END IF;
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_review_decision') THEN
                    ALTER TYPE order_review_decision ADD VALUE IF NOT EXISTS 'request_changes';
                    ALTER TYPE order_review_decision ADD VALUE IF NOT EXISTS 'rejected';
                END IF;
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notification_type') THEN
                    ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'task_cancelled';
                    ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'review_expired';
                    ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'order_failed';
                    ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'dispute_resolved';
                    ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'result_changes_requested';
                    ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'result_rejected';
                END IF;
            END
            $$;
            """,
            """
            CREATE TABLE IF NOT EXISTS order_notifications (
                id UUID PRIMARY KEY,
                order_id UUID NOT NULL,
                recipient_openclaw_id UUID NOT NULL,
                notification_type TEXT NOT NULL,
                status TEXT NOT NULL,
                callback_url TEXT,
                requires_ack BOOLEAN NOT NULL DEFAULT FALSE,
                payload JSONB NOT NULL DEFAULT '{}'::JSONB,
                retry_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                next_retry_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                sent_at TIMESTAMPTZ,
                acked_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            ALTER TABLE order_notifications
            ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMPTZ
            """,
            """
            CREATE TABLE IF NOT EXISTS settlements (
                id UUID PRIMARY KEY,
                order_id UUID NOT NULL UNIQUE,
                requester_openclaw_id UUID NOT NULL,
                executor_openclaw_id UUID NOT NULL,
                hire_fee NUMERIC(12, 2) NOT NULL DEFAULT 0,
                token_fee NUMERIC(12, 2) NOT NULL DEFAULT 0,
                platform_fee NUMERIC(12, 2) NOT NULL DEFAULT 0,
                total_amount NUMERIC(12, 2) NOT NULL,
                currency TEXT NOT NULL DEFAULT 'USD',
                status TEXT NOT NULL DEFAULT 'pending',
                external_reference TEXT,
                settled_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS openclaw_usage_receipts (
                id UUID PRIMARY KEY,
                order_id UUID NOT NULL,
                openclaw_id UUID NOT NULL,
                provider TEXT NOT NULL,
                provider_request_id TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                measured_at TIMESTAMPTZ NOT NULL,
                receipt_commitment TEXT NOT NULL,
                signature TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL
            )
            """,
        ]
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    self._rebuild_legacy_identity_tables_if_needed(cur)
                    self._rebuild_legacy_usage_receipts_table_if_needed(cur)
                    for sql in statements:
                        cur.execute(sql)
                conn.commit()
            return
        except Exception as ex:
            raise ApiError("PERSISTENCE_ERROR", 500, f"Failed to initialize PostgreSQL tables: {ex}") from ex

    def _rebuild_legacy_identity_tables_if_needed(self, cur) -> None:
        cur.execute(
            """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name IN ('openclaws', 'openclaw_profiles')
            """
        )
        columns = {(row["table_name"], row["column_name"]): row["data_type"] for row in cur.fetchall()}

        openclaws_exists = any(table == "openclaws" for table, _ in columns)
        openclaw_profiles_exists = any(table == "openclaw_profiles" for table, _ in columns)

        openclaws_incompatible = openclaws_exists and (
            columns.get(("openclaws", "id")) != "uuid"
            or ("openclaws", "email") not in columns
            or ("openclaws", "display_name") not in columns
        )
        openclaw_profiles_incompatible = openclaw_profiles_exists and (
            columns.get(("openclaw_profiles", "openclaw_id")) != "uuid"
            or ("openclaw_profiles", "routing_payload") not in columns
        )

        if not openclaws_incompatible and not openclaw_profiles_incompatible:
            return

        if openclaw_profiles_incompatible:
            self._drop_empty_legacy_table_or_raise(cur, "openclaw_profiles")
        if openclaws_incompatible:
            self._drop_empty_legacy_table_or_raise(cur, "openclaws")

    def _drop_empty_legacy_table_or_raise(self, cur, table_name: str) -> None:
        cur.execute(f"SELECT COUNT(*) AS row_count FROM {table_name}")
        row_count = int(cur.fetchone()["row_count"])
        if row_count > 0:
            raise ApiError(
                "PERSISTENCE_MIGRATION_REQUIRED",
                500,
                f"Table {table_name} still uses the legacy schema and contains data. Clear or migrate it before enabling UUID APIs.",
            )
        cur.execute(f"DROP TABLE IF EXISTS {table_name}")

    def _rebuild_legacy_usage_receipts_table_if_needed(self, cur) -> None:
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'openclaw_usage_receipts'
            """
        )
        columns = {row["column_name"]: row["data_type"] for row in cur.fetchall()}
        if not columns:
            return

        incompatible = (
            columns.get("id") != "uuid"
            or columns.get("order_id") != "uuid"
            or columns.get("openclaw_id") != "uuid"
            or columns.get("measured_at") != "timestamp with time zone"
            or columns.get("created_at") != "timestamp with time zone"
        )
        if not incompatible:
            return

        self._drop_empty_legacy_table_or_raise(cur, "openclaw_usage_receipts")

    def _seed_templates(self) -> None:
        if self.templates:
            return

        def add(code: str, name: str, task_type: str, description: str, base_price: str, sla_hours: int) -> None:
            now = self._now_iso()
            template = TaskTemplateView(
                id=uuid.uuid5(uuid.NAMESPACE_URL, f"openclaw-task-template:{code}"),
                code=code,
                name=name,
                task_type=task_type,
                description=description,
                input_schema={"fields": []},
                output_schema={"format": "json"},
                acceptance_schema={"checklist": []},
                pricing_model="fixed",
                default_price=Decimal(base_price),
                default_sla_seconds=sla_hours * 60 * 60,
                status="active",
                created_at=now,
                updated_at=now,
            )
            self.templates[template.id] = template
            self._persist_task_template(template)

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
        self._load_schema_capabilities()
        with self._connect() as conn:
            if self._openclaws_has_identity_columns and self._openclaw_profiles_has_modern_columns:
                openclaw_sql = """
                    SELECT
                        oc.id,
                        oc.email,
                        oc.password_hash,
                        oc.display_name,
                        oc.user_status,
                        oc.subscription_status,
                        oc.service_status,
                        oc.last_heartbeat_at,
                        oc.created_at,
                        oc.updated_at,
                        op.callback_url,
                        op.routing_payload,
                        op.updated_at AS profile_updated_at
                    FROM openclaws oc
                    LEFT JOIN openclaw_profiles op ON op.openclaw_id = oc.id
                    ORDER BY oc.created_at, oc.id
                """
            else:
                openclaw_sql = """
                    SELECT
                        oc.id,
                        NULL::text AS email,
                        NULL::text AS password_hash,
                        oc.name AS display_name,
                        'active'::text AS user_status,
                        oc.subscription_status,
                        oc.service_status,
                        NULL::timestamptz AS last_heartbeat_at,
                        oc.created_at,
                        oc.updated_at,
                        NULL::text AS callback_url,
                        jsonb_build_object(
                            'name', op.name,
                            'capacity_per_week', op.capacity_per_week,
                            'service_config', COALESCE(op.service_config, '{}'::jsonb)
                        ) AS routing_payload,
                        op.updated_at AS profile_updated_at
                    FROM openclaws oc
                    LEFT JOIN openclaw_profiles op ON op.id = oc.id
                    ORDER BY oc.created_at, oc.id
                """

            for row in conn.execute(openclaw_sql):
                openclaw_id = row["id"] if isinstance(row["id"], uuid.UUID) else uuid.UUID(str(row["id"]))
                email = row["email"] or f"bootstrap+{openclaw_id.hex[:16]}@openclaw.local"
                password_hash = row["password_hash"] or self._hash(str(openclaw_id))
                identity = OpenClawIdentityView(
                    id=openclaw_id,
                    email=email,
                    display_name=row["display_name"],
                    user_status=row["user_status"],
                    created_at=self._as_iso(row["created_at"]),
                    updated_at=self._as_iso(row["updated_at"]),
                )
                self.users[openclaw_id] = identity
                self.email_to_user_id[identity.email.lower()] = openclaw_id
                self.user_password_hashes[openclaw_id] = password_hash
                self.openclaws[openclaw_id] = OpenClawView(
                    id=openclaw_id,
                    name=row["display_name"],
                    subscription_status=row["subscription_status"],
                    service_status=row["service_status"],
                    active_order_id=None,
                    updated_at=self._as_iso(row["updated_at"]),
                )

                routing_payload = self._load_json(row["routing_payload"])
                service_config = routing_payload.get("service_config")
                if not isinstance(service_config, dict):
                    service_config = {}
                if row["callback_url"] and "callback_url" not in service_config:
                    service_config["callback_url"] = row["callback_url"]
                capacity_per_week = routing_payload.get("capacity_per_week")
                if not isinstance(capacity_per_week, int) or capacity_per_week < 1:
                    capacity_per_week = 1
                self.openclaw_profiles[openclaw_id] = OpenClawProfileView(
                    id=openclaw_id,
                    name=routing_payload.get("name") or row["display_name"],
                    capacity_per_week=capacity_per_week,
                    service_config=service_config,
                    subscription_status=row["subscription_status"],
                    service_status=row["service_status"],
                    updated_at=self._as_iso(row["profile_updated_at"] or row["updated_at"]),
                )

            for row in conn.execute(
                """
                SELECT id, code, name, task_type, description, input_schema, output_schema, acceptance_schema,
                       pricing_model, default_price, default_sla_seconds, status, created_at, updated_at
                FROM task_templates
                ORDER BY code
                """
            ):
                template_id = row["id"] if isinstance(row["id"], uuid.UUID) else uuid.UUID(str(row["id"]))
                self.templates[template_id] = TaskTemplateView(
                    id=template_id,
                    code=row["code"],
                    name=row["name"],
                    task_type=row["task_type"],
                    description=row["description"],
                    input_schema=self._load_json(row["input_schema"]),
                    output_schema=self._load_json(row["output_schema"]),
                    acceptance_schema=self._load_json(row["acceptance_schema"]),
                    pricing_model=row["pricing_model"],
                    default_price=Decimal(str(row["default_price"] or "0")),
                    default_sla_seconds=row["default_sla_seconds"],
                    status=row["status"],
                    created_at=self._as_iso(row["created_at"]),
                    updated_at=self._as_iso(row["updated_at"]),
                )

            for row in conn.execute(
                """
                SELECT id, owner_openclaw_id, task_template_id, title, summary, sample_deliverables,
                       price_min, price_max, capacity_per_week, status, created_at, updated_at
                FROM capability_packages
                ORDER BY created_at, id
                """
            ):
                package_id = row["id"] if isinstance(row["id"], uuid.UUID) else uuid.UUID(str(row["id"]))
                owner_openclaw_id = row["owner_openclaw_id"] if isinstance(row["owner_openclaw_id"], uuid.UUID) else uuid.UUID(str(row["owner_openclaw_id"]))
                task_template_id = row["task_template_id"] if isinstance(row["task_template_id"], uuid.UUID) else uuid.UUID(str(row["task_template_id"]))
                self.capability_packages[package_id] = CapabilityPackageView(
                    id=package_id,
                    owner_openclaw_id=owner_openclaw_id,
                    title=row["title"],
                    summary=row["summary"],
                    task_template_id=task_template_id,
                    sample_deliverables=self._load_json(row["sample_deliverables"]),
                    price_min=Decimal(str(row["price_min"])) if row["price_min"] is not None else None,
                    price_max=Decimal(str(row["price_max"])) if row["price_max"] is not None else None,
                    capacity_per_week=row["capacity_per_week"],
                    status=row["status"],
                    created_at=self._as_iso(row["created_at"]),
                    updated_at=self._as_iso(row["updated_at"]),
                )

            for row in conn.execute(
                """
                SELECT id, order_no, requester_openclaw_id, executor_openclaw_id, task_template_id, capability_package_id,
                       title, requirement_payload, quoted_price, currency, sla_seconds, status,
                       published_at, assigned_at, assignment_expires_at, acknowledged_at, started_at,
                       delivered_at, review_started_at, review_expires_at, approved_at, settled_at,
                       cancelled_at, expired_at, failed_at, latest_failure_code, latest_failure_note,
                       assignment_attempt_count, created_at, updated_at
                FROM orders
                ORDER BY created_at, id
                """
            ):
                order_id = row["id"] if isinstance(row["id"], uuid.UUID) else uuid.UUID(str(row["id"]))
                requester_openclaw_id = row["requester_openclaw_id"] if isinstance(row["requester_openclaw_id"], uuid.UUID) else uuid.UUID(str(row["requester_openclaw_id"]))
                executor_openclaw_id = row["executor_openclaw_id"]
                parsed_executor_openclaw_id = (
                    executor_openclaw_id
                    if executor_openclaw_id is None or isinstance(executor_openclaw_id, uuid.UUID)
                    else uuid.UUID(str(executor_openclaw_id))
                )
                task_template_id = row["task_template_id"] if isinstance(row["task_template_id"], uuid.UUID) else uuid.UUID(str(row["task_template_id"]))
                capability_package_id = row["capability_package_id"]
                parsed_capability_package_id = (
                    capability_package_id
                    if capability_package_id is None or isinstance(capability_package_id, uuid.UUID)
                    else uuid.UUID(str(capability_package_id))
                )
                self.orders[order_id] = OrderView(
                    id=order_id,
                    order_no=row["order_no"],
                    requester_openclaw_id=requester_openclaw_id,
                    executor_openclaw_id=parsed_executor_openclaw_id,
                    task_template_id=task_template_id,
                    capability_package_id=parsed_capability_package_id,
                    title=row["title"],
                    status=row["status"],
                    quoted_price=Decimal(str(row["quoted_price"])),
                    currency=row["currency"],
                    sla_seconds=row["sla_seconds"],
                    requirement_payload=self._load_json(row["requirement_payload"]),
                    published_at=self._as_iso(row["published_at"]),
                    assigned_at=self._as_iso(row["assigned_at"]),
                    assignment_expires_at=self._as_iso(row["assignment_expires_at"]),
                    acknowledged_at=self._as_iso(row["acknowledged_at"]),
                    started_at=self._as_iso(row["started_at"]),
                    delivered_at=self._as_iso(row["delivered_at"]),
                    review_started_at=self._as_iso(row["review_started_at"]),
                    review_expires_at=self._as_iso(row["review_expires_at"]),
                    approved_at=self._as_iso(row["approved_at"]),
                    settled_at=self._as_iso(row["settled_at"]),
                    cancelled_at=self._as_iso(row["cancelled_at"]),
                    expired_at=self._as_iso(row["expired_at"]),
                    failed_at=self._as_iso(row["failed_at"]),
                    latest_failure_code=row["latest_failure_code"],
                    latest_failure_note=row["latest_failure_note"],
                    assignment_attempt_count=row["assignment_attempt_count"],
                    created_at=self._as_iso(row["created_at"]),
                    updated_at=self._as_iso(row["updated_at"]),
                )

            for row in conn.execute(
                """
                SELECT id, order_id, version_no, submitted_by_openclaw_id, delivery_note, deliverable_payload, submitted_at
                FROM order_deliverables
                ORDER BY order_id, version_no
                """
            ):
                order_id = row["order_id"] if isinstance(row["order_id"], uuid.UUID) else uuid.UUID(str(row["order_id"]))
                deliverable_id = row["id"] if isinstance(row["id"], uuid.UUID) else uuid.UUID(str(row["id"]))
                submitted_by = row["submitted_by_openclaw_id"] if isinstance(row["submitted_by_openclaw_id"], uuid.UUID) else uuid.UUID(str(row["submitted_by_openclaw_id"]))
                self.deliverables.setdefault(order_id, []).append(
                    DeliverableView(
                        id=deliverable_id,
                        order_id=order_id,
                        version_no=row["version_no"],
                        delivery_note=row["delivery_note"],
                        deliverable_payload=self._load_json(row["deliverable_payload"]),
                        submitted_by=submitted_by,
                        submitted_at=self._as_iso(row["submitted_at"]),
                    )
                )

            for row in conn.execute(
                """
                SELECT id, order_id, opened_by_openclaw_id, reason_code, description, status, resolution_payload, created_at, updated_at
                FROM order_disputes
                ORDER BY created_at, id
                """
            ):
                order_id = row["order_id"] if isinstance(row["order_id"], uuid.UUID) else uuid.UUID(str(row["order_id"]))
                dispute_id = row["id"] if isinstance(row["id"], uuid.UUID) else uuid.UUID(str(row["id"]))
                opened_by = row["opened_by_openclaw_id"] if isinstance(row["opened_by_openclaw_id"], uuid.UUID) else uuid.UUID(str(row["opened_by_openclaw_id"]))
                self.disputes.setdefault(order_id, []).append(
                    DisputeView(
                        id=dispute_id,
                        order_id=order_id,
                        opened_by=opened_by,
                        reason_code=row["reason_code"],
                        description=row["description"],
                        status=row["status"],
                        created_at=self._as_iso(row["created_at"]),
                        resolution_payload=self._load_json(row["resolution_payload"]),
                        updated_at=self._as_iso(row["updated_at"]),
                    )
                )

            for row in conn.execute(
                """
                SELECT id, order_id, recipient_openclaw_id, notification_type, status, callback_url, payload,
                       retry_count, last_error, next_retry_at, created_at, sent_at, acked_at, updated_at
                FROM order_notifications
                ORDER BY created_at, id
                """
            ):
                notification_id = row["id"] if isinstance(row["id"], uuid.UUID) else uuid.UUID(str(row["id"]))
                notification_order_id = row["order_id"] if isinstance(row["order_id"], uuid.UUID) else uuid.UUID(str(row["order_id"]))
                recipient_openclaw_id = row["recipient_openclaw_id"] if isinstance(row["recipient_openclaw_id"], uuid.UUID) else uuid.UUID(str(row["recipient_openclaw_id"]))
                self.notifications[notification_id] = NotificationView(
                    id=notification_id,
                    openclaw_id=recipient_openclaw_id,
                    order_id=notification_order_id,
                    notification_type=row["notification_type"],
                    status=row["status"],
                    callback_url=row["callback_url"],
                    payload=self._load_json(row["payload"]),
                    retry_count=row["retry_count"] or 0,
                    last_error=row["last_error"],
                    next_retry_at=self._as_iso(row["next_retry_at"]),
                    created_at=self._as_iso(row["created_at"]),
                    sent_at=self._as_iso(row["sent_at"]),
                    acked_at=self._as_iso(row["acked_at"]),
                    updated_at=self._as_iso(row["updated_at"]),
                )

            for row in conn.execute(
                """
                SELECT id, order_id, openclaw_id, provider, provider_request_id, model,
                       prompt_tokens, completion_tokens, total_tokens, measured_at,
                       receipt_commitment, signature, created_at
                FROM openclaw_usage_receipts ORDER BY id
                """
            ):
                receipt_id = row["id"] if isinstance(row["id"], uuid.UUID) else uuid.UUID(str(row["id"]))
                receipt_order_id = row["order_id"] if isinstance(row["order_id"], uuid.UUID) else uuid.UUID(str(row["order_id"]))
                receipt_openclaw_id = row["openclaw_id"] if isinstance(row["openclaw_id"], uuid.UUID) else uuid.UUID(str(row["openclaw_id"]))
                receipt = TokenUsageReceiptView(
                    id=receipt_id,
                    order_id=receipt_order_id,
                    openclaw_id=receipt_openclaw_id,
                    provider=row["provider"],
                    provider_request_id=row["provider_request_id"],
                    model=row["model"],
                    prompt_tokens=row["prompt_tokens"],
                    completion_tokens=row["completion_tokens"],
                    total_tokens=row["total_tokens"],
                    measured_at=self._as_iso(row["measured_at"]),
                    receipt_commitment=row["receipt_commitment"],
                    signature=row["signature"],
                    created_at=self._as_iso(row["created_at"]),
                )
                self.usage_receipts[receipt.id] = receipt

            for row in conn.execute(
                """
                SELECT order_id, executor_openclaw_id, hire_fee, token_fee, total_amount, currency, settled_at
                FROM settlements
                WHERE status = 'completed' OR settled_at IS NOT NULL
                ORDER BY created_at, id
                """
            ):
                order_id = row["order_id"] if isinstance(row["order_id"], uuid.UUID) else uuid.UUID(str(row["order_id"]))
                executor_openclaw_id = row["executor_openclaw_id"] if isinstance(row["executor_openclaw_id"], uuid.UUID) else uuid.UUID(str(row["executor_openclaw_id"]))
                token_fee = Decimal(str(row["token_fee"] or "0"))
                self.settlement_fees_by_order_id[order_id] = SettlementFeeView(
                    order_id=order_id,
                    openclaw_id=executor_openclaw_id,
                    hire_fee=Decimal(str(row["hire_fee"] or "0")),
                    token_used=int((token_fee * Decimal("100")).to_integral_value(rounding=ROUND_HALF_UP)),
                    token_fee=token_fee,
                    total_fee=Decimal(str(row["total_amount"] or "0")),
                    currency=row["currency"],
                    settled_at=self._as_iso(row["settled_at"]),
                )

        for openclaw_id, runtime in list(self.openclaws.items()):
            active_order_id = self._find_active_order_id_for_openclaw(openclaw_id)
            self.openclaws[openclaw_id] = runtime.model_copy(update={"active_order_id": active_order_id})

    def _persist_user_identity(
        self,
        user: OpenClawIdentityView,
        password_hash: str,
        subscription_status: str,
        service_status: str,
        last_heartbeat_at: str | None,
    ) -> None:
        if not self._openclaws_has_identity_columns:
            self._execute(
                """
                INSERT INTO openclaws (
                    id, name, subscription_status, service_status, active_order_id, token_rate_per_100, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, NULL, 1.00, ?::timestamptz, ?::timestamptz)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    subscription_status = excluded.subscription_status,
                    service_status = excluded.service_status,
                    updated_at = excluded.updated_at
                """,
                (
                    user.id,
                    user.display_name,
                    subscription_status,
                    service_status,
                    user.created_at,
                    user.updated_at,
                ),
            )
            return
        self._execute(
            """
            INSERT INTO openclaws (
                id, email, password_hash, display_name, user_status, subscription_status, service_status,
                last_heartbeat_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?::timestamptz, ?::timestamptz, ?::timestamptz)
            ON CONFLICT(id) DO UPDATE SET
                email = excluded.email,
                password_hash = excluded.password_hash,
                display_name = excluded.display_name,
                user_status = excluded.user_status,
                subscription_status = excluded.subscription_status,
                service_status = excluded.service_status,
                last_heartbeat_at = COALESCE(excluded.last_heartbeat_at, openclaws.last_heartbeat_at),
                updated_at = excluded.updated_at
            """,
            (
                user.id,
                user.email,
                password_hash,
                user.display_name,
                user.user_status,
                subscription_status,
                service_status,
                last_heartbeat_at,
                user.created_at,
                user.updated_at,
            ),
        )

    def _persist_openclaw_runtime(self, runtime: OpenClawView, last_heartbeat_at: str | None = None) -> None:
        user = self.users.get(runtime.id)
        if user is None:
            user = self._bootstrap_openclaw_identity(runtime.id, runtime.name)
        else:
            user = user.model_copy(update={"display_name": runtime.name, "updated_at": runtime.updated_at})
            self.users[runtime.id] = user
        password_hash = self.user_password_hashes.get(runtime.id) or self._hash(str(runtime.id))
        self.user_password_hashes[runtime.id] = password_hash
        self._persist_user_identity(
            user,
            password_hash,
            runtime.subscription_status,
            runtime.service_status,
            last_heartbeat_at,
        )

    def _persist_openclaw_profile(
        self,
        profile: OpenClawProfileView,
        profile_detail: dict[str, Any] | None = None,
    ) -> None:
        normalized_profile_detail = self._normalize_profile_detail(profile_detail)
        callback_url = normalized_profile_detail.get("callback_url")
        if not callback_url and isinstance(profile.service_config, dict):
            raw_callback_url = profile.service_config.get("callback_url")
            if isinstance(raw_callback_url, str):
                callback_url = raw_callback_url.strip() or None
        routing_payload = {
            "name": profile.name,
            "capacity_per_week": profile.capacity_per_week,
            "service_config": profile.service_config or {},
        }
        if not self._openclaw_profiles_has_modern_columns:
            self._execute(
                """
                INSERT INTO openclaw_profiles (
                    id, name, capacity_per_week, service_config, subscription_status, service_status, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?::timestamptz)
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
                    self._dump_json(profile.service_config),
                    profile.subscription_status,
                    profile.service_status,
                    profile.updated_at,
                ),
            )
            return
        self._execute(
            """
            INSERT INTO openclaw_profiles (
                openclaw_id, bio, geo_location, timezone_name, callback_url, routing_payload, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?::timestamptz, ?::timestamptz)
            ON CONFLICT(openclaw_id) DO UPDATE SET
                bio = excluded.bio,
                geo_location = excluded.geo_location,
                timezone_name = excluded.timezone_name,
                callback_url = excluded.callback_url,
                routing_payload = excluded.routing_payload,
                updated_at = excluded.updated_at
            """,
            (
                profile.id,
                normalized_profile_detail.get("bio"),
                normalized_profile_detail.get("geo_location"),
                normalized_profile_detail.get("timezone_name"),
                callback_url,
                self._dump_json(routing_payload),
                profile.updated_at,
                profile.updated_at,
            ),
        )

    def _persist_openclaw_capability_defaults(self, openclaw_id: uuid.UUID) -> None:
        self._persist_openclaw_capabilities(openclaw_id, None)

    def _persist_openclaw_capabilities(
        self,
        openclaw_id: uuid.UUID,
        capabilities: dict[str, Any] | None,
        updated_at: str | None = None,
    ) -> None:
        normalized = {
            "gpu_vram": 0,
            "cpu_threads": 0,
            "system_ram": 0,
            "max_concurrency": 1,
            "network_speed": 0,
            "disk_iops": 0,
            "env_sandbox": "linux_shell",
            "internet_access": False,
            "skill_tags": [],
            "pre_installed_tools": [],
            "external_auths": [],
        }
        if isinstance(capabilities, dict):
            for key in normalized:
                value = capabilities.get(key)
                if value is not None:
                    normalized[key] = value

        timestamp = updated_at or self._now_iso()
        self._execute(
            """
            INSERT INTO openclaw_capabilities (
                openclaw_id, gpu_vram, cpu_threads, system_ram, max_concurrency, network_speed, disk_iops,
                env_sandbox, internet_access, skill_tags, pre_installed_tools, external_auths,
                capability_payload, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::timestamptz, ?::timestamptz)
            ON CONFLICT(openclaw_id) DO UPDATE SET
                gpu_vram = excluded.gpu_vram,
                cpu_threads = excluded.cpu_threads,
                system_ram = excluded.system_ram,
                max_concurrency = excluded.max_concurrency,
                network_speed = excluded.network_speed,
                disk_iops = excluded.disk_iops,
                env_sandbox = excluded.env_sandbox,
                internet_access = excluded.internet_access,
                skill_tags = excluded.skill_tags,
                pre_installed_tools = excluded.pre_installed_tools,
                external_auths = excluded.external_auths,
                capability_payload = excluded.capability_payload,
                updated_at = excluded.updated_at
            """,
            (
                openclaw_id,
                normalized["gpu_vram"],
                normalized["cpu_threads"],
                normalized["system_ram"],
                normalized["max_concurrency"],
                normalized["network_speed"],
                normalized["disk_iops"],
                normalized["env_sandbox"],
                normalized["internet_access"],
                normalized["skill_tags"],
                normalized["pre_installed_tools"],
                normalized["external_auths"],
                self._dump_json(normalized),
                timestamp,
                timestamp,
            ),
        )

    def _persist_openclaw_reputation_defaults(self, openclaw_id: uuid.UUID) -> None:
        self._execute(
            """
            INSERT INTO openclaw_reputation_stats (openclaw_id)
            VALUES (?)
            ON CONFLICT(openclaw_id) DO NOTHING
            """,
            (openclaw_id,),
        )

    def _persist_task_template(self, template: TaskTemplateView) -> None:
        self._execute(
            """
            INSERT INTO task_templates (
                id, code, name, task_type, description, input_schema, output_schema, acceptance_schema,
                pricing_model, default_price, default_sla_seconds, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::timestamptz, ?::timestamptz)
            ON CONFLICT(id) DO UPDATE SET
                code = excluded.code,
                name = excluded.name,
                task_type = excluded.task_type,
                description = excluded.description,
                input_schema = excluded.input_schema,
                output_schema = excluded.output_schema,
                acceptance_schema = excluded.acceptance_schema,
                pricing_model = excluded.pricing_model,
                default_price = excluded.default_price,
                default_sla_seconds = excluded.default_sla_seconds,
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (
                template.id,
                template.code,
                template.name,
                template.task_type,
                template.description,
                self._dump_json(template.input_schema),
                self._dump_json(template.output_schema),
                self._dump_json(template.acceptance_schema),
                template.pricing_model,
                str(template.default_price),
                template.default_sla_seconds,
                template.status,
                template.created_at,
                template.updated_at,
            ),
        )

    def _persist_capability_package(self, package: CapabilityPackageView) -> None:
        self._execute(
            """
            INSERT INTO capability_packages (
                id, owner_openclaw_id, task_template_id, title, summary, sample_deliverables,
                price_min, price_max, capacity_per_week, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::timestamptz, ?::timestamptz)
            ON CONFLICT(id) DO UPDATE SET
                owner_openclaw_id = excluded.owner_openclaw_id,
                task_template_id = excluded.task_template_id,
                title = excluded.title,
                summary = excluded.summary,
                sample_deliverables = excluded.sample_deliverables,
                price_min = excluded.price_min,
                price_max = excluded.price_max,
                capacity_per_week = excluded.capacity_per_week,
                status = excluded.status,
                updated_at = excluded.updated_at
            """,
            (
                package.id,
                package.owner_openclaw_id,
                package.task_template_id,
                package.title,
                package.summary,
                self._dump_json(package.sample_deliverables),
                str(package.price_min) if package.price_min is not None else None,
                str(package.price_max) if package.price_max is not None else None,
                package.capacity_per_week,
                package.status,
                package.created_at,
                package.updated_at,
            ),
        )

    def _persist_order_snapshot(self, order: OrderView) -> None:
        self._execute(
            """
            INSERT INTO orders (
                id, order_no, requester_openclaw_id, executor_openclaw_id, task_template_id, capability_package_id,
                title, requirement_payload, quoted_price, currency, sla_seconds, status,
                published_at, assigned_at, assignment_expires_at, acknowledged_at, started_at,
                delivered_at, review_started_at, review_expires_at, approved_at, settled_at,
                cancelled_at, expired_at, failed_at, latest_failure_code, latest_failure_note,
                assignment_attempt_count, created_at, updated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::timestamptz, ?::timestamptz, ?::timestamptz, ?::timestamptz, ?::timestamptz,
                ?::timestamptz, ?::timestamptz, ?::timestamptz, ?::timestamptz, ?::timestamptz,
                ?::timestamptz, ?::timestamptz, ?::timestamptz, ?, ?, ?, ?::timestamptz, ?::timestamptz
            )
            ON CONFLICT(id) DO UPDATE SET
                requester_openclaw_id = excluded.requester_openclaw_id,
                executor_openclaw_id = excluded.executor_openclaw_id,
                task_template_id = excluded.task_template_id,
                capability_package_id = excluded.capability_package_id,
                title = excluded.title,
                requirement_payload = excluded.requirement_payload,
                quoted_price = excluded.quoted_price,
                currency = excluded.currency,
                sla_seconds = excluded.sla_seconds,
                status = excluded.status,
                published_at = excluded.published_at,
                assigned_at = excluded.assigned_at,
                assignment_expires_at = excluded.assignment_expires_at,
                acknowledged_at = excluded.acknowledged_at,
                started_at = excluded.started_at,
                delivered_at = excluded.delivered_at,
                review_started_at = excluded.review_started_at,
                review_expires_at = excluded.review_expires_at,
                approved_at = excluded.approved_at,
                settled_at = excluded.settled_at,
                cancelled_at = excluded.cancelled_at,
                expired_at = excluded.expired_at,
                failed_at = excluded.failed_at,
                latest_failure_code = excluded.latest_failure_code,
                latest_failure_note = excluded.latest_failure_note,
                assignment_attempt_count = excluded.assignment_attempt_count,
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
                self._dump_json(order.requirement_payload),
                str(order.quoted_price),
                order.currency,
                order.sla_seconds,
                order.status,
                order.published_at,
                order.assigned_at,
                order.assignment_expires_at,
                order.acknowledged_at,
                order.started_at,
                order.delivered_at,
                order.review_started_at,
                order.review_expires_at,
                order.approved_at,
                order.settled_at,
                order.cancelled_at,
                order.expired_at,
                order.failed_at,
                order.latest_failure_code,
                order.latest_failure_note,
                order.assignment_attempt_count,
                order.created_at,
                order.updated_at,
            ),
        )

    def _persist_deliverable(self, deliverable: DeliverableView) -> None:
        self._execute(
            """
            INSERT INTO order_deliverables (
                id, order_id, version_no, submitted_by_openclaw_id, delivery_note, deliverable_payload, submitted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?::timestamptz)
            ON CONFLICT(id) DO UPDATE SET
                delivery_note = excluded.delivery_note,
                deliverable_payload = excluded.deliverable_payload,
                submitted_at = excluded.submitted_at
            """,
            (
                deliverable.id,
                deliverable.order_id,
                deliverable.version_no,
                deliverable.submitted_by,
                deliverable.delivery_note,
                self._dump_json(deliverable.deliverable_payload),
                deliverable.submitted_at,
            ),
        )

    def _persist_review(
        self,
        order_id: uuid.UUID,
        reviewed_by_openclaw_id: uuid.UUID,
        decision: str,
        checklist_result: dict[str, Any],
        comment: str | None,
    ) -> None:
        self._execute(
            """
            INSERT INTO order_reviews (
                id, order_id, reviewed_by_openclaw_id, decision, checklist_result, comment, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?::timestamptz)
            ON CONFLICT(order_id) DO UPDATE SET
                reviewed_by_openclaw_id = excluded.reviewed_by_openclaw_id,
                decision = excluded.decision,
                checklist_result = excluded.checklist_result,
                comment = excluded.comment,
                created_at = excluded.created_at
            """,
            (
                uuid.uuid4(),
                order_id,
                reviewed_by_openclaw_id,
                decision,
                self._dump_json(checklist_result or {}),
                comment,
                self._now_iso(),
            ),
        )

    def _persist_dispute(self, dispute: DisputeView) -> None:
        self._execute(
            """
            INSERT INTO order_disputes (
                id, order_id, opened_by_openclaw_id, reason_code, description, status, resolution_payload, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?::timestamptz, ?::timestamptz)
            ON CONFLICT(id) DO UPDATE SET
                reason_code = excluded.reason_code,
                description = excluded.description,
                status = excluded.status,
                resolution_payload = excluded.resolution_payload,
                updated_at = excluded.updated_at
            """,
            (
                dispute.id,
                dispute.order_id,
                dispute.opened_by,
                dispute.reason_code,
                dispute.description,
                dispute.status,
                self._dump_json(dispute.resolution_payload),
                dispute.created_at,
                dispute.updated_at or dispute.created_at,
            ),
        )

    def _persist_result_event(self, order_id: uuid.UUID, actor_openclaw_id: uuid.UUID, event_type: str, payload: dict[str, Any]) -> None:
        self._execute(
            "INSERT INTO order_events (order_id, actor_kind, actor_openclaw_id, event_type, payload, created_at) VALUES (?, 'openclaw', ?, ?, ?, ?::timestamptz)",
            (order_id, actor_openclaw_id, event_type, self._dump_json(payload or {}), self._now_iso()),
        )

    def _persist_notification(self, notification: NotificationView) -> None:
        requires_ack = notification.notification_type in {"task_assigned", "result_ready"}
        self._execute(
            """
            INSERT INTO order_notifications (
                id, order_id, recipient_openclaw_id, notification_type, status, callback_url,
                requires_ack, payload, retry_count, last_error, next_retry_at, created_at, sent_at, acked_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::timestamptz, ?::timestamptz, ?::timestamptz, ?::timestamptz, ?::timestamptz)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                callback_url = excluded.callback_url,
                requires_ack = excluded.requires_ack,
                payload = excluded.payload,
                retry_count = excluded.retry_count,
                last_error = excluded.last_error,
                next_retry_at = excluded.next_retry_at,
                sent_at = excluded.sent_at,
                acked_at = excluded.acked_at,
                updated_at = excluded.updated_at
            """,
            (
                notification.id,
                notification.order_id,
                notification.openclaw_id,
                notification.notification_type,
                notification.status,
                notification.callback_url,
                requires_ack,
                self._dump_json(notification.payload),
                notification.retry_count,
                notification.last_error,
                notification.next_retry_at,
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
                order_id = excluded.order_id,
                openclaw_id = excluded.openclaw_id,
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

    def _persist_settlement(self, order: OrderView, settlement: SettlementFeeView) -> None:
        self._execute(
            """
            INSERT INTO settlements (
                id, order_id, requester_openclaw_id, executor_openclaw_id, hire_fee, token_fee, platform_fee,
                total_amount, currency, status, external_reference, settled_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, 'completed', NULL, ?::timestamptz, ?::timestamptz, ?::timestamptz)
            ON CONFLICT(order_id) DO UPDATE SET
                requester_openclaw_id = excluded.requester_openclaw_id,
                executor_openclaw_id = excluded.executor_openclaw_id,
                hire_fee = excluded.hire_fee,
                token_fee = excluded.token_fee,
                total_amount = excluded.total_amount,
                currency = excluded.currency,
                status = excluded.status,
                settled_at = excluded.settled_at,
                updated_at = excluded.updated_at
            """,
            (
                uuid.uuid4(),
                settlement.order_id,
                order.requester_openclaw_id,
                settlement.openclaw_id,
                str(settlement.hire_fee),
                str(settlement.token_fee),
                str(settlement.total_fee),
                settlement.currency,
                settlement.settled_at,
                settlement.settled_at,
                settlement.settled_at,
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

    def _load_schema_capabilities(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT table_name, column_name
                    FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name IN ('openclaws', 'openclaw_profiles')
                    """
                )
                columns = {(row["table_name"], row["column_name"]) for row in cur.fetchall()}
        self._openclaws_has_identity_columns = ("openclaws", "email") in columns and ("openclaws", "display_name") in columns
        self._openclaw_profiles_has_modern_columns = ("openclaw_profiles", "openclaw_id") in columns and ("openclaw_profiles", "routing_payload") in columns

    @staticmethod
    def _as_iso(raw: Any) -> str | None:
        if raw is None:
            return None
        if isinstance(raw, datetime):
            return raw.astimezone(UTC).isoformat().replace("+00:00", "Z")
        text = str(raw)
        if text.endswith("+00:00"):
            return text.replace("+00:00", "Z")
        return text

    def _find_active_order_id_for_openclaw(self, openclaw_id: uuid.UUID) -> uuid.UUID | None:
        candidates = [
            order
            for order in self.orders.values()
            if order.executor_openclaw_id == openclaw_id and order.status in {"assigned", "acknowledged", "in_progress", "delivered", "reviewing", "changes_requested", "approved"}
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: (item.updated_at, item.id), reverse=True)[0].id

    @staticmethod
    def _normalize_legacy_order_status(raw_status: str, executor_openclaw_id: uuid.UUID | None) -> str:
        normalized = (raw_status or "").strip().lower()
        if normalized in {"created", "submitted"}:
            return "published"
        if normalized == "accepted":
            return "acknowledged" if executor_openclaw_id is not None else "published"
        if normalized == "result_ready":
            return "reviewing"
        return normalized
