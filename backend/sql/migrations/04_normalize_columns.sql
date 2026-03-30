BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'openclaws' AND column_name = 'user_status' AND udt_name = 'text'
    ) THEN
        EXECUTE 'ALTER TABLE openclaws ALTER COLUMN user_status DROP DEFAULT';
        EXECUTE 'ALTER TABLE openclaws ALTER COLUMN user_status TYPE openclaw_user_status USING user_status::openclaw_user_status';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'openclaws' AND column_name = 'subscription_status' AND udt_name = 'text'
    ) THEN
        EXECUTE 'ALTER TABLE openclaws ALTER COLUMN subscription_status DROP DEFAULT';
        EXECUTE 'ALTER TABLE openclaws ALTER COLUMN subscription_status TYPE openclaw_subscription_status USING subscription_status::openclaw_subscription_status';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'openclaws' AND column_name = 'service_status' AND udt_name = 'text'
    ) THEN
        EXECUTE 'ALTER TABLE openclaws ALTER COLUMN service_status DROP DEFAULT';
        EXECUTE 'ALTER TABLE openclaws ALTER COLUMN service_status TYPE openclaw_service_status USING service_status::openclaw_service_status';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'openclaw_capabilities' AND column_name = 'env_sandbox' AND udt_name = 'text'
    ) THEN
        EXECUTE 'ALTER TABLE openclaw_capabilities ALTER COLUMN env_sandbox DROP DEFAULT';
        EXECUTE 'ALTER TABLE openclaw_capabilities ALTER COLUMN env_sandbox TYPE openclaw_env_sandbox USING env_sandbox::openclaw_env_sandbox';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'openclaw_reputation_stats' AND column_name = 'task_difficulty_cap' AND udt_name = 'text'
    ) THEN
        EXECUTE 'ALTER TABLE openclaw_reputation_stats ALTER COLUMN task_difficulty_cap DROP DEFAULT';
        EXECUTE 'ALTER TABLE openclaw_reputation_stats ALTER COLUMN task_difficulty_cap TYPE task_difficulty_level USING task_difficulty_cap::task_difficulty_level';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'task_templates' AND column_name = 'status' AND udt_name = 'text'
    ) THEN
        EXECUTE 'ALTER TABLE task_templates ALTER COLUMN status DROP DEFAULT';
        EXECUTE 'ALTER TABLE task_templates ALTER COLUMN status TYPE task_template_status USING status::task_template_status';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'capability_packages' AND column_name = 'status' AND udt_name = 'text'
    ) THEN
        EXECUTE 'ALTER TABLE capability_packages ALTER COLUMN status DROP DEFAULT';
        EXECUTE 'ALTER TABLE capability_packages ALTER COLUMN status TYPE capability_package_status USING status::capability_package_status';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'orders' AND column_name = 'status' AND udt_name = 'text'
    ) THEN
        EXECUTE 'ALTER TABLE orders ALTER COLUMN status DROP DEFAULT';
        EXECUTE 'ALTER TABLE orders ALTER COLUMN status TYPE order_status USING status::order_status';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'order_reviews' AND column_name = 'decision' AND udt_name = 'text'
    ) THEN
        EXECUTE 'ALTER TABLE order_reviews ALTER COLUMN decision TYPE order_review_decision USING decision::order_review_decision';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'order_disputes' AND column_name = 'status' AND udt_name = 'text'
    ) THEN
        EXECUTE 'ALTER TABLE order_disputes ALTER COLUMN status DROP DEFAULT';
        EXECUTE 'ALTER TABLE order_disputes ALTER COLUMN status TYPE order_dispute_status USING status::order_dispute_status';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'order_notifications' AND column_name = 'notification_type' AND udt_name = 'text'
    ) THEN
        EXECUTE 'ALTER TABLE order_notifications ALTER COLUMN notification_type TYPE notification_type USING notification_type::notification_type';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'order_notifications' AND column_name = 'status' AND udt_name = 'text'
    ) THEN
        EXECUTE 'ALTER TABLE order_notifications ALTER COLUMN status DROP DEFAULT';
        EXECUTE 'ALTER TABLE order_notifications ALTER COLUMN status TYPE notification_status USING status::notification_status';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'order_events' AND column_name = 'actor_kind' AND udt_name = 'text'
    ) THEN
        EXECUTE 'ALTER TABLE order_events ALTER COLUMN actor_kind TYPE event_actor_kind USING actor_kind::event_actor_kind';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'order_events' AND column_name = 'from_status' AND udt_name = 'text'
    ) THEN
        EXECUTE 'ALTER TABLE order_events ALTER COLUMN from_status TYPE order_status USING from_status::order_status';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'order_events' AND column_name = 'to_status' AND udt_name = 'text'
    ) THEN
        EXECUTE 'ALTER TABLE order_events ALTER COLUMN to_status TYPE order_status USING to_status::order_status';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'settlements' AND column_name = 'status' AND udt_name = 'text'
    ) THEN
        EXECUTE 'ALTER TABLE settlements ALTER COLUMN status DROP DEFAULT';
        EXECUTE 'ALTER TABLE settlements ALTER COLUMN status TYPE settlement_status USING status::settlement_status';
    END IF;
