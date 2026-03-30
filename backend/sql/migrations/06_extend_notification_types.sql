DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notification_type') THEN
        ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'task_cancelled';
        ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'review_expired';
        ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'order_failed';
        ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'dispute_resolved';
    END IF;
END
$$;
