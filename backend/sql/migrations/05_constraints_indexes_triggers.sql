BEGIN;

CREATE OR REPLACE FUNCTION ensure_constraint(p_table_name TEXT, p_constraint_name TEXT, p_sql TEXT)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = current_schema()
          AND t.relname = p_table_name
          AND c.conname = p_constraint_name
    ) THEN
        EXECUTE p_sql;
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION ensure_index(p_index_name TEXT, p_sql TEXT)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    IF to_regclass(format('%I.%I', current_schema(), p_index_name)) IS NULL THEN
        EXECUTE p_sql;
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION ensure_trigger(p_table_name TEXT, p_trigger_name TEXT, p_sql TEXT)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger tg
        JOIN pg_class t ON t.oid = tg.tgrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = current_schema()
          AND t.relname = p_table_name
          AND tg.tgname = p_trigger_name
          AND NOT tg.tgisinternal
    ) THEN
        EXECUTE p_sql;
    END IF;
END;
$$;

SELECT ensure_constraint('openclaws', 'openclaws_display_name_not_blank_chk', $sql$
    ALTER TABLE openclaws
    ADD CONSTRAINT openclaws_display_name_not_blank_chk
    CHECK (char_length(trim(display_name)) > 0)
$sql$);
SELECT ensure_constraint('openclaws', 'openclaws_email_format_chk', $sql$
    ALTER TABLE openclaws
    ADD CONSTRAINT openclaws_email_format_chk
    CHECK (position('@' IN email) > 1)
$sql$);

SELECT ensure_constraint('openclaw_profiles', 'openclaw_profiles_openclaw_fk', $sql$
    ALTER TABLE openclaw_profiles
    ADD CONSTRAINT openclaw_profiles_openclaw_fk
    FOREIGN KEY (openclaw_id) REFERENCES openclaws(id) ON DELETE CASCADE
$sql$);

SELECT ensure_constraint('openclaw_capabilities', 'openclaw_capabilities_openclaw_fk', $sql$
    ALTER TABLE openclaw_capabilities
    ADD CONSTRAINT openclaw_capabilities_openclaw_fk
    FOREIGN KEY (openclaw_id) REFERENCES openclaws(id) ON DELETE CASCADE
$sql$);
SELECT ensure_constraint('openclaw_capabilities', 'openclaw_capabilities_gpu_vram_nonnegative_chk', $sql$
    ALTER TABLE openclaw_capabilities
    ADD CONSTRAINT openclaw_capabilities_gpu_vram_nonnegative_chk
    CHECK (gpu_vram >= 0)
$sql$);
SELECT ensure_constraint('openclaw_capabilities', 'openclaw_capabilities_cpu_threads_nonnegative_chk', $sql$
    ALTER TABLE openclaw_capabilities
    ADD CONSTRAINT openclaw_capabilities_cpu_threads_nonnegative_chk
    CHECK (cpu_threads >= 0)
$sql$);
SELECT ensure_constraint('openclaw_capabilities', 'openclaw_capabilities_system_ram_nonnegative_chk', $sql$
    ALTER TABLE openclaw_capabilities
    ADD CONSTRAINT openclaw_capabilities_system_ram_nonnegative_chk
    CHECK (system_ram >= 0)
$sql$);
SELECT ensure_constraint('openclaw_capabilities', 'openclaw_capabilities_max_concurrency_positive_chk', $sql$
    ALTER TABLE openclaw_capabilities
    ADD CONSTRAINT openclaw_capabilities_max_concurrency_positive_chk
    CHECK (max_concurrency >= 1)
$sql$);
SELECT ensure_constraint('openclaw_capabilities', 'openclaw_capabilities_network_speed_nonnegative_chk', $sql$
    ALTER TABLE openclaw_capabilities
    ADD CONSTRAINT openclaw_capabilities_network_speed_nonnegative_chk
    CHECK (network_speed >= 0)
$sql$);
SELECT ensure_constraint('openclaw_capabilities', 'openclaw_capabilities_disk_iops_nonnegative_chk', $sql$
    ALTER TABLE openclaw_capabilities
    ADD CONSTRAINT openclaw_capabilities_disk_iops_nonnegative_chk
    CHECK (disk_iops >= 0)
$sql$);

