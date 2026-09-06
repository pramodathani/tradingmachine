"""
Checks that Zerodha's binary frames are being decoded correctly.

The synthetic checks in this module build frames byte by byte from known values and assert that every field comes back exactly, which needs no network and no market hours. They exist because a binary parser fails silently: a wrong offset or a field read at the wrong width produces numbers that are still plausible prices and quantities, and a model trading on them would give no sign that anything was wrong.

Each check targets a specific way this parser could be wrong rather than simply exercising the happy path. The index ordering check would fail if index packets were decoded with the tradeable reader, the depth check would fail if the two byte order count were read as four bytes, and the divisor checks would fail if the currency segments were treated like every other segment.

Run with: python3 -m stream.zerodha.verify_stream --synthetic
"""

import argparse
import asyncio
import struct
import sys
from datetime import datetime

import requests
from sqlalchemy import create_engine, text as sql_text

from stream.zerodha.connection import ZerodhaConnection
from stream.zerodha.credentials import websocket_credentials
from stream.zerodha.packets import decode_frame
from utilities.configuration import postgres_configuration

ARRIVAL_TIME = datetime(2026, 9, 5, 10, 30, 0)

NSE_EQUITY_TOKEN = 738561
NSE_CURRENCY_TOKEN = 12345 * 256 + 3
BSE_CURRENCY_TOKEN = 12345 * 256 + 6
NSE_COMMODITY_TOKEN = 12345 * 256 + 12
INDEX_TOKEN = 256265
UNKNOWN_SEGMENT_TOKEN = 12345 * 256 + 17


def build_frame(packets):
    """
    Assemble a binary websocket frame out of already-built packets.

    Args:
        packets (list[bytes]): The packets to place in the frame, in order.

    Returns:
        bytes: A frame carrying a two byte packet count followed by each packet introduced by its own two byte length.
    """
    frame = struct.pack(">H", len(packets))
    for packet in packets:
        frame = frame + struct.pack(">H", len(packet)) + packet
    return frame


def build_ltp_packet(instrument_token, last_price):
    """
    Build an eight byte last traded price packet.

    Args:
        instrument_token (int): The instrument token to place in the packet.
        last_price (int): The last traded price in wire units.

    Returns:
        bytes: The eight byte packet.
    """
    return struct.pack(">II", instrument_token, last_price)


def build_index_packet(instrument_token, last_price, high_price, low_price, open_price, close_price, price_change, exchange_timestamp=None):
    """
    Build a twenty eight or thirty two byte index packet.

    The field order after the last traded price is high, low, open, close, which is deliberately different from the tradeable packet's open, high, low, close.

    Args:
        instrument_token (int): The instrument token to place in the packet.
        last_price (int): The last traded price in wire units.
        high_price (int): The day's high in wire units.
        low_price (int): The day's low in wire units.
        open_price (int): The day's open in wire units.
        close_price (int): The day's close in wire units.
        price_change (int): The exchange's own price change field, which the parser ignores.
        exchange_timestamp (int | None): Seconds since the Unix epoch, or None to build a twenty eight byte quote packet instead of a thirty two byte full packet.

    Returns:
        bytes: The packet, twenty eight bytes when exchange_timestamp is None and thirty two bytes otherwise.
    """
    packet = struct.pack(
        ">IIIIIII",
        instrument_token,
        last_price,
        high_price,
        low_price,
        open_price,
        close_price,
        price_change,
    )
    if exchange_timestamp is None:
        return packet
    return packet + struct.pack(">I", exchange_timestamp)


