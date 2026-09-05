CREATE TABLE IF NOT EXISTS market_data.ticks (
    "arrival_time" TIMESTAMPTZ NOT NULL,
    "instrument_id" UUID,
    "broker" TEXT NOT NULL,
    "broker_token" TEXT NOT NULL,
    "price_divisor" INTEGER NOT NULL,
    "tick_mode" TEXT NOT NULL,
    "tradable" BOOLEAN NOT NULL,
    "exchange_timestamp" TIMESTAMPTZ,
    "last_trade_time" TIMESTAMPTZ,
    "last_price" BIGINT,
    "last_traded_quantity" BIGINT,
    "average_traded_price" BIGINT,
    "volume_traded" BIGINT,
    "total_buy_quantity" BIGINT,
    "total_sell_quantity" BIGINT,
    "open_price" BIGINT,
    "high_price" BIGINT,
    "low_price" BIGINT,
    "close_price" BIGINT,
    "open_interest" BIGINT,
    "open_interest_day_high" BIGINT,
    "open_interest_day_low" BIGINT,
    "bid_quantities" BIGINT[],
    "bid_prices" BIGINT[],
    "bid_orders" INTEGER[],
    "ask_quantities" BIGINT[],
    "ask_prices" BIGINT[],
    "ask_orders" INTEGER[],
    "shard_number" SMALLINT NOT NULL
);

SELECT create_hypertable(
    'market_data.ticks',
    by_range('arrival_time', INTERVAL '1 hour'),
    if_not_exists => TRUE
);
