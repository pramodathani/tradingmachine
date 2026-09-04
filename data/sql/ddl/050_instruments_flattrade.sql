CREATE TABLE IF NOT EXISTS instruments.flattrade (
    "exchange" TEXT,
    "token" TEXT,
    "lotsize" TEXT,
    "symbol" TEXT,
    "tradingsymbol" TEXT,
    "instrument" TEXT,
    "expiry" TEXT,
    "strike" TEXT,
    "optiontype" TEXT,
    "download_date" DATE NOT NULL
);

SELECT create_hypertable(
    'instruments.flattrade',
    by_range('download_date', INTERVAL '1 month'),
    if_not_exists => TRUE
);