def build_tradable_packet(instrument_token, values, depth=None):
    """
    Build a forty four byte quote packet, or a one hundred and eighty four byte full packet when depth is supplied.

    Args:
        instrument_token (int): The instrument token to place in the packet.
        values (dict): Wire values keyed by the names used in the decoded tick, covering last_price, last_traded_quantity, average_traded_price, volume_traded, total_buy_quantity, total_sell_quantity, open_price, high_price, low_price and close_price, and additionally last_trade_time, open_interest, open_interest_day_high, open_interest_day_low and exchange_timestamp for a full packet.
        depth (dict | None): Depth to append, holding "bids" and "asks", each a list of five quantity, price and order count triples. None builds a quote packet.

    Returns:
        bytes: The packet.
    """
    packet = struct.pack(
        ">IIIIIIIIIII",
        instrument_token,
        values["last_price"],
        values["last_traded_quantity"],
        values["average_traded_price"],
        values["volume_traded"],
        values["total_buy_quantity"],
        values["total_sell_quantity"],
        values["open_price"],
        values["high_price"],
        values["low_price"],
        values["close_price"],
    )
    if depth is None:
        return packet

    packet = packet + struct.pack(
        ">IIIII",
        values["last_trade_time"],
        values["open_interest"],
        values["open_interest_day_high"],
        values["open_interest_day_low"],
        values["exchange_timestamp"],
    )
    for side in ("bids", "asks"):
        for quantity, price, orders in depth[side]:
            packet = packet + struct.pack(">IIH2x", quantity, price, orders)
    return packet


def check_heartbeat_decodes_to_nothing():
    """
    A one byte heartbeat must decode to no ticks rather than raising.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    ticks = decode_frame(b"\x01", ARRIVAL_TIME)
    empty = decode_frame(b"", ARRIVAL_TIME)
    passed = ticks == [] and empty == []
    return ("heartbeat and empty frames decode to nothing", passed, f"one byte gave {ticks!r}, empty gave {empty!r}")


def check_ltp_packet():
    """
    An eight byte packet must yield the token and the last traded price.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    frame = build_frame([build_ltp_packet(NSE_EQUITY_TOKEN, 284155)])
    ticks = decode_frame(frame, ARRIVAL_TIME)
    tick = ticks[0]
    passed = (
        len(ticks) == 1
        and tick["instrument_token"] == NSE_EQUITY_TOKEN
        and tick["last_price"] == 284155
        and tick["tick_mode"] == "ltp"
        and tick["tradable"] is True
        and tick["price_divisor"] == 100
    )
    return ("ltp packet", passed, f"token {tick['instrument_token']} price {tick['last_price']} mode {tick['tick_mode']}")


def check_quote_packet():
    """
    A forty four byte packet must yield every field in open, high, low, close order and no depth.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    values = {
        "last_price": 284155,
        "last_traded_quantity": 12,
        "average_traded_price": 283812,
        "volume_traded": 4182933,
        "total_buy_quantity": 118422,
        "total_sell_quantity": 96311,
        "open_price": 282000,
        "high_price": 285190,
        "low_price": 281505,
        "close_price": 281935,
    }
    frame = build_frame([build_tradable_packet(NSE_EQUITY_TOKEN, values)])
    tick = decode_frame(frame, ARRIVAL_TIME)[0]
    mismatched = []
    for name in values:
        if tick[name] != values[name]:
            mismatched.append(f"{name} expected {values[name]} got {tick[name]}")
    passed = not mismatched and tick["tick_mode"] == "quote" and "bid_prices" not in tick
    return ("quote packet, open high low close order", passed, "; ".join(mismatched) or f"all ten fields exact, mode {tick['tick_mode']}, depth absent")


def check_full_packet_and_depth():
    """
    A one hundred and eighty four byte packet must yield open interest, both timestamps and five depth levels a side.

    The order counts are chosen so that reading the two byte order field as four bytes would shift every later depth entry, which would show up as wrong prices rather than only wrong order counts.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    values = {
        "last_price": 284155,
        "last_traded_quantity": 12,
        "average_traded_price": 283812,
        "volume_traded": 4182933,
        "total_buy_quantity": 118422,
        "total_sell_quantity": 96311,
        "open_price": 282000,
        "high_price": 285190,
        "low_price": 281505,
        "close_price": 281935,
        "last_trade_time": 1788609598,
        "open_interest": 21845,
        "open_interest_day_high": 30000,
        "open_interest_day_low": 11000,
        "exchange_timestamp": 1788609599,
    }
    depth = {
        "bids": [
            (53, 284150, 1),
            (120, 284145, 3),
            (8, 284140, 1),
            (400, 284135, 7),
            (17, 284130, 2),
        ],
        "asks": [
            (43, 284160, 2),
            (90, 284165, 4),
            (250, 284170, 9),
            (11, 284175, 1),
            (600, 284180, 65535),
        ],
    }
    frame = build_frame([build_tradable_packet(NSE_EQUITY_TOKEN, values, depth)])
    tick = decode_frame(frame, ARRIVAL_TIME)[0]

    problems = []
    if tick["tick_mode"] != "full":
        problems.append(f"mode {tick['tick_mode']}")
    if tick["open_interest"] != 21845:
        problems.append(f"open interest {tick['open_interest']}")
    if tick["exchange_timestamp"] != datetime.fromtimestamp(1788609599):
        problems.append(f"exchange timestamp {tick['exchange_timestamp']}")
    if tick["last_trade_time"] != datetime.fromtimestamp(1788609598):
        problems.append(f"last trade time {tick['last_trade_time']}")

    expected_bid_prices = [284150, 284145, 284140, 284135, 284130]
    expected_ask_prices = [284160, 284165, 284170, 284175, 284180]
    expected_bid_orders = [1, 3, 1, 7, 2]
    expected_ask_orders = [2, 4, 9, 1, 65535]
    if tick["bid_prices"] != expected_bid_prices:
        problems.append(f"bid prices {tick['bid_prices']}")
    if tick["ask_prices"] != expected_ask_prices:
        problems.append(f"ask prices {tick['ask_prices']}")
    if tick["bid_orders"] != expected_bid_orders:
        problems.append(f"bid orders {tick['bid_orders']}")
    if tick["ask_orders"] != expected_ask_orders:
        problems.append(f"ask orders {tick['ask_orders']}")
    if tick["bid_quantities"] != [53, 120, 8, 400, 17]:
        problems.append(f"bid quantities {tick['bid_quantities']}")

    passed = not problems
    return ("full packet, depth and the two byte order count", passed, "; ".join(problems) or "all fields exact, five levels a side, 65535 orders survived")


