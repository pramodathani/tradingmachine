CREATE OR REPLACE FUNCTION market_data.divide_prices("wire_prices" BIGINT[], "price_divisor" INTEGER)
RETURNS NUMERIC[]
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $$
    SELECT array_agg(trim_scale("value"::NUMERIC / "price_divisor") ORDER BY "ordinality")
    FROM unnest("wire_prices") WITH ORDINALITY AS t("value", "ordinality");
$$;

CREATE OR REPLACE VIEW market_data.ticks_priced AS
SELECT
    "arrival_time",
    "instrument_id",
    "broker",
    "broker_token",
    "price_divisor",
    "tick_mode",
    "tradable",
    "exchange_timestamp",
    "last_trade_time",
    trim_scale("last_price"::NUMERIC / "price_divisor") AS "last_price",
    "last_traded_quantity",
    trim_scale("average_traded_price"::NUMERIC / "price_divisor") AS "average_traded_price",
    "volume_traded",
    "total_buy_quantity",
    "total_sell_quantity",
    trim_scale("open_price"::NUMERIC / "price_divisor") AS "open_price",
    trim_scale("high_price"::NUMERIC / "price_divisor") AS "high_price",
    trim_scale("low_price"::NUMERIC / "price_divisor") AS "low_price",
    trim_scale("close_price"::NUMERIC / "price_divisor") AS "close_price",
    "open_interest",
    "open_interest_day_high",
    "open_interest_day_low",
    "bid_quantities",
    market_data.divide_prices("bid_prices", "price_divisor") AS "bid_prices",
    "bid_orders",
    "ask_quantities",
    market_data.divide_prices("ask_prices", "price_divisor") AS "ask_prices",
    "ask_orders",
    "shard_number"
FROM market_data.ticks;
