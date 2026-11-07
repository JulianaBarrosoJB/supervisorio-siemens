CREATE TABLE IF NOT EXISTS motor_snapshots (
    event_id TEXT PRIMARY KEY,
    station_id TEXT NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL,
    measurements JSONB NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_motor_snapshots_station_time
ON motor_snapshots (station_id, captured_at DESC);