def check_index_field_order():
    """
    An index packet must be read as high, low, open, close, not as open, high, low, close.

    The five prices are deliberately all different, so decoding an index with the tradeable reader would put the high where the open belongs and fail this check.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    frame = build_frame([
        build_index_packet(
            INDEX_TOKEN,
            last_price=2500000,
            high_price=2530000,
            low_price=2470000,
            open_price=2490000,
            close_price=2480000,
            price_change=20000,
            exchange_timestamp=1788609599,
        ),
    ])
    tick = decode_frame(frame, ARRIVAL_TIME)[0]
    problems = []
    if tick["high_price"] != 2530000:
        problems.append(f"high {tick['high_price']}")
    if tick["low_price"] != 2470000:
        problems.append(f"low {tick['low_price']}")
    if tick["open_price"] != 2490000:
        problems.append(f"open {tick['open_price']}")
    if tick["close_price"] != 2480000:
        problems.append(f"close {tick['close_price']}")
    if tick["tradable"] is not False:
        problems.append("marked tradable")
    if tick["tick_mode"] != "index_full":
        problems.append(f"mode {tick['tick_mode']}")
    if "bid_prices" in tick or "volume_traded" in tick:
        problems.append("carries depth or volume")
    passed = not problems
    return ("index packet, high low open close order", passed, "; ".join(problems) or "high/low/open/close each in the right place, no depth, not tradable")


def check_index_quote_packet():
    """
    A twenty eight byte index packet must decode with no exchange timestamp.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    frame = build_frame([
        build_index_packet(
            INDEX_TOKEN,
            last_price=2500000,
            high_price=2530000,
            low_price=2470000,
            open_price=2490000,
            close_price=2480000,
            price_change=20000,
        ),
    ])
    tick = decode_frame(frame, ARRIVAL_TIME)[0]
    passed = tick["tick_mode"] == "index_quote" and tick["exchange_timestamp"] is None and tick["open_price"] == 2490000
    return ("index quote packet", passed, f"mode {tick['tick_mode']} timestamp {tick['exchange_timestamp']}")


