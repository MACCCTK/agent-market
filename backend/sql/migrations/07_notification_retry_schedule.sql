ALTER TABLE order_notifications
ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS order_notifications_retry_idx
ON order_notifications (status, next_retry_at)
WHERE status IN ('retry_scheduled', 'dead_letter');
