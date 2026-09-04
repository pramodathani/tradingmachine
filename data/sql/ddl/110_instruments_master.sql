CREATE TABLE IF NOT EXISTS instruments.master (
    "instrument_id" UUID NOT NULL,
    "exchange" TEXT NOT NULL,
    "segment" TEXT NOT NULL,
    "shape" TEXT NOT NULL,
    "symbol" TEXT,
    "underlying_symbol" TEXT,
    "expiry_date" DATE,
    "strike_price" NUMERIC,
    "option_type" TEXT,
    "first_seen_date" DATE NOT NULL,
    "last_seen_date" DATE NOT NULL,
    PRIMARY KEY ("instrument_id")
);

CREATE UNIQUE INDEX IF NOT EXISTS master_security_uk
    ON instruments.master ("exchange", "segment", "symbol") WHERE "shape" = 'security';

CREATE UNIQUE INDEX IF NOT EXISTS master_future_uk
    ON instruments.master ("exchange", "segment", "underlying_symbol", "expiry_date") WHERE "shape" = 'future';

CREATE UNIQUE INDEX IF NOT EXISTS master_option_uk
    ON instruments.master ("exchange", "segment", "underlying_symbol", "expiry_date", "strike_price", "option_type") WHERE "shape" = 'option';

CREATE INDEX IF NOT EXISTS master_segment_idx ON instruments.master ("segment", "exchange");