def check_price_divisors():
    """
    The two currency segments must use their own divisors and every other segment must use a hundred.

    Segment 12 is NSE Commodity, which postdates both of Zerodha's client libraries and divides by ten thousand rather than a hundred, a value established against Zerodha's own quote endpoint rather than guessed from tick sizes. Segment 17 does not exist today and must fall through to the ordinary hundred rather than being rejected.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    expected = [
        (NSE_EQUITY_TOKEN, 100, "nse"),
        (NSE_CURRENCY_TOKEN, 10000000, "cds"),
        (BSE_CURRENCY_TOKEN, 10000, "bcd"),
        (NSE_COMMODITY_TOKEN, 10000, "nco"),
        (INDEX_TOKEN, 100, "indices"),
        (UNKNOWN_SEGMENT_TOKEN, 100, "segment_17"),
    ]
    problems = []
    for token, divisor, name in expected:
        frame = build_frame([build_ltp_packet(token, 861234500)])
        tick = decode_frame(frame, ARRIVAL_TIME)[0]
        if tick["price_divisor"] != divisor:
            problems.append(f"token {token} divisor {tick['price_divisor']} expected {divisor}")
        if tick["kite_segment"] != name:
            problems.append(f"token {token} segment {tick['kite_segment']} expected {name}")
    passed = not problems
    return ("price divisors and segment names", passed, "; ".join(problems) or "nse 100, cds 10000000, bcd 10000, nco 10000, indices 100, unknown 100")


def check_implausible_timestamps():
    """
    A zero or nonsensical exchange timestamp must become no timestamp rather than a wrong one.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    values = {
        "last_price": 100,
        "last_traded_quantity": 1,
        "average_traded_price": 100,
        "volume_traded": 1,
        "total_buy_quantity": 1,
        "total_sell_quantity": 1,
        "open_price": 100,
        "high_price": 100,
        "low_price": 100,
        "close_price": 100,
        "last_trade_time": 0,
        "open_interest": 0,
        "open_interest_day_high": 0,
        "open_interest_day_low": 0,
        "exchange_timestamp": 4294967295,
    }
    depth = {
        "bids": [(0, 0, 0)] * 5,
        "asks": [(0, 0, 0)] * 5,
    }
    frame = build_frame([build_tradable_packet(NSE_EQUITY_TOKEN, values, depth)])
    tick = decode_frame(frame, ARRIVAL_TIME)[0]
    passed = tick["last_trade_time"] is None and tick["exchange_timestamp"] is None
    return ("implausible timestamps become None", passed, f"last trade time {tick['last_trade_time']}, exchange timestamp {tick['exchange_timestamp']}")


def check_multiple_packets_in_one_frame():
    """
    A frame carrying packets of several different lengths must decode all of them, in order.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    values = {
        "last_price": 284155,
        "last_traded_quantity": 12,
        "average_traded_price": 283812,
        "volume_traded": 4182933,
        "total_buy_quantity": 118422,
        "total_sell_quantity": 96311,
        "open_price": 282000,
        "high_price": 285190,
        "low_price": 281505,
        "close_price": 281935,
    }
    frame = build_frame([
        build_ltp_packet(NSE_EQUITY_TOKEN, 111),
        build_index_packet(INDEX_TOKEN, 2500000, 2530000, 2470000, 2490000, 2480000, 0),
        build_tradable_packet(NSE_CURRENCY_TOKEN, values),
    ])
    ticks = decode_frame(frame, ARRIVAL_TIME)
    modes = []
    for tick in ticks:
        modes.append(tick["tick_mode"])
    passed = modes == ["ltp", "index_quote", "quote"] and ticks[0]["last_price"] == 111 and ticks[2]["price_divisor"] == 10000000
    return ("mixed packet lengths in one frame", passed, f"decoded {len(ticks)} packets as {modes}")


def check_truncated_frame_does_not_raise():
    """
    A frame that ends mid packet must return what was read rather than raising.

    An exception here would run inside the socket read loop and would take down a connection carrying several thousand instruments over one malformed frame.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    frame = build_frame([
        build_ltp_packet(NSE_EQUITY_TOKEN, 284155),
        build_ltp_packet(INDEX_TOKEN, 2500000),
    ])
    problems = []
    for cut in range(1, len(frame)):
        try:
            decode_frame(frame[:cut], ARRIVAL_TIME)
        except Exception as error:
            problems.append(f"cut at {cut} raised {type(error).__name__}: {error}")

    lying_count = struct.pack(">H", 50) + frame[2:]
    try:
        ticks = decode_frame(lying_count, ARRIVAL_TIME)
    except Exception as error:
        problems.append(f"overstated packet count raised {type(error).__name__}: {error}")
        ticks = []

    passed = not problems and len(ticks) == 2
    return ("truncated and overstated frames never raise", passed, "; ".join(problems) or f"all {len(frame) - 1} truncations handled, overstated count gave {len(ticks)} packets")


