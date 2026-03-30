BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'openclaw_user_status') THEN
        CREATE TYPE openclaw_user_status AS ENUM ('active', 'suspended', 'deactivated');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'openclaw_subscription_status') THEN
        CREATE TYPE openclaw_subscription_status AS ENUM ('subscribed', 'unsubscribed');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'openclaw_service_status') THEN
        CREATE TYPE openclaw_service_status AS ENUM ('available', 'busy', 'offline', 'paused');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'openclaw_env_sandbox') THEN
        CREATE TYPE openclaw_env_sandbox AS ENUM ('linux_shell', 'browser_only', 'hybrid', 'custom');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'task_template_status') THEN
        CREATE TYPE task_template_status AS ENUM ('draft', 'active', 'archived');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'capability_package_status') THEN
        CREATE TYPE capability_package_status AS ENUM ('draft', 'active', 'paused', 'archived');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_status') THEN
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
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_review_decision') THEN
        CREATE TYPE order_review_decision AS ENUM ('approved', 'disputed');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_dispute_status') THEN
        CREATE TYPE order_dispute_status AS ENUM ('open', 'under_review', 'resolved', 'rejected', 'closed');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notification_type') THEN
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
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notification_status') THEN
        CREATE TYPE notification_status AS ENUM ('pending', 'sent', 'acked', 'failed', 'retry_scheduled', 'dead_letter');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'settlement_status') THEN
        CREATE TYPE settlement_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'voided');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'task_difficulty_level') THEN
        CREATE TYPE task_difficulty_level AS ENUM ('easy', 'medium', 'hard');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'event_actor_kind') THEN
        CREATE TYPE event_actor_kind AS ENUM ('openclaw', 'platform', 'system');
    END IF;
END
$$;

CREATE OR REPLACE FUNCTION set_row_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

COMMIT;
