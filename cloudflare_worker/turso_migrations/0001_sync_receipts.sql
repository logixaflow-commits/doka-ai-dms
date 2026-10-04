-- Apply only to the secondary Turso database.
-- Insert the event_id in the same Turso transaction as the mirrored changes.
-- A duplicate event_id means the outbox event has already been applied.
CREATE TABLE IF NOT EXISTS sync_receipts (
    event_id TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
