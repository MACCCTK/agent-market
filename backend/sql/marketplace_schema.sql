-- OpenClaw Marketplace v1 PostgreSQL Baseline Schema
-- This file is intended as a greenfield baseline schema.
-- For production rollout, split it into reviewed migrations.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE openclaw_user_status AS ENUM (
    'active',
    'suspended',
    'deactivated'
);

CREATE TYPE openclaw_subscription_status AS ENUM (
    'subscribed',
    'unsubscribed'
);

CREATE TYPE openclaw_service_status AS ENUM (
    'available',
    'busy',
    'offline',
    'paused'
);

CREATE TYPE openclaw_env_sandbox AS ENUM (
    'linux_shell',
    'browser_only',
    'hybrid',
    'custom'
);

CREATE TYPE task_template_status AS ENUM (
    'draft',
    'active',
    'archived'
);

CREATE TYPE capability_package_status AS ENUM (
    'draft',
    'active',
    'paused',
    'archived'
);

CREATE TYPE order_status AS ENUM (
    'draft',
    'published',
    'assigned',
    'acknowledged',
    'in_progress',
    'delivered',
    'reviewing',
    'approved',
    'settled',
    'cancelled',
    'disputed',
    'expired',
    'failed'
);

CREATE TYPE order_review_decision AS ENUM (
    'approved',
    'disputed'
);

CREATE TYPE order_dispute_status AS ENUM (
    'open',
    'under_review',
    'resolved',
    'rejected',
    'closed'
);

CREATE TYPE notification_type AS ENUM (
    'task_assigned',
    'task_acknowledged',
    'task_started',
    'result_ready',
    'result_approved',
    'task_disputed',
    'assignment_expired',
    'task_cancelled',
    'review_expired',
    'order_failed',
    'dispute_resolved',
    'settlement_completed'
);

CREATE TYPE notification_status AS ENUM (
    'pending',
    'sent',
    'acked',
    'failed',
    'retry_scheduled',
    'dead_letter'
);

CREATE TYPE settlement_status AS ENUM (
    'pending',
    'processing',
    'completed',
    'failed',
    'voided'
);

CREATE TYPE task_difficulty_level AS ENUM (
    'easy',
    'medium',
    'hard'
);

CREATE TYPE event_actor_kind AS ENUM (
    'openclaw',
    'platform',
    'system'
);

CREATE OR REPLACE FUNCTION set_row_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TABLE openclaws (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    user_status openclaw_user_status NOT NULL DEFAULT 'active',
    subscription_status openclaw_subscription_status NOT NULL DEFAULT 'unsubscribed',
    service_status openclaw_service_status NOT NULL DEFAULT 'offline',
    last_heartbeat_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (char_length(trim(display_name)) > 0),
    CHECK (position('@' IN email) > 1)
);

CREATE UNIQUE INDEX openclaws_email_lower_uidx
    ON openclaws (lower(email));

CREATE INDEX openclaws_subscription_service_idx
    ON openclaws (subscription_status, service_status);

CREATE INDEX openclaws_user_status_idx
    ON openclaws (user_status);

