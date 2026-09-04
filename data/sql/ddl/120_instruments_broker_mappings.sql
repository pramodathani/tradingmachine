CREATE TABLE IF NOT EXISTS instruments.broker_mappings (
    "instrument_id" UUID NOT NULL,
    "broker" TEXT NOT NULL,
    "broker_token" TEXT NOT NULL,
    "broker_symbol" TEXT,
    "lot_size" NUMERIC,
    "tick_size" NUMERIC,
    "mapping_date" DATE NOT NULL,
    PRIMARY KEY ("instrument_id", "broker", "mapping_date"),
    FOREIGN KEY ("instrument_id") REFERENCES instruments.master ("instrument_id")
);

CREATE INDEX IF NOT EXISTS broker_mappings_token_idx
    ON instruments.broker_mappings ("broker", "broker_token", "mapping_date");

CREATE INDEX IF NOT EXISTS broker_mappings_date_idx
    ON instruments.broker_mappings ("mapping_date", "instrument_id");

SELECT create_hypertable(
    'instruments.broker_mappings',
    by_range('mapping_date', INTERVAL '1 month'),
    if_not_exists => TRUE
);