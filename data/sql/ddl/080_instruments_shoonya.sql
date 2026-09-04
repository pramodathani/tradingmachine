CREATE TABLE IF NOT EXISTS instruments.shoonya (
    "exchange" TEXT,
    "token" TEXT,
    "lotsize" TEXT,
    "symbol" TEXT,
    "tradingsymbol" TEXT,
    "instrument" TEXT,
    "ticksize" TEXT,
    "expiry" TEXT,
    "optiontype" TEXT,
    "strikeprice" TEXT,
    "precision" TEXT,
    "multiplier" TEXT,
    "gngd" TEXT,
    "download_date" DATE NOT NULL
);

SELECT create_hypertable(
    'instruments.shoonya',
    by_range('download_date', INTERVAL '1 month'),
    if_not_exists => TRUE
);