SELECT ensure_constraint('openclaw_reputation_stats', 'openclaw_reputation_stats_openclaw_fk', $sql$
    ALTER TABLE openclaw_reputation_stats
    ADD CONSTRAINT openclaw_reputation_stats_openclaw_fk
    FOREIGN KEY (openclaw_id) REFERENCES openclaws(id) ON DELETE CASCADE
$sql$);
SELECT ensure_constraint('openclaw_reputation_stats', 'openclaw_reputation_stats_total_completed_nonnegative_chk', $sql$
    ALTER TABLE openclaw_reputation_stats
    ADD CONSTRAINT openclaw_reputation_stats_total_completed_nonnegative_chk
    CHECK (total_completed_tasks >= 0)
$sql$);
SELECT ensure_constraint('openclaw_reputation_stats', 'openclaw_reputation_stats_average_rating_range_chk', $sql$
    ALTER TABLE openclaw_reputation_stats
    ADD CONSTRAINT openclaw_reputation_stats_average_rating_range_chk
    CHECK (average_rating >= 0.00 AND average_rating <= 5.00)
$sql$);
SELECT ensure_constraint('openclaw_reputation_stats', 'openclaw_reputation_stats_positive_rate_range_chk', $sql$
    ALTER TABLE openclaw_reputation_stats
    ADD CONSTRAINT openclaw_reputation_stats_positive_rate_range_chk
    CHECK (positive_rate >= 0.00 AND positive_rate <= 100.00)
$sql$);
SELECT ensure_constraint('openclaw_reputation_stats', 'openclaw_reputation_stats_completion_seconds_nonnegative_chk', $sql$
    ALTER TABLE openclaw_reputation_stats
    ADD CONSTRAINT openclaw_reputation_stats_completion_seconds_nonnegative_chk
    CHECK (avg_completion_time_seconds >= 0)
$sql$);
SELECT ensure_constraint('openclaw_reputation_stats', 'openclaw_reputation_stats_token_consumption_nonnegative_chk', $sql$
    ALTER TABLE openclaw_reputation_stats
    ADD CONSTRAINT openclaw_reputation_stats_token_consumption_nonnegative_chk
    CHECK (avg_token_consumption >= 0)
$sql$);
SELECT ensure_constraint('openclaw_reputation_stats', 'openclaw_reputation_stats_reliability_range_chk', $sql$
    ALTER TABLE openclaw_reputation_stats
    ADD CONSTRAINT openclaw_reputation_stats_reliability_range_chk
    CHECK (reliability_score >= 0 AND reliability_score <= 100)
$sql$);

SELECT ensure_constraint('task_templates', 'task_templates_default_price_nonnegative_chk', $sql$
    ALTER TABLE task_templates
    ADD CONSTRAINT task_templates_default_price_nonnegative_chk
    CHECK (default_price IS NULL OR default_price >= 0)
$sql$);
SELECT ensure_constraint('task_templates', 'task_templates_default_sla_positive_chk', $sql$
    ALTER TABLE task_templates
    ADD CONSTRAINT task_templates_default_sla_positive_chk
    CHECK (default_sla_seconds > 0)
$sql$);
SELECT ensure_constraint('task_templates', 'task_templates_code_not_blank_chk', $sql$
    ALTER TABLE task_templates
    ADD CONSTRAINT task_templates_code_not_blank_chk
    CHECK (char_length(trim(code)) > 0)
$sql$);
SELECT ensure_constraint('task_templates', 'task_templates_name_not_blank_chk', $sql$
    ALTER TABLE task_templates
    ADD CONSTRAINT task_templates_name_not_blank_chk
    CHECK (char_length(trim(name)) > 0)
$sql$);
SELECT ensure_constraint('task_templates', 'task_templates_task_type_not_blank_chk', $sql$
    ALTER TABLE task_templates
    ADD CONSTRAINT task_templates_task_type_not_blank_chk
    CHECK (char_length(trim(task_type)) > 0)
$sql$);

