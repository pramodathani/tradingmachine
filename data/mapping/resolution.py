"""
Look-ups over the mapped instrument tables.

Three questions can be asked, and between them they close the loop from an instrument identity to a broker's own raw row and back:

- ``resolve_broker_tokens`` goes from an identity to every broker's token for it, which is what placing an order or requesting a quote needs.
- ``resolve_identity`` goes the other way, from a broker's tokens back to the unified identities, which is what reading a position or holding back from a broker needs.
- ``resolve_raw_row`` goes from a broker token to that broker's full raw row, which is the escape hatch for anything the mapped tables do not carry.

The third exists because a broker's own order or quote endpoint sometimes needs an identifier the mapped tables have no column for. Fyers is the known case: the ``broker_symbol`` stored for it is a human-readable description, not a tradeable ticker, so its order symbol has to be constructed from raw fields. Because ``broker_token`` is each broker's own join key into its raw table, that row is always one lookup away.

Every function takes an ``as_of_date`` and uses the latest mapping on or before it, so a lookup for a past date sees what was mapped then rather than what is mapped now.
"""

import pandas as pd
from sqlalchemy import text

from data.mapping.base import instrument_id


def resolve_broker_tokens(engine, exchange, segment, shape, identity, as_of_date):
    """
    Find every broker's token for one instrument identity.

    Args:
        engine: A SQLAlchemy engine for the black_box database.
        exchange (str): Canonical lowercase exchange name, for example "nse".
        segment (str): Exchange-prefixed segment value, for example "nse_equities".
        shape (str): One of "security", "future", or "option".
        identity (dict): The identity fields for the shape, for example {"symbol": "RELIANCE"}.
        as_of_date (datetime.date): Use the latest mapping on or before this date.

    Returns:
        tuple: A (mapping_date, rows) pair, where mapping_date is the date the answer came from (datetime.date, or None when the instrument was never mapped) and rows is a list of dicts with keys "broker", "broker_token", "broker_symbol", "lot_size", and "tick_size".
    """
    computed_id = instrument_id(exchange, segment, shape, identity)
    with engine.connect() as connection:
        latest = connection.execute(
            text(
                "SELECT max(mapping_date) AS mapping_date FROM instruments.broker_mappings "
                "WHERE instrument_id = :instrument_id AND mapping_date <= :as_of_date"
            ),
            {
                "instrument_id": computed_id,
                "as_of_date": as_of_date,
            },
        ).one()
        mapping_date = latest.mapping_date
        if mapping_date is None:
            return (None, [])

        result = connection.execute(
            text(
                "SELECT broker, broker_token, broker_symbol, lot_size, tick_size "
                "FROM instruments.broker_mappings "
                "WHERE instrument_id = :instrument_id AND mapping_date = :mapping_date "
                "ORDER BY broker"
            ),
            {
                "instrument_id": computed_id,
                "mapping_date": mapping_date,
            },
        ).all()

    rows = []
    for row in result:
        rows.append(
            {
                "broker": row.broker,
                "broker_token": row.broker_token,
                "broker_symbol": row.broker_symbol,
                "lot_size": row.lot_size,
                "tick_size": row.tick_size,
            }
        )
    return (mapping_date, rows)


def resolve_identity(engine, broker, broker_tokens, as_of_date):
    """
    Find the unified identity behind each of one broker's tokens.

    A token can point at more than one instrument, which happens when a broker's file reuses it, so the most recent mapping wins and the symbol breaks any remaining tie. That keeps the answer stable from one call to the next rather than depending on row order.

    Args:
        engine: A SQLAlchemy engine for the black_box database.
        broker (str): The broker name, for example "zerodha".
        broker_tokens (list[str]): The broker's own tokens to resolve.
        as_of_date (datetime.date): Use the latest mapping on or before this date.

    Returns:
        dict: Mapping of broker token to a dict with keys "instrument_id", "exchange", "segment", "shape", "symbol", "underlying_symbol", "expiry_date", "strike_price", "option_type", and "mapping_date". Tokens with no mapping are absent from the result.
    """
    if not broker_tokens:
        return {}

    tokens = []
    for token in broker_tokens:
        tokens.append(str(token))

    with engine.connect() as connection:
        result = connection.execute(
            text(
                "SELECT DISTINCT ON (b.broker_token) "
                "  b.broker_token, b.mapping_date, m.instrument_id, m.exchange, m.segment, m.shape, "
                "  m.symbol, m.underlying_symbol, m.expiry_date, m.strike_price, m.option_type "
                "FROM instruments.broker_mappings b "
                "JOIN instruments.master m ON m.instrument_id = b.instrument_id "
                "WHERE b.broker = :broker AND b.mapping_date <= :as_of_date "
                "  AND b.broker_token = ANY(:tokens) "
                "ORDER BY b.broker_token, b.mapping_date DESC, m.symbol ASC"
            ),
            {
                "broker": broker,
                "as_of_date": as_of_date,
                "tokens": tokens,
            },
        ).all()

    resolved = {}
    for row in result:
        resolved[row.broker_token] = {
            "instrument_id": str(row.instrument_id),
            "exchange": row.exchange,
            "segment": row.segment,
            "shape": row.shape,
            "symbol": row.symbol,
            "underlying_symbol": row.underlying_symbol,
            "expiry_date": row.expiry_date,
            "strike_price": row.strike_price,
            "option_type": row.option_type,
            "mapping_date": row.mapping_date,
        }
    return resolved


def resolve_raw_row(engine, broker, broker_token, as_of_date):
    """
    Fetch a broker's full raw instrument row for one of its own tokens.

    Args:
        engine: A SQLAlchemy engine for the black_box database.
        broker (str): The broker name, which is also its raw table name under the instruments schema.
        broker_token (str): The broker's own token, as stored in instruments.broker_mappings.
        as_of_date (datetime.date): Use the latest downloaded snapshot on or before this date.

    Returns:
        dict | None: Every column of the raw row, or None when that broker's file has no such token on or before the date.

    Raises:
        ValueError: If the broker name is not one of the mapped brokers, since the name is interpolated into the table name.
    """
    from data.mapping.run_mapping import PROCESSING_ORDER

    if broker not in PROCESSING_ORDER:
        raise ValueError(f"{broker!r} is not one of the mapped brokers: {PROCESSING_ORDER}")

    token_column = RAW_TOKEN_COLUMNS[broker]
    with engine.connect() as connection:
        raw = pd.read_sql(
            text(
                f"SELECT * FROM instruments.{broker} "
                f"WHERE {token_column} = :token AND download_date <= :as_of_date "
                f"ORDER BY download_date DESC LIMIT 1"
            ),
            connection,
            params={
                "token": str(broker_token),
                "as_of_date": as_of_date,
            },
        )
    if raw.empty:
        return None
    return raw.to_dict("records")[0]


RAW_TOKEN_COLUMNS = {
    "dhan": "security_id",
    "kotak": "psymbol",
    "groww": "exchange_token",
    "stoxkart": "token",
    "fyers": "fytoken",
    "wisdom_capital": "exchangeinstrumentid",
    "indmoney": "security_id",
    "flattrade": "token",
    "shoonya": "token",
    "zerodha": "instrument_token",
}