SYNTHETIC_CHECKS = [
    check_heartbeat_decodes_to_nothing,
    check_ltp_packet,
    check_quote_packet,
    check_full_packet_and_depth,
    check_index_field_order,
    check_index_quote_packet,
    check_price_divisors,
    check_implausible_timestamps,
    check_multiple_packets_in_one_frame,
    check_truncated_frame_does_not_raise,
]


def run_synthetic():
    """
    Run every synthetic check and report the results.

    Returns:
        int: The number of checks that failed.
    """
    failures = 0
    print("Synthetic decoding checks")
    print()
    for check in SYNTHETIC_CHECKS:
        name, passed, detail = check()
        marker = "PASS" if passed else "FAIL"
        if not passed:
            failures = failures + 1
        print(f"  {marker}  {name}")
        print(f"        {detail}")
    print()
    print(f"{len(SYNTHETIC_CHECKS) - failures} of {len(SYNTHETIC_CHECKS)} checks passed.")
    return failures


QUOTE_ENDPOINT = "https://api.kite.trade/quote"

VERIFICATION_TOLERANCE = 0.0001


def select_verification_instruments(engine, per_exchange):
    """
    Choose instruments to check against Zerodha's own quote endpoint, spanning as many segments as possible.

    Expired contracts are excluded, because the quote endpoint will not price them and they would produce gaps rather than comparisons. Futures are preferred over options within a derivative exchange, since they are more likely to have traded and therefore to carry a full set of values worth comparing.

    Args:
        engine: A SQLAlchemy engine for the tradingmachine database.
        per_exchange (int): How many instruments to take from each exchange.

    Returns:
        list[dict]: One entry per instrument with keys "instrument_token", "tradingsymbol", "exchange" and "identifier", where the identifier is the exchange and trading symbol joined by a colon as the quote endpoint expects.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the instrument tables cannot be read.
    """
    statement = sql_text(
        "SELECT instrument_token, tradingsymbol, exchange FROM ("
        "  SELECT instrument_token, tradingsymbol, exchange,"
        "         row_number() OVER ("
        "             PARTITION BY exchange"
        "             ORDER BY CASE WHEN instrument_type = 'FUT' THEN 0 WHEN instrument_type = 'EQ' THEN 1 ELSE 2 END,"
        "                      expiry NULLS FIRST, tradingsymbol"
        "         ) AS rank"
        "  FROM instruments.zerodha"
        "  WHERE download_date = (SELECT max(download_date) FROM instruments.zerodha)"
        "    AND (expiry IS NULL OR expiry = '' OR expiry::date > CURRENT_DATE)"
        ") ranked WHERE rank <= :per_exchange ORDER BY exchange, tradingsymbol"
    )
    with engine.connect() as connection:
        rows = connection.execute(statement, {"per_exchange": per_exchange}).all()

    instruments = []
    for instrument_token, tradingsymbol, exchange in rows:
        instruments.append({
            "instrument_token": int(instrument_token),
            "tradingsymbol": tradingsymbol,
            "exchange": exchange,
            "identifier": f"{exchange}:{tradingsymbol}",
        })
    return instruments