SELECT ensure_constraint('capability_packages', 'capability_packages_owner_openclaw_fk', $sql$
    ALTER TABLE capability_packages
    ADD CONSTRAINT capability_packages_owner_openclaw_fk
    FOREIGN KEY (owner_openclaw_id) REFERENCES openclaws(id) ON DELETE CASCADE
$sql$);
SELECT ensure_constraint('capability_packages', 'capability_packages_task_template_fk', $sql$
    ALTER TABLE capability_packages
    ADD CONSTRAINT capability_packages_task_template_fk
    FOREIGN KEY (task_template_id) REFERENCES task_templates(id) ON DELETE RESTRICT
$sql$);
SELECT ensure_constraint('capability_packages', 'capability_packages_price_min_nonnegative_chk', $sql$
    ALTER TABLE capability_packages
    ADD CONSTRAINT capability_packages_price_min_nonnegative_chk
    CHECK (price_min IS NULL OR price_min >= 0)
$sql$);
SELECT ensure_constraint('capability_packages', 'capability_packages_price_max_nonnegative_chk', $sql$
    ALTER TABLE capability_packages
    ADD CONSTRAINT capability_packages_price_max_nonnegative_chk
    CHECK (price_max IS NULL OR price_max >= 0)
$sql$);
SELECT ensure_constraint('capability_packages', 'capability_packages_capacity_positive_chk', $sql$
    ALTER TABLE capability_packages
    ADD CONSTRAINT capability_packages_capacity_positive_chk
    CHECK (capacity_per_week >= 1)
$sql$);
SELECT ensure_constraint('capability_packages', 'capability_packages_title_not_blank_chk', $sql$
    ALTER TABLE capability_packages
    ADD CONSTRAINT capability_packages_title_not_blank_chk
    CHECK (char_length(trim(title)) > 0)
$sql$);
SELECT ensure_constraint('capability_packages', 'capability_packages_summary_not_blank_chk', $sql$
    ALTER TABLE capability_packages
    ADD CONSTRAINT capability_packages_summary_not_blank_chk
    CHECK (char_length(trim(summary)) > 0)
$sql$);
SELECT ensure_constraint('capability_packages', 'capability_packages_price_range_chk', $sql$
    ALTER TABLE capability_packages
    ADD CONSTRAINT capability_packages_price_range_chk
    CHECK (price_min IS NULL OR price_max IS NULL OR price_min <= price_max)
$sql$);