END
$$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'orders' AND column_name = 'currency' AND data_type <> 'character'
    ) THEN
        EXECUTE 'ALTER TABLE orders ALTER COLUMN currency DROP DEFAULT';
        EXECUTE 'ALTER TABLE orders ALTER COLUMN currency TYPE CHAR(3) USING upper(substr(currency, 1, 3))::char(3)';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'settlements' AND column_name = 'currency' AND data_type <> 'character'
    ) THEN
        EXECUTE 'ALTER TABLE settlements ALTER COLUMN currency DROP DEFAULT';
        EXECUTE 'ALTER TABLE settlements ALTER COLUMN currency TYPE CHAR(3) USING upper(substr(currency, 1, 3))::char(3)';
    END IF;
END
$$;

ALTER TABLE openclaws
    ALTER COLUMN id SET DEFAULT gen_random_uuid(),
    ALTER COLUMN user_status SET DEFAULT 'active',
    ALTER COLUMN subscription_status SET DEFAULT 'unsubscribed',
    ALTER COLUMN service_status SET DEFAULT 'offline',
    ALTER COLUMN created_at SET DEFAULT NOW(),
    ALTER COLUMN updated_at SET DEFAULT NOW();

ALTER TABLE openclaw_profiles
    ALTER COLUMN routing_payload SET DEFAULT '{}'::JSONB,
    ALTER COLUMN created_at SET DEFAULT NOW(),
    ALTER COLUMN updated_at SET DEFAULT NOW();

ALTER TABLE openclaw_capabilities
    ALTER COLUMN gpu_vram SET DEFAULT 0,
    ALTER COLUMN cpu_threads SET DEFAULT 0,
    ALTER COLUMN system_ram SET DEFAULT 0,
    ALTER COLUMN max_concurrency SET DEFAULT 1,
    ALTER COLUMN network_speed SET DEFAULT 0,
    ALTER COLUMN disk_iops SET DEFAULT 0,
    ALTER COLUMN env_sandbox SET DEFAULT 'linux_shell',
    ALTER COLUMN internet_access SET DEFAULT FALSE,
    ALTER COLUMN skill_tags SET DEFAULT ARRAY[]::TEXT[],
    ALTER COLUMN pre_installed_tools SET DEFAULT ARRAY[]::TEXT[],
    ALTER COLUMN external_auths SET DEFAULT ARRAY[]::TEXT[],
    ALTER COLUMN capability_payload SET DEFAULT '{}'::JSONB,
    ALTER COLUMN created_at SET DEFAULT NOW(),
    ALTER COLUMN updated_at SET DEFAULT NOW();

ALTER TABLE openclaw_reputation_stats
    ALTER COLUMN total_completed_tasks SET DEFAULT 0,
    ALTER COLUMN average_rating SET DEFAULT 0.00,
    ALTER COLUMN positive_rate SET DEFAULT 0.00,
    ALTER COLUMN avg_completion_time_seconds SET DEFAULT 0,
    ALTER COLUMN avg_token_consumption SET DEFAULT 0,
    ALTER COLUMN task_difficulty_cap SET DEFAULT 'easy',
    ALTER COLUMN reliability_score SET DEFAULT 0,
    ALTER COLUMN updated_at SET DEFAULT NOW();

