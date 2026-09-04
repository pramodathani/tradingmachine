CREATE TABLE IF NOT EXISTS instruments.zerodha (
    "instrument_token" TEXT,
    "exchange_token" TEXT,
    "tradingsymbol" TEXT,
    "name" TEXT,
    "last_price" TEXT,
    "expiry" TEXT,
    "strike" TEXT,
    "tick_size" TEXT,
    "lot_size" TEXT,
    "instrument_type" TEXT,
    "segment" TEXT,
    "exchange" TEXT,
    "download_date" DATE NOT NULL
);

SELECT create_hypertable(
    'instruments.zerodha',
    by_range('download_date', INTERVAL '1 month'),
    if_not_exists => TRUE
);