def capture_ticks(instrument_tokens, seconds):
    """
    Open one websocket connection, collect whatever it sends, and decode it.

    Zerodha sends a snapshot of every subscribed instrument immediately after a subscription is accepted, so this returns useful data even when the market is closed, which is what makes this check runnable outside trading hours.

    Args:
        instrument_tokens (list[int]): The instrument tokens to subscribe to in full mode.
        seconds (float): How long to stay connected before closing.

    Returns:
        tuple: An (api_key, access_token, ticks_by_token) triple, where ticks_by_token maps instrument token to the most recently decoded tick for it.

    Raises:
        stream.zerodha.credentials.ZerodhaCredentialsError: If there is no usable API key or access token.
        stream.zerodha.connection.ZerodhaConnectionError: If the connection could not be established.
    """
    frames = []

    async def capture():
        """
        Hold one connection open for the requested time and let the callback collect frames.

        Returns:
            tuple: An (api_key, access_token) pair, returned so the caller can reuse the same credentials for the REST comparison.
        """
        api_key, access_token = websocket_credentials()
        connection = ZerodhaConnection(
            api_key=api_key,
            access_token=access_token,
            instrument_tokens=instrument_tokens,
            on_frame=lambda arrival, frame: frames.append((arrival, frame)),
            mode="full",
            maximum_reconnect_attempts=0,
        )
        stop_event = asyncio.Event()
        task = asyncio.create_task(connection.run(stop_event))
        await asyncio.sleep(seconds)
        stop_event.set()
        try:
            await asyncio.wait_for(task, timeout=10)
        except asyncio.TimeoutError:
            task.cancel()
        return (api_key, access_token)

    api_key, access_token = asyncio.run(capture())

    ticks_by_token = {}
    for arrival, frame in frames:
        if len(frame) < 2:
            continue
        for tick in decode_frame(frame, datetime.fromtimestamp(arrival / 1e9)):
            ticks_by_token[tick["instrument_token"]] = tick
    return (api_key, access_token, ticks_by_token)