ALTER TABLE task_templates
    ALTER COLUMN id SET DEFAULT gen_random_uuid(),
    ALTER COLUMN input_schema SET DEFAULT '{}'::JSONB,
    ALTER COLUMN output_schema SET DEFAULT '{}'::JSONB,
    ALTER COLUMN acceptance_schema SET DEFAULT '{}'::JSONB,
    ALTER COLUMN pricing_model SET DEFAULT 'fixed',
    ALTER COLUMN status SET DEFAULT 'draft',
    ALTER COLUMN created_at SET DEFAULT NOW(),
    ALTER COLUMN updated_at SET DEFAULT NOW();

ALTER TABLE capability_packages
    ALTER COLUMN id SET DEFAULT gen_random_uuid(),
    ALTER COLUMN sample_deliverables SET DEFAULT '{}'::JSONB,
    ALTER COLUMN status SET DEFAULT 'draft',
    ALTER COLUMN created_at SET DEFAULT NOW(),
    ALTER COLUMN updated_at SET DEFAULT NOW();

ALTER TABLE orders
    ALTER COLUMN id SET DEFAULT gen_random_uuid(),
    ALTER COLUMN requirement_payload SET DEFAULT '{}'::JSONB,
    ALTER COLUMN currency SET DEFAULT 'USD',
    ALTER COLUMN status SET DEFAULT 'draft',
    ALTER COLUMN assignment_attempt_count SET DEFAULT 0,
    ALTER COLUMN created_at SET DEFAULT NOW(),
    ALTER COLUMN updated_at SET DEFAULT NOW();

ALTER TABLE order_deliverables
    ALTER COLUMN id SET DEFAULT gen_random_uuid(),
    ALTER COLUMN deliverable_payload SET DEFAULT '{}'::JSONB,
    ALTER COLUMN submitted_at SET DEFAULT NOW();

ALTER TABLE order_reviews
    ALTER COLUMN id SET DEFAULT gen_random_uuid(),
    ALTER COLUMN checklist_result SET DEFAULT '{}'::JSONB,
    ALTER COLUMN created_at SET DEFAULT NOW();

ALTER TABLE order_disputes
    ALTER COLUMN id SET DEFAULT gen_random_uuid(),
    ALTER COLUMN status SET DEFAULT 'open',
    ALTER COLUMN resolution_payload SET DEFAULT '{}'::JSONB,
    ALTER COLUMN created_at SET DEFAULT NOW(),
    ALTER COLUMN updated_at SET DEFAULT NOW();

ALTER TABLE order_notifications
    ALTER COLUMN id SET DEFAULT gen_random_uuid(),
    ALTER COLUMN status SET DEFAULT 'pending',
    ALTER COLUMN requires_ack SET DEFAULT FALSE,
    ALTER COLUMN payload SET DEFAULT '{}'::JSONB,
    ALTER COLUMN retry_count SET DEFAULT 0,
    ALTER COLUMN created_at SET DEFAULT NOW(),
    ALTER COLUMN updated_at SET DEFAULT NOW();

ALTER TABLE order_events
    ALTER COLUMN payload SET DEFAULT '{}'::JSONB,
    ALTER COLUMN created_at SET DEFAULT NOW();

ALTER TABLE settlements
    ALTER COLUMN id SET DEFAULT gen_random_uuid(),
    ALTER COLUMN hire_fee SET DEFAULT 0,
    ALTER COLUMN token_fee SET DEFAULT 0,
    ALTER COLUMN platform_fee SET DEFAULT 0,
    ALTER COLUMN currency SET DEFAULT 'USD',
    ALTER COLUMN status SET DEFAULT 'pending',
    ALTER COLUMN created_at SET DEFAULT NOW(),
    ALTER COLUMN updated_at SET DEFAULT NOW();

COMMIT;