CREATE TABLE openclaw_profiles (
    openclaw_id UUID PRIMARY KEY
        REFERENCES openclaws(id)
        ON DELETE CASCADE,
    bio TEXT,
    geo_location TEXT,
    timezone_name TEXT,
    callback_url TEXT,
    routing_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX openclaw_profiles_geo_location_idx
    ON openclaw_profiles (geo_location);

CREATE TABLE openclaw_capabilities (
    openclaw_id UUID PRIMARY KEY
        REFERENCES openclaws(id)
        ON DELETE CASCADE,
    gpu_vram INTEGER NOT NULL DEFAULT 0 CHECK (gpu_vram >= 0),
    cpu_threads INTEGER NOT NULL DEFAULT 0 CHECK (cpu_threads >= 0),
    system_ram INTEGER NOT NULL DEFAULT 0 CHECK (system_ram >= 0),
    max_concurrency INTEGER NOT NULL DEFAULT 1 CHECK (max_concurrency >= 1),
    network_speed INTEGER NOT NULL DEFAULT 0 CHECK (network_speed >= 0),
    disk_iops INTEGER NOT NULL DEFAULT 0 CHECK (disk_iops >= 0),
    env_sandbox openclaw_env_sandbox NOT NULL DEFAULT 'linux_shell',
    internet_access BOOLEAN NOT NULL DEFAULT FALSE,
    skill_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    pre_installed_tools TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    external_auths TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    capability_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX openclaw_capabilities_hardware_idx
    ON openclaw_capabilities (gpu_vram, system_ram, cpu_threads, max_concurrency);

CREATE INDEX openclaw_capabilities_env_idx
    ON openclaw_capabilities (env_sandbox, internet_access);

CREATE INDEX openclaw_capabilities_skill_tags_gin_idx
    ON openclaw_capabilities
    USING GIN (skill_tags);

CREATE INDEX openclaw_capabilities_tools_gin_idx
    ON openclaw_capabilities
    USING GIN (pre_installed_tools);

CREATE INDEX openclaw_capabilities_external_auths_gin_idx
    ON openclaw_capabilities
    USING GIN (external_auths);

CREATE TABLE openclaw_reputation_stats (
    openclaw_id UUID PRIMARY KEY
        REFERENCES openclaws(id)
        ON DELETE CASCADE,
    total_completed_tasks INTEGER NOT NULL DEFAULT 0 CHECK (total_completed_tasks >= 0),
    average_rating NUMERIC(3, 2) NOT NULL DEFAULT 0.00 CHECK (average_rating >= 0.00 AND average_rating <= 5.00),
    positive_rate NUMERIC(5, 2) NOT NULL DEFAULT 0.00 CHECK (positive_rate >= 0.00 AND positive_rate <= 100.00),
    avg_completion_time_seconds INTEGER NOT NULL DEFAULT 0 CHECK (avg_completion_time_seconds >= 0),
    avg_token_consumption INTEGER NOT NULL DEFAULT 0 CHECK (avg_token_consumption >= 0),
    task_difficulty_cap task_difficulty_level NOT NULL DEFAULT 'easy',
    reliability_score INTEGER NOT NULL DEFAULT 0 CHECK (reliability_score >= 0 AND reliability_score <= 100),
    latest_feedback TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX openclaw_reputation_score_idx
    ON openclaw_reputation_stats (reliability_score DESC, average_rating DESC);

CREATE TABLE task_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    description TEXT NOT NULL,
    input_schema JSONB NOT NULL DEFAULT '{}'::JSONB,
    output_schema JSONB NOT NULL DEFAULT '{}'::JSONB,
    acceptance_schema JSONB NOT NULL DEFAULT '{}'::JSONB,
    pricing_model TEXT NOT NULL DEFAULT 'fixed',
    default_price NUMERIC(12, 2) CHECK (default_price IS NULL OR default_price >= 0),
    default_sla_seconds INTEGER NOT NULL CHECK (default_sla_seconds > 0),
    status task_template_status NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (char_length(trim(code)) > 0),
    CHECK (char_length(trim(name)) > 0),
    CHECK (char_length(trim(task_type)) > 0)
);

CREATE INDEX task_templates_status_type_idx
    ON task_templates (status, task_type);

CREATE TABLE capability_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_openclaw_id UUID NOT NULL
        REFERENCES openclaws(id)
        ON DELETE CASCADE,
    task_template_id UUID NOT NULL
        REFERENCES task_templates(id)
        ON DELETE RESTRICT,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    sample_deliverables JSONB NOT NULL DEFAULT '{}'::JSONB,
    price_min NUMERIC(12, 2) CHECK (price_min IS NULL OR price_min >= 0),
    price_max NUMERIC(12, 2) CHECK (price_max IS NULL OR price_max >= 0),
    capacity_per_week INTEGER NOT NULL CHECK (capacity_per_week >= 1),
    status capability_package_status NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (char_length(trim(title)) > 0),
    CHECK (char_length(trim(summary)) > 0),
    CHECK (
        price_min IS NULL
        OR price_max IS NULL
        OR price_min <= price_max
    )
);

CREATE INDEX capability_packages_owner_status_idx
    ON capability_packages (owner_openclaw_id, status);

CREATE INDEX capability_packages_template_status_idx
    ON capability_packages (task_template_id, status);

CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_no TEXT NOT NULL UNIQUE,
    requester_openclaw_id UUID NOT NULL
        REFERENCES openclaws(id)
        ON DELETE RESTRICT,
    executor_openclaw_id UUID
        REFERENCES openclaws(id)
        ON DELETE RESTRICT,
    task_template_id UUID NOT NULL
        REFERENCES task_templates(id)
        ON DELETE RESTRICT,
    capability_package_id UUID
        REFERENCES capability_packages(id)
        ON DELETE SET NULL,
    title TEXT NOT NULL,
    requirement_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    quoted_price NUMERIC(12, 2) NOT NULL CHECK (quoted_price >= 0),
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    sla_seconds INTEGER NOT NULL CHECK (sla_seconds > 0),
    status order_status NOT NULL DEFAULT 'draft',
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
    assignment_attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (assignment_attempt_count >= 0),
    latest_failure_code TEXT,
    latest_failure_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (char_length(trim(title)) > 0),
    CHECK (requester_openclaw_id <> executor_openclaw_id),
    CHECK (currency = upper(currency)),
    CHECK (assigned_at IS NULL OR executor_openclaw_id IS NOT NULL),
    CHECK (assignment_expires_at IS NULL OR assigned_at IS NOT NULL),
    CHECK (acknowledged_at IS NULL OR assigned_at IS NOT NULL),
    CHECK (delivered_at IS NULL OR started_at IS NOT NULL),
    CHECK (review_started_at IS NULL OR delivered_at IS NOT NULL),
    CHECK (review_expires_at IS NULL OR review_started_at IS NOT NULL),
    CHECK (approved_at IS NULL OR review_started_at IS NOT NULL),
    CHECK (settled_at IS NULL OR approved_at IS NOT NULL),
    CHECK (status <> 'assigned' OR (executor_openclaw_id IS NOT NULL AND assigned_at IS NOT NULL AND assignment_expires_at IS NOT NULL)),
    CHECK (status <> 'reviewing' OR (delivered_at IS NOT NULL AND review_started_at IS NOT NULL)),
    CHECK (status <> 'approved' OR approved_at IS NOT NULL),
    CHECK (status <> 'settled' OR settled_at IS NOT NULL),
    CHECK (status <> 'cancelled' OR cancelled_at IS NOT NULL),
    CHECK (status <> 'expired' OR expired_at IS NOT NULL),
    CHECK (status <> 'failed' OR failed_at IS NOT NULL)
);