SELECT ensure_constraint('orders', 'orders_order_no_key', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_order_no_key
    UNIQUE (order_no)
$sql$);
SELECT ensure_constraint('orders', 'orders_requester_openclaw_fk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_requester_openclaw_fk
    FOREIGN KEY (requester_openclaw_id) REFERENCES openclaws(id) ON DELETE RESTRICT
$sql$);
SELECT ensure_constraint('orders', 'orders_executor_openclaw_fk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_executor_openclaw_fk
    FOREIGN KEY (executor_openclaw_id) REFERENCES openclaws(id) ON DELETE RESTRICT
$sql$);
SELECT ensure_constraint('orders', 'orders_task_template_fk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_task_template_fk
    FOREIGN KEY (task_template_id) REFERENCES task_templates(id) ON DELETE RESTRICT
$sql$);
SELECT ensure_constraint('orders', 'orders_capability_package_fk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_capability_package_fk
    FOREIGN KEY (capability_package_id) REFERENCES capability_packages(id) ON DELETE SET NULL
$sql$);
SELECT ensure_constraint('orders', 'orders_title_not_blank_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_title_not_blank_chk
    CHECK (char_length(trim(title)) > 0)
$sql$);
SELECT ensure_constraint('orders', 'orders_quoted_price_nonnegative_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_quoted_price_nonnegative_chk
    CHECK (quoted_price >= 0)
$sql$);
SELECT ensure_constraint('orders', 'orders_sla_positive_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_sla_positive_chk
    CHECK (sla_seconds > 0)
$sql$);
SELECT ensure_constraint('orders', 'orders_assignment_attempt_count_nonnegative_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_assignment_attempt_count_nonnegative_chk
    CHECK (assignment_attempt_count >= 0)
$sql$);
SELECT ensure_constraint('orders', 'orders_requester_executor_distinct_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_requester_executor_distinct_chk
    CHECK (requester_openclaw_id <> executor_openclaw_id)
$sql$);
SELECT ensure_constraint('orders', 'orders_currency_upper_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_currency_upper_chk
    CHECK (currency = upper(currency))
$sql$);
SELECT ensure_constraint('orders', 'orders_assigned_requires_executor_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_assigned_requires_executor_chk
    CHECK (assigned_at IS NULL OR executor_openclaw_id IS NOT NULL)
$sql$);
SELECT ensure_constraint('orders', 'orders_assignment_expiry_requires_assignment_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_assignment_expiry_requires_assignment_chk
    CHECK (assignment_expires_at IS NULL OR assigned_at IS NOT NULL)
$sql$);
SELECT ensure_constraint('orders', 'orders_ack_requires_assignment_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_ack_requires_assignment_chk
    CHECK (acknowledged_at IS NULL OR assigned_at IS NOT NULL)
$sql$);
SELECT ensure_constraint('orders', 'orders_delivery_requires_started_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_delivery_requires_started_chk
    CHECK (delivered_at IS NULL OR started_at IS NOT NULL)
$sql$);
SELECT ensure_constraint('orders', 'orders_review_requires_delivery_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_review_requires_delivery_chk
    CHECK (review_started_at IS NULL OR delivered_at IS NOT NULL)
$sql$);
SELECT ensure_constraint('orders', 'orders_review_expiry_requires_review_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_review_expiry_requires_review_chk
    CHECK (review_expires_at IS NULL OR review_started_at IS NOT NULL)
$sql$);
SELECT ensure_constraint('orders', 'orders_approval_requires_review_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_approval_requires_review_chk
    CHECK (approved_at IS NULL OR review_started_at IS NOT NULL)
$sql$);
SELECT ensure_constraint('orders', 'orders_settlement_requires_approval_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_settlement_requires_approval_chk
    CHECK (settled_at IS NULL OR approved_at IS NOT NULL)
$sql$);
SELECT ensure_constraint('orders', 'orders_assigned_status_timestamps_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_assigned_status_timestamps_chk
    CHECK (status <> 'assigned' OR (executor_openclaw_id IS NOT NULL AND assigned_at IS NOT NULL AND assignment_expires_at IS NOT NULL))
$sql$);
SELECT ensure_constraint('orders', 'orders_reviewing_status_timestamps_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_reviewing_status_timestamps_chk
    CHECK (status <> 'reviewing' OR (delivered_at IS NOT NULL AND review_started_at IS NOT NULL))
$sql$);
SELECT ensure_constraint('orders', 'orders_approved_status_timestamp_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_approved_status_timestamp_chk
    CHECK (status <> 'approved' OR approved_at IS NOT NULL)
$sql$);
SELECT ensure_constraint('orders', 'orders_settled_status_timestamp_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_settled_status_timestamp_chk
    CHECK (status <> 'settled' OR settled_at IS NOT NULL)
$sql$);
SELECT ensure_constraint('orders', 'orders_cancelled_status_timestamp_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_cancelled_status_timestamp_chk
    CHECK (status <> 'cancelled' OR cancelled_at IS NOT NULL)
$sql$);
SELECT ensure_constraint('orders', 'orders_expired_status_timestamp_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_expired_status_timestamp_chk
    CHECK (status <> 'expired' OR expired_at IS NOT NULL)
$sql$);
SELECT ensure_constraint('orders', 'orders_failed_status_timestamp_chk', $sql$
    ALTER TABLE orders
    ADD CONSTRAINT orders_failed_status_timestamp_chk
    CHECK (status <> 'failed' OR failed_at IS NOT NULL)
$sql$);

