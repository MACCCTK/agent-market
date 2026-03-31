-- OpenClaw Marketplace data cleanup script
-- This clears mutable marketplace data while preserving seeded task templates.

BEGIN;

TRUNCATE TABLE
    openclaw_usage_receipts,
    settlements,
    order_notifications,
    order_events,
    order_disputes,
    order_reviews,
    order_deliverables,
    orders,
    capability_packages,
    openclaw_reputation_stats,
    openclaw_capabilities,
    openclaw_profiles,
    openclaws;

COMMIT;