CREATE INDEX orders_requester_status_idx
    ON orders (requester_openclaw_id, status, created_at DESC);

CREATE INDEX orders_executor_status_idx
    ON orders (executor_openclaw_id, status, updated_at DESC);

CREATE INDEX orders_status_created_idx
    ON orders (status, created_at DESC);

CREATE INDEX orders_assignment_expires_idx
    ON orders (assignment_expires_at)
    WHERE status = 'assigned';

CREATE INDEX orders_review_expires_idx
    ON orders (review_expires_at)
    WHERE status = 'reviewing';

CREATE TABLE order_deliverables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL
        REFERENCES orders(id)
        ON DELETE CASCADE,
    version_no INTEGER NOT NULL CHECK (version_no >= 1),
    submitted_by_openclaw_id UUID NOT NULL
        REFERENCES openclaws(id)
        ON DELETE RESTRICT,
    delivery_note TEXT NOT NULL,
    deliverable_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (char_length(trim(delivery_note)) > 0),
    UNIQUE (order_id, version_no)
);

CREATE INDEX order_deliverables_order_idx
    ON order_deliverables (order_id, submitted_at DESC);

CREATE TABLE order_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL UNIQUE
        REFERENCES orders(id)
        ON DELETE CASCADE,
    reviewed_by_openclaw_id UUID NOT NULL
        REFERENCES openclaws(id)
        ON DELETE RESTRICT,
    decision order_review_decision NOT NULL,
    checklist_result JSONB NOT NULL DEFAULT '{}'::JSONB,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX order_reviews_reviewer_idx
    ON order_reviews (reviewed_by_openclaw_id, created_at DESC);

CREATE TABLE order_disputes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL
        REFERENCES orders(id)
        ON DELETE CASCADE,
    opened_by_openclaw_id UUID NOT NULL
        REFERENCES openclaws(id)
        ON DELETE RESTRICT,
    reason_code TEXT NOT NULL,
    description TEXT NOT NULL,
    status order_dispute_status NOT NULL DEFAULT 'open',
    resolution_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (char_length(trim(reason_code)) > 0),
    CHECK (char_length(trim(description)) > 0)
);

CREATE INDEX order_disputes_order_status_idx
    ON order_disputes (order_id, status, created_at DESC);

CREATE TABLE order_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL
        REFERENCES orders(id)
        ON DELETE CASCADE,
    recipient_openclaw_id UUID NOT NULL
        REFERENCES openclaws(id)
        ON DELETE CASCADE,
    notification_type notification_type NOT NULL,
    status notification_status NOT NULL DEFAULT 'pending',
    callback_url TEXT,
    requires_ack BOOLEAN NOT NULL DEFAULT FALSE,
    payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    last_error TEXT,
    next_retry_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    acked_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (NOT requires_ack OR notification_type IN ('task_assigned', 'result_ready')),
    CHECK (status <> 'acked' OR acked_at IS NOT NULL),
    CHECK (acked_at IS NULL OR requires_ack)
);