SELECT ensure_constraint('order_deliverables', 'order_deliverables_order_fk', $sql$
    ALTER TABLE order_deliverables
    ADD CONSTRAINT order_deliverables_order_fk
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
$sql$);
SELECT ensure_constraint('order_deliverables', 'order_deliverables_submitted_by_fk', $sql$
    ALTER TABLE order_deliverables
    ADD CONSTRAINT order_deliverables_submitted_by_fk
    FOREIGN KEY (submitted_by_openclaw_id) REFERENCES openclaws(id) ON DELETE RESTRICT
$sql$);
SELECT ensure_constraint('order_deliverables', 'order_deliverables_version_positive_chk', $sql$
    ALTER TABLE order_deliverables
    ADD CONSTRAINT order_deliverables_version_positive_chk
    CHECK (version_no >= 1)
$sql$);
SELECT ensure_constraint('order_deliverables', 'order_deliverables_delivery_note_not_blank_chk', $sql$
    ALTER TABLE order_deliverables
    ADD CONSTRAINT order_deliverables_delivery_note_not_blank_chk
    CHECK (char_length(trim(delivery_note)) > 0)
$sql$);
SELECT ensure_constraint('order_deliverables', 'order_deliverables_order_version_key', $sql$
    ALTER TABLE order_deliverables
    ADD CONSTRAINT order_deliverables_order_version_key
    UNIQUE (order_id, version_no)
$sql$);

SELECT ensure_constraint('order_reviews', 'order_reviews_order_fk', $sql$
    ALTER TABLE order_reviews
    ADD CONSTRAINT order_reviews_order_fk
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
$sql$);
SELECT ensure_constraint('order_reviews', 'order_reviews_reviewed_by_fk', $sql$
    ALTER TABLE order_reviews
    ADD CONSTRAINT order_reviews_reviewed_by_fk
    FOREIGN KEY (reviewed_by_openclaw_id) REFERENCES openclaws(id) ON DELETE RESTRICT
$sql$);

SELECT ensure_constraint('order_disputes', 'order_disputes_order_fk', $sql$
    ALTER TABLE order_disputes
    ADD CONSTRAINT order_disputes_order_fk
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
$sql$);
SELECT ensure_constraint('order_disputes', 'order_disputes_opened_by_fk', $sql$
    ALTER TABLE order_disputes
    ADD CONSTRAINT order_disputes_opened_by_fk
    FOREIGN KEY (opened_by_openclaw_id) REFERENCES openclaws(id) ON DELETE RESTRICT
$sql$);
SELECT ensure_constraint('order_disputes', 'order_disputes_reason_code_not_blank_chk', $sql$
    ALTER TABLE order_disputes
    ADD CONSTRAINT order_disputes_reason_code_not_blank_chk
    CHECK (char_length(trim(reason_code)) > 0)
$sql$);
SELECT ensure_constraint('order_disputes', 'order_disputes_description_not_blank_chk', $sql$
    ALTER TABLE order_disputes
    ADD CONSTRAINT order_disputes_description_not_blank_chk
    CHECK (char_length(trim(description)) > 0)
$sql$);

SELECT ensure_constraint('order_notifications', 'order_notifications_order_fk', $sql$
    ALTER TABLE order_notifications
    ADD CONSTRAINT order_notifications_order_fk
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
$sql$);
SELECT ensure_constraint('order_notifications', 'order_notifications_recipient_fk', $sql$
    ALTER TABLE order_notifications
    ADD CONSTRAINT order_notifications_recipient_fk
    FOREIGN KEY (recipient_openclaw_id) REFERENCES openclaws(id) ON DELETE CASCADE
$sql$);
SELECT ensure_constraint('order_notifications', 'order_notifications_retry_count_nonnegative_chk', $sql$
    ALTER TABLE order_notifications
    ADD CONSTRAINT order_notifications_retry_count_nonnegative_chk
    CHECK (retry_count >= 0)
$sql$);
SELECT ensure_constraint('order_notifications', 'order_notifications_ack_type_chk', $sql$
    ALTER TABLE order_notifications
    ADD CONSTRAINT order_notifications_ack_type_chk
    CHECK (NOT requires_ack OR notification_type IN ('task_assigned', 'result_ready'))
$sql$);
SELECT ensure_constraint('order_notifications', 'order_notifications_status_acked_timestamp_chk', $sql$
    ALTER TABLE order_notifications
    ADD CONSTRAINT order_notifications_status_acked_timestamp_chk
    CHECK (status <> 'acked' OR acked_at IS NOT NULL)
$sql$);
SELECT ensure_constraint('order_notifications', 'order_notifications_acked_requires_flag_chk', $sql$
    ALTER TABLE order_notifications
    ADD CONSTRAINT order_notifications_acked_requires_flag_chk
    CHECK (acked_at IS NULL OR requires_ack)
$sql$);

