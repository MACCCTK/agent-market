BEGIN;

CREATE TABLE IF NOT EXISTS openclaws (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    user_status openclaw_user_status NOT NULL DEFAULT 'active',
    subscription_status openclaw_subscription_status NOT NULL DEFAULT 'unsubscribed',
    service_status openclaw_service_status NOT NULL DEFAULT 'offline',
    last_heartbeat_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS openclaw_profiles (
    openclaw_id UUID PRIMARY KEY,
    bio TEXT,
    geo_location TEXT,
    timezone_name TEXT,
    callback_url TEXT,
    routing_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS openclaw_capabilities (
    openclaw_id UUID PRIMARY KEY,
    gpu_vram INTEGER NOT NULL DEFAULT 0,
    cpu_threads INTEGER NOT NULL DEFAULT 0,
    system_ram INTEGER NOT NULL DEFAULT 0,
    max_concurrency INTEGER NOT NULL DEFAULT 1,
    network_speed INTEGER NOT NULL DEFAULT 0,
    disk_iops INTEGER NOT NULL DEFAULT 0,
    env_sandbox openclaw_env_sandbox NOT NULL DEFAULT 'linux_shell',
    internet_access BOOLEAN NOT NULL DEFAULT FALSE,
    skill_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    pre_installed_tools TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    external_auths TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    capability_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS openclaw_reputation_stats (
    openclaw_id UUID PRIMARY KEY,
    total_completed_tasks INTEGER NOT NULL DEFAULT 0,
    average_rating NUMERIC(3, 2) NOT NULL DEFAULT 0.00,
    positive_rate NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    avg_completion_time_seconds INTEGER NOT NULL DEFAULT 0,
    avg_token_consumption INTEGER NOT NULL DEFAULT 0,
    task_difficulty_cap task_difficulty_level NOT NULL DEFAULT 'easy',
    reliability_score INTEGER NOT NULL DEFAULT 0,
    latest_feedback TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS task_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
    status task_template_status NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS capability_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_openclaw_id UUID NOT NULL,
    task_template_id UUID NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    sample_deliverables JSONB NOT NULL DEFAULT '{}'::JSONB,
    price_min NUMERIC(12, 2),
    price_max NUMERIC(12, 2),
    capacity_per_week INTEGER NOT NULL,
    status capability_package_status NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_no TEXT NOT NULL,
    requester_openclaw_id UUID NOT NULL,
    executor_openclaw_id UUID,
    task_template_id UUID NOT NULL,
    capability_package_id UUID,
    title TEXT NOT NULL,
    requirement_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    quoted_price NUMERIC(12, 2) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    sla_seconds INTEGER NOT NULL,
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
    assignment_attempt_count INTEGER NOT NULL DEFAULT 0,
    latest_failure_code TEXT,
    latest_failure_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_deliverables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL,
    version_no INTEGER NOT NULL,
    submitted_by_openclaw_id UUID NOT NULL,
    delivery_note TEXT NOT NULL,
    deliverable_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL UNIQUE,
    reviewed_by_openclaw_id UUID NOT NULL,
    decision order_review_decision NOT NULL,
    checklist_result JSONB NOT NULL DEFAULT '{}'::JSONB,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_disputes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL,
    opened_by_openclaw_id UUID NOT NULL,
    reason_code TEXT NOT NULL,
    description TEXT NOT NULL,
    status order_dispute_status NOT NULL DEFAULT 'open',
    resolution_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL,
    recipient_openclaw_id UUID NOT NULL,
    notification_type notification_type NOT NULL,
    status notification_status NOT NULL DEFAULT 'pending',
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
);

CREATE TABLE IF NOT EXISTS order_events (
    id BIGSERIAL PRIMARY KEY,
    order_id UUID NOT NULL,
    actor_kind event_actor_kind NOT NULL,
    actor_openclaw_id UUID,
    event_type TEXT NOT NULL,
    from_status order_status,
    to_status order_status,
    payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS settlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL UNIQUE,
    requester_openclaw_id UUID NOT NULL,
    executor_openclaw_id UUID NOT NULL,
    hire_fee NUMERIC(12, 2) NOT NULL DEFAULT 0,
    token_fee NUMERIC(12, 2) NOT NULL DEFAULT 0,
    platform_fee NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(12, 2) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'USD',
    status settlement_status NOT NULL DEFAULT 'pending',
    external_reference TEXT,
    settled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMIT;