CREATE INDEX order_notifications_recipient_status_idx
    ON order_notifications (recipient_openclaw_id, status, created_at DESC);

CREATE INDEX order_notifications_order_idx
    ON order_notifications (order_id, created_at DESC);

CREATE INDEX order_notifications_retry_idx
    ON order_notifications (status, next_retry_at)
    WHERE status IN ('retry_scheduled', 'dead_letter');

CREATE INDEX order_notifications_retry_idx
    ON order_notifications (status, created_at)
    WHERE status IN ('failed', 'retry_scheduled');

CREATE INDEX order_notifications_ack_required_idx
    ON order_notifications (recipient_openclaw_id, created_at DESC)
    WHERE requires_ack = TRUE AND status IN ('pending', 'sent');

CREATE TABLE order_events (
    id BIGSERIAL PRIMARY KEY,
    order_id UUID NOT NULL
        REFERENCES orders(id)
        ON DELETE CASCADE,
    actor_kind event_actor_kind NOT NULL,
    actor_openclaw_id UUID
        REFERENCES openclaws(id)
        ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    from_status order_status,
    to_status order_status,
    payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        (actor_kind = 'openclaw' AND actor_openclaw_id IS NOT NULL)
        OR (actor_kind IN ('platform', 'system') AND actor_openclaw_id IS NULL)
    ),
    CHECK (char_length(trim(event_type)) > 0)
);

CREATE INDEX order_events_order_created_idx
    ON order_events (order_id, created_at DESC);

CREATE INDEX order_events_event_type_idx
    ON order_events (event_type, created_at DESC);

CREATE TABLE settlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL UNIQUE
        REFERENCES orders(id)
        ON DELETE CASCADE,
    requester_openclaw_id UUID NOT NULL
        REFERENCES openclaws(id)
        ON DELETE RESTRICT,
    executor_openclaw_id UUID NOT NULL
        REFERENCES openclaws(id)
        ON DELETE RESTRICT,
    hire_fee NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (hire_fee >= 0),
    token_fee NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (token_fee >= 0),
    platform_fee NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (platform_fee >= 0),
    total_amount NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0),
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    status settlement_status NOT NULL DEFAULT 'pending',
    external_reference TEXT,
    settled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (requester_openclaw_id <> executor_openclaw_id),
    CHECK (currency = upper(currency)),
    CHECK (total_amount = hire_fee + token_fee + platform_fee),
    CHECK ((status = 'completed') = (settled_at IS NOT NULL))
);

CREATE INDEX settlements_executor_status_idx
    ON settlements (executor_openclaw_id, status, created_at DESC);

CREATE INDEX settlements_requester_status_idx
    ON settlements (requester_openclaw_id, status, created_at DESC);

CREATE TRIGGER openclaws_set_updated_at
BEFORE UPDATE ON openclaws
FOR EACH ROW
EXECUTE FUNCTION set_row_updated_at();

CREATE TRIGGER openclaw_profiles_set_updated_at
BEFORE UPDATE ON openclaw_profiles
FOR EACH ROW
EXECUTE FUNCTION set_row_updated_at();

CREATE TRIGGER openclaw_capabilities_set_updated_at
BEFORE UPDATE ON openclaw_capabilities
FOR EACH ROW
EXECUTE FUNCTION set_row_updated_at();

CREATE TRIGGER openclaw_reputation_stats_set_updated_at
BEFORE UPDATE ON openclaw_reputation_stats
FOR EACH ROW
EXECUTE FUNCTION set_row_updated_at();

CREATE TRIGGER task_templates_set_updated_at
BEFORE UPDATE ON task_templates
FOR EACH ROW
EXECUTE FUNCTION set_row_updated_at();

CREATE TRIGGER capability_packages_set_updated_at
BEFORE UPDATE ON capability_packages
FOR EACH ROW
EXECUTE FUNCTION set_row_updated_at();

CREATE TRIGGER orders_set_updated_at
BEFORE UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION set_row_updated_at();

CREATE TRIGGER order_disputes_set_updated_at
BEFORE UPDATE ON order_disputes
FOR EACH ROW
EXECUTE FUNCTION set_row_updated_at();

CREATE TRIGGER order_notifications_set_updated_at
BEFORE UPDATE ON order_notifications
FOR EACH ROW
EXECUTE FUNCTION set_row_updated_at();

CREATE TRIGGER settlements_set_updated_at
BEFORE UPDATE ON settlements
FOR EACH ROW
EXECUTE FUNCTION set_row_updated_at();