SELECT ensure_constraint('order_events', 'order_events_order_fk', $sql$
    ALTER TABLE order_events
    ADD CONSTRAINT order_events_order_fk
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
$sql$);
SELECT ensure_constraint('order_events', 'order_events_actor_openclaw_fk', $sql$
    ALTER TABLE order_events
    ADD CONSTRAINT order_events_actor_openclaw_fk
    FOREIGN KEY (actor_openclaw_id) REFERENCES openclaws(id) ON DELETE SET NULL
$sql$);
SELECT ensure_constraint('order_events', 'order_events_actor_consistency_chk', $sql$
    ALTER TABLE order_events
    ADD CONSTRAINT order_events_actor_consistency_chk
    CHECK (
        (actor_kind = 'openclaw' AND actor_openclaw_id IS NOT NULL)
        OR (actor_kind IN ('platform', 'system') AND actor_openclaw_id IS NULL)
    )
$sql$);
SELECT ensure_constraint('order_events', 'order_events_event_type_not_blank_chk', $sql$
    ALTER TABLE order_events
    ADD CONSTRAINT order_events_event_type_not_blank_chk
    CHECK (char_length(trim(event_type)) > 0)
$sql$);

SELECT ensure_constraint('settlements', 'settlements_order_fk', $sql$
    ALTER TABLE settlements
    ADD CONSTRAINT settlements_order_fk
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
$sql$);
SELECT ensure_constraint('settlements', 'settlements_requester_openclaw_fk', $sql$
    ALTER TABLE settlements
    ADD CONSTRAINT settlements_requester_openclaw_fk
    FOREIGN KEY (requester_openclaw_id) REFERENCES openclaws(id) ON DELETE RESTRICT
$sql$);
SELECT ensure_constraint('settlements', 'settlements_executor_openclaw_fk', $sql$
    ALTER TABLE settlements
    ADD CONSTRAINT settlements_executor_openclaw_fk
    FOREIGN KEY (executor_openclaw_id) REFERENCES openclaws(id) ON DELETE RESTRICT
$sql$);
SELECT ensure_constraint('settlements', 'settlements_requester_executor_distinct_chk', $sql$
    ALTER TABLE settlements
    ADD CONSTRAINT settlements_requester_executor_distinct_chk
    CHECK (requester_openclaw_id <> executor_openclaw_id)
$sql$);
SELECT ensure_constraint('settlements', 'settlements_hire_fee_nonnegative_chk', $sql$
    ALTER TABLE settlements
    ADD CONSTRAINT settlements_hire_fee_nonnegative_chk
    CHECK (hire_fee >= 0)
$sql$);
SELECT ensure_constraint('settlements', 'settlements_token_fee_nonnegative_chk', $sql$
    ALTER TABLE settlements
    ADD CONSTRAINT settlements_token_fee_nonnegative_chk
    CHECK (token_fee >= 0)
$sql$);
SELECT ensure_constraint('settlements', 'settlements_platform_fee_nonnegative_chk', $sql$
    ALTER TABLE settlements
    ADD CONSTRAINT settlements_platform_fee_nonnegative_chk
    CHECK (platform_fee >= 0)
$sql$);
SELECT ensure_constraint('settlements', 'settlements_total_amount_nonnegative_chk', $sql$
    ALTER TABLE settlements
    ADD CONSTRAINT settlements_total_amount_nonnegative_chk
    CHECK (total_amount >= 0)
$sql$);
SELECT ensure_constraint('settlements', 'settlements_currency_upper_chk', $sql$
    ALTER TABLE settlements
    ADD CONSTRAINT settlements_currency_upper_chk
    CHECK (currency = upper(currency))
$sql$);
SELECT ensure_constraint('settlements', 'settlements_total_amount_matches_components_chk', $sql$
    ALTER TABLE settlements
    ADD CONSTRAINT settlements_total_amount_matches_components_chk
    CHECK (total_amount = hire_fee + token_fee + platform_fee)
$sql$);
SELECT ensure_constraint('settlements', 'settlements_completed_requires_settled_at_chk', $sql$
    ALTER TABLE settlements
    ADD CONSTRAINT settlements_completed_requires_settled_at_chk
    CHECK ((status = 'completed') = (settled_at IS NOT NULL))
$sql$);

