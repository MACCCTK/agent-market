BEGIN;

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
        ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'result_changes_requested';
        ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'result_rejected';
    END IF;
END
$$;

COMMIT;