def fetch_quotes(api_key, access_token, identifiers):
    """
    Ask Zerodha's REST quote endpoint what it thinks these instruments are worth.

    Args:
        api_key (str): The Zerodha Kite Connect API key.
        access_token (str): An access token issued today.
        identifiers (list[str]): Exchange and trading symbol pairs, such as "NSE:RELIANCE".

    Returns:
        dict: The endpoint's data block, keyed by identifier. Instruments it declines to price are simply absent.

    Raises:
        requests.HTTPError: If the endpoint returned an error status.
    """
    response = requests.get(
        QUOTE_ENDPOINT,
        params={"i": identifiers},
        headers={
            "X-Kite-Version": "3",
            "Authorization": f"token {api_key}:{access_token}",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("data", {})


def compare_tick_to_quote(tick, quote):
    """
    Compare one decoded tick against Zerodha's own quote for the same instrument.

    Prices are divided by the tick's own divisor before comparing, which is what makes this a real test of the divisor rather than only of the field offsets. Quantities, volume and open interest are compared as they are, since no divisor applies to them.

    Args:
        tick (dict): A decoded tick from stream.zerodha.packets.
        quote (dict): One instrument's entry from the quote endpoint's data block.

    Returns:
        tuple: A (compared_count, disagreements) pair, where disagreements is a list of readable strings describing each value that did not match.
    """
    divisor = tick["price_divisor"]
    compared = 0
    disagreements = []

    values = [
        ("last_price", tick.get("last_price"), quote.get("last_price"), True),
        ("open", tick.get("open_price"), quote.get("ohlc", {}).get("open"), True),
        ("high", tick.get("high_price"), quote.get("ohlc", {}).get("high"), True),
        ("low", tick.get("low_price"), quote.get("ohlc", {}).get("low"), True),
        ("close", tick.get("close_price"), quote.get("ohlc", {}).get("close"), True),
        ("volume", tick.get("volume_traded"), quote.get("volume"), False),
        ("open_interest", tick.get("open_interest"), quote.get("oi"), False),
        ("total_buy_quantity", tick.get("total_buy_quantity"), quote.get("buy_quantity"), False),
        ("total_sell_quantity", tick.get("total_sell_quantity"), quote.get("sell_quantity"), False),
    ]
    for name, ours, theirs, scaled in values:
        if ours is None or theirs is None:
            continue
        compared = compared + 1
        ours_value = ours / divisor if scaled else ours
        if abs(float(ours_value) - float(theirs)) >= VERIFICATION_TOLERANCE:
            disagreements.append(f"{name}: ours {ours_value} theirs {theirs}")

    depth = quote.get("depth") or {}
    sides = [
        ("buy", tick.get("bid_prices"), tick.get("bid_quantities")),
        ("sell", tick.get("ask_prices"), tick.get("ask_quantities")),
    ]
    for side_name, prices, quantities in sides:
        entries = depth.get(side_name) or []
        if not prices:
            continue
        for level, entry in enumerate(entries):
            if level >= len(prices):
                break
            compared = compared + 2
            our_price = prices[level] / divisor
            if abs(our_price - float(entry["price"])) >= VERIFICATION_TOLERANCE:
                disagreements.append(f"depth {side_name} level {level + 1} price: ours {our_price} theirs {entry['price']}")
            if quantities[level] != entry["quantity"]:
                disagreements.append(f"depth {side_name} level {level + 1} quantity: ours {quantities[level]} theirs {entry['quantity']}")

    return (compared, disagreements)


def run_against_rest(per_exchange, seconds):
    """
    Check decoded websocket ticks against Zerodha's own REST quotes for the same instruments.

    This is the check the synthetic ones cannot replace. Those prove the parser agrees with this file's own idea of the format, since every byte they read was written here; this one uses the broker as the oracle, so it catches a field that both the parser and the synthetic checks are wrong about in the same direction.

    Args:
        per_exchange (int): How many instruments to take from each exchange.
        seconds (float): How long to hold the websocket connection open.

    Returns:
        int: The number of instruments that disagreed with the quote endpoint.

    Raises:
        stream.zerodha.credentials.ZerodhaCredentialsError: If there is no usable API key or access token.
        requests.HTTPError: If the quote endpoint returned an error status.
    """
    engine = create_engine(postgres_configuration["connection_string"])
    instruments = select_verification_instruments(engine, per_exchange)
    tokens = [instrument["instrument_token"] for instrument in instruments]
    print(f"Checking {len(tokens)} instruments across {len({i['exchange'] for i in instruments})} exchanges against Zerodha's quote endpoint.")
    print()

    api_key, access_token, ticks_by_token = capture_ticks(tokens, seconds)
    quotes = fetch_quotes(api_key, access_token, [instrument["identifier"] for instrument in instruments])

    total_compared = 0
    disagreeing_instruments = 0
    unquotable = 0
    undelivered = 0

    for instrument in instruments:
        tick = ticks_by_token.get(instrument["instrument_token"])
        quote = quotes.get(instrument["identifier"])
        if tick is None:
            undelivered = undelivered + 1
            continue
        if quote is None:
            unquotable = unquotable + 1
            continue

        compared, disagreements = compare_tick_to_quote(tick, quote)
        total_compared = total_compared + compared
        if disagreements:
            disagreeing_instruments = disagreeing_instruments + 1
            print(f"  MISMATCH  {instrument['identifier']} (segment {tick['exchange_segment']}, divisor {tick['price_divisor']})")
            for disagreement in disagreements:
                print(f"        {disagreement}")
        else:
            print(f"  ok        {instrument['identifier']:32s} segment {tick['exchange_segment']:>2d} divisor {tick['price_divisor']:>10,d} {compared:>3d} values")

    print()
    print(f"{total_compared} values compared, {disagreeing_instruments} instruments disagreed.")
    if undelivered:
        print(f"{undelivered} instruments were not delivered by the websocket.")
    if unquotable:
        print(f"{unquotable} instruments the quote endpoint would not price, so they could not be compared.")
    return disagreeing_instruments


def main():
    """
    Parse the command line and run the requested checks.

    Returns:
        None.

    Raises:
        SystemExit: Always, with status 1 when any check failed and 0 otherwise.
    """
    parser = argparse.ArgumentParser(description="Check that Zerodha binary frames are decoded correctly.")
    parser.add_argument("--synthetic", action="store_true", help="Run the byte-level checks, which need no network.")
    parser.add_argument("--against-rest", action="store_true", help="Compare decoded websocket ticks against Zerodha's own REST quotes.")
    parser.add_argument("--per-exchange", type=int, default=3, help="How many instruments to take from each exchange for --against-rest.")
    parser.add_argument("--seconds", type=float, default=12.0, help="How long to hold the websocket open for --against-rest.")
    arguments = parser.parse_args()

    if not arguments.synthetic and not arguments.against_rest:
        parser.error("nothing to do: pass --synthetic, --against-rest, or both")

    failures = 0
    if arguments.synthetic:
        failures = failures + run_synthetic()
    if arguments.against_rest:
        if arguments.synthetic:
            print()
        failures = failures + run_against_rest(arguments.per_exchange, arguments.seconds)

    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