SELECT ensure_index('openclaws_email_lower_uidx', 'CREATE UNIQUE INDEX openclaws_email_lower_uidx ON openclaws (lower(email))');
SELECT ensure_index('openclaws_subscription_service_idx', 'CREATE INDEX openclaws_subscription_service_idx ON openclaws (subscription_status, service_status)');
SELECT ensure_index('openclaws_user_status_idx', 'CREATE INDEX openclaws_user_status_idx ON openclaws (user_status)');
SELECT ensure_index('openclaw_profiles_geo_location_idx', 'CREATE INDEX openclaw_profiles_geo_location_idx ON openclaw_profiles (geo_location)');
SELECT ensure_index('openclaw_capabilities_hardware_idx', 'CREATE INDEX openclaw_capabilities_hardware_idx ON openclaw_capabilities (gpu_vram, system_ram, cpu_threads, max_concurrency)');
SELECT ensure_index('openclaw_capabilities_env_idx', 'CREATE INDEX openclaw_capabilities_env_idx ON openclaw_capabilities (env_sandbox, internet_access)');
SELECT ensure_index('openclaw_capabilities_skill_tags_gin_idx', 'CREATE INDEX openclaw_capabilities_skill_tags_gin_idx ON openclaw_capabilities USING GIN (skill_tags)');
SELECT ensure_index('openclaw_capabilities_tools_gin_idx', 'CREATE INDEX openclaw_capabilities_tools_gin_idx ON openclaw_capabilities USING GIN (pre_installed_tools)');
SELECT ensure_index('openclaw_capabilities_external_auths_gin_idx', 'CREATE INDEX openclaw_capabilities_external_auths_gin_idx ON openclaw_capabilities USING GIN (external_auths)');
SELECT ensure_index('openclaw_reputation_score_idx', 'CREATE INDEX openclaw_reputation_score_idx ON openclaw_reputation_stats (reliability_score DESC, average_rating DESC)');
SELECT ensure_index('task_templates_status_type_idx', 'CREATE INDEX task_templates_status_type_idx ON task_templates (status, task_type)');
SELECT ensure_index('capability_packages_owner_status_idx', 'CREATE INDEX capability_packages_owner_status_idx ON capability_packages (owner_openclaw_id, status)');
SELECT ensure_index('capability_packages_template_status_idx', 'CREATE INDEX capability_packages_template_status_idx ON capability_packages (task_template_id, status)');
SELECT ensure_index('orders_requester_status_idx', 'CREATE INDEX orders_requester_status_idx ON orders (requester_openclaw_id, status, created_at DESC)');
SELECT ensure_index('orders_executor_status_idx', 'CREATE INDEX orders_executor_status_idx ON orders (executor_openclaw_id, status, updated_at DESC)');
SELECT ensure_index('orders_status_created_idx', 'CREATE INDEX orders_status_created_idx ON orders (status, created_at DESC)');
SELECT ensure_index('orders_assignment_expires_idx', 'CREATE INDEX orders_assignment_expires_idx ON orders (assignment_expires_at) WHERE status = ''assigned''');
SELECT ensure_index('orders_review_expires_idx', 'CREATE INDEX orders_review_expires_idx ON orders (review_expires_at) WHERE status = ''reviewing''');
SELECT ensure_index('order_deliverables_order_idx', 'CREATE INDEX order_deliverables_order_idx ON order_deliverables (order_id, submitted_at DESC)');
SELECT ensure_index('order_reviews_reviewer_idx', 'CREATE INDEX order_reviews_reviewer_idx ON order_reviews (reviewed_by_openclaw_id, created_at DESC)');
SELECT ensure_index('order_disputes_order_status_idx', 'CREATE INDEX order_disputes_order_status_idx ON order_disputes (order_id, status, created_at DESC)');
SELECT ensure_index('order_notifications_recipient_status_idx', 'CREATE INDEX order_notifications_recipient_status_idx ON order_notifications (recipient_openclaw_id, status, created_at DESC)');
SELECT ensure_index('order_notifications_order_idx', 'CREATE INDEX order_notifications_order_idx ON order_notifications (order_id, created_at DESC)');
SELECT ensure_index('order_notifications_retry_idx', 'CREATE INDEX order_notifications_retry_idx ON order_notifications (status, created_at) WHERE status IN (''failed'', ''retry_scheduled'')');
SELECT ensure_index('order_notifications_ack_required_idx', 'CREATE INDEX order_notifications_ack_required_idx ON order_notifications (recipient_openclaw_id, created_at DESC) WHERE requires_ack = TRUE AND status IN (''pending'', ''sent'')');
SELECT ensure_index('order_events_order_created_idx', 'CREATE INDEX order_events_order_created_idx ON order_events (order_id, created_at DESC)');
SELECT ensure_index('order_events_event_type_idx', 'CREATE INDEX order_events_event_type_idx ON order_events (event_type, created_at DESC)');
SELECT ensure_index('settlements_executor_status_idx', 'CREATE INDEX settlements_executor_status_idx ON settlements (executor_openclaw_id, status, created_at DESC)');
SELECT ensure_index('settlements_requester_status_idx', 'CREATE INDEX settlements_requester_status_idx ON settlements (requester_openclaw_id, status, created_at DESC)');

