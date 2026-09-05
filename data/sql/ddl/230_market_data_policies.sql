ALTER TABLE market_data.ticks SET (
    timescaledb.enable_columnstore = true,
    timescaledb.segmentby = 'broker',
    timescaledb.orderby = 'instrument_id, arrival_time DESC'
);

CALL add_columnstore_policy(
    'market_data.ticks',
    after => INTERVAL '2 days',
    if_not_exists => TRUE
);

SELECT add_retention_policy(
    'market_data.ticks',
    drop_after => INTERVAL '90 days',
    if_not_exists => TRUE
);