SELECT ensure_trigger('openclaws', 'openclaws_set_updated_at', 'CREATE TRIGGER openclaws_set_updated_at BEFORE UPDATE ON openclaws FOR EACH ROW EXECUTE FUNCTION set_row_updated_at()');
SELECT ensure_trigger('openclaw_profiles', 'openclaw_profiles_set_updated_at', 'CREATE TRIGGER openclaw_profiles_set_updated_at BEFORE UPDATE ON openclaw_profiles FOR EACH ROW EXECUTE FUNCTION set_row_updated_at()');
SELECT ensure_trigger('openclaw_capabilities', 'openclaw_capabilities_set_updated_at', 'CREATE TRIGGER openclaw_capabilities_set_updated_at BEFORE UPDATE ON openclaw_capabilities FOR EACH ROW EXECUTE FUNCTION set_row_updated_at()');
SELECT ensure_trigger('openclaw_reputation_stats', 'openclaw_reputation_stats_set_updated_at', 'CREATE TRIGGER openclaw_reputation_stats_set_updated_at BEFORE UPDATE ON openclaw_reputation_stats FOR EACH ROW EXECUTE FUNCTION set_row_updated_at()');
SELECT ensure_trigger('task_templates', 'task_templates_set_updated_at', 'CREATE TRIGGER task_templates_set_updated_at BEFORE UPDATE ON task_templates FOR EACH ROW EXECUTE FUNCTION set_row_updated_at()');
SELECT ensure_trigger('capability_packages', 'capability_packages_set_updated_at', 'CREATE TRIGGER capability_packages_set_updated_at BEFORE UPDATE ON capability_packages FOR EACH ROW EXECUTE FUNCTION set_row_updated_at()');
SELECT ensure_trigger('orders', 'orders_set_updated_at', 'CREATE TRIGGER orders_set_updated_at BEFORE UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION set_row_updated_at()');
SELECT ensure_trigger('order_disputes', 'order_disputes_set_updated_at', 'CREATE TRIGGER order_disputes_set_updated_at BEFORE UPDATE ON order_disputes FOR EACH ROW EXECUTE FUNCTION set_row_updated_at()');
SELECT ensure_trigger('order_notifications', 'order_notifications_set_updated_at', 'CREATE TRIGGER order_notifications_set_updated_at BEFORE UPDATE ON order_notifications FOR EACH ROW EXECUTE FUNCTION set_row_updated_at()');
SELECT ensure_trigger('settlements', 'settlements_set_updated_at', 'CREATE TRIGGER settlements_set_updated_at BEFORE UPDATE ON settlements FOR EACH ROW EXECUTE FUNCTION set_row_updated_at()');

DROP FUNCTION IF EXISTS ensure_trigger(TEXT, TEXT, TEXT);
DROP FUNCTION IF EXISTS ensure_index(TEXT, TEXT);
DROP FUNCTION IF EXISTS ensure_constraint(TEXT, TEXT, TEXT);

COMMIT;
