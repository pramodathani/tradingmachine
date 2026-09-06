"""
Checks that Flattrade's JSON frames are being decoded correctly.

The synthetic checks in this module build messages field by field from known values and assert that every field comes back exactly, which needs no network and no market hours. They exist because a JSON parser fails differently from a binary one: every field is named, so there are no offsets to get wrong, but a wrong wire key reads as absent, a wrong precision silently rescales every price, and a merge that replaces instead of updating quietly drops every field an incremental message did not repeat.

Each check targets a specific way this decoder could be wrong rather than simply exercising the happy path. The wire string check pins the literal message types and field names, because the builders and the decoder share one module's constants and would otherwise agree with themselves about a renamed key, and the depth check pins that the five arrays stay five long and keep their zeros, because trimming empty levels would be an easy and wrong convenience.

Run with: python3 -m stream.flattrade.verify_stream --synthetic

The --against-rest mode is the oracle check: it captures live websocket ticks for a spread of instruments, asks Flattrade's own REST quote endpoint what the same instruments are worth, and compares every value the two share. It also measures the implied price scale exchange by exchange, because the wire's `pp` price precision is read off the messages themselves and this is what settles whether the decoder read it right.

Run with: python3 -m stream.flattrade.verify_stream --against-rest --per-exchange 3 --seconds 12
"""

import argparse
import asyncio
import json
import statistics
import time
from datetime import datetime

import orjson
import requests
from sqlalchemy import create_engine, text as sql_text

from stream.flattrade import connection, packets
from stream.flattrade.connection import FlattradeConnection
from stream.flattrade.credentials import websocket_credentials
from stream.flattrade.packets import (
    ASK_ORDER_KEYS,
    ASK_PRICE_KEYS,
    ASK_QUANTITY_KEYS,
    BID_ORDER_KEYS,
    BID_PRICE_KEYS,
    BID_QUANTITY_KEYS,
    MESSAGE_TYPE_AUTHENTICATION_ACK,
    MESSAGE_TYPE_DEPTH_ACK,
    MESSAGE_TYPE_DEPTH_UPDATE,
    MESSAGE_TYPE_HEARTBEAT,
    MESSAGE_TYPE_HEARTBEAT_ACK,
    MESSAGE_TYPE_KEY,
    MESSAGE_TYPE_ORDER_UPDATE,
    MESSAGE_TYPE_POSITION_UPDATE,
    MESSAGE_TYPE_TOUCHLINE_ACK,
    MESSAGE_TYPE_TOUCHLINE_UPDATE,
    MESSAGE_TYPE_UNSUBSCRIBE_DEPTH_ACK,
    MESSAGE_TYPE_UNSUBSCRIBE_TOUCHLINE_ACK,
    TickAssembler,
    decode_frame,
    frame_packet_count,
)
from utilities.configuration import postgres_configuration

ARRIVAL_TIME = datetime(2026, 9, 6, 10, 30, 0)

QUOTE_ENDPOINT = "https://piconnect.flattrade.in/PiConnectAPI/GetQuotes"
QUOTE_REQUEST_PAUSE_SECONDS = 1.0
VERIFICATION_TOLERANCE = 0.011

EXCHANGE = "NSE"
TOKEN = "22"
INDEX_EXCHANGE = "NSE"
INDEX_TOKEN = "26000"


def build_message(message_type_value, values):
    """
    Build one websocket frame out of a message type and wire fields.

    Args:
        message_type_value (str): The message type to put in the `t` field.
        values (dict): The wire fields the message carries, keyed by their wire names.

    Returns:
        bytes: The frame, one JSON object encoded as UTF-8 text, which is how the live feed sends it.
    """
    message = {MESSAGE_TYPE_KEY: message_type_value}
    message.update(values)
    return orjson.dumps(message)


def build_touchline_ack_message(exchange, token, values, price_precision=None):
    """
    Build a touchline acknowledgement frame, the full snapshot one scrip gets on subscribe.

    Args:
        exchange (str): The exchange code, for example "NSE".
        token (str): The scrip token as the wire spells it.
        values (dict): Wire fields keyed by their wire names, covering the snapshot's prices and quantities.
        price_precision (int | None): The price precision to put in `pp`, or None to leave it out.

    Returns:
        bytes: The frame.
    """
    values = dict(values)
    values["e"] = exchange
    values["tk"] = token
    if price_precision is not None:
        values["pp"] = price_precision
    return build_message(MESSAGE_TYPE_TOUCHLINE_ACK, values)


def build_touchline_update_message(exchange, token, values):
    """
    Build a touchline update frame, which carries only the fields that changed.

    Args:
        exchange (str): The exchange code, for example "NSE".
        token (str): The scrip token as the wire spells it.
        values (dict): Wire fields keyed by their wire names.

    Returns:
        bytes: The frame.
    """
    values = dict(values)
    values["e"] = exchange
    values["tk"] = token
    return build_message(MESSAGE_TYPE_TOUCHLINE_UPDATE, values)


def build_depth_ack_message(exchange, token, values, price_precision=None):
    """
    Build a depth acknowledgement frame, the five level snapshot one scrip gets on subscribe.

    Args:
        exchange (str): The exchange code, for example "NSE".
        token (str): The scrip token as the wire spells it.
        values (dict): Wire fields keyed by their wire names, including the `bq1` through `so5` depth keys.
        price_precision (int | None): The price precision to put in `pp`, or None to leave it out.

    Returns:
        bytes: The frame.
    """
    values = dict(values)
    values["e"] = exchange
    values["tk"] = token
    if price_precision is not None:
        values["pp"] = price_precision
    return build_message(MESSAGE_TYPE_DEPTH_ACK, values)


def build_depth_update_message(exchange, token, values):
    """
    Build a depth update frame, which carries only the fields that changed.

    Args:
        exchange (str): The exchange code, for example "NSE".
        token (str): The scrip token as the wire spells it.
        values (dict): Wire fields keyed by their wire names.

    Returns:
        bytes: The frame.
    """
    values = dict(values)
    values["e"] = exchange
    values["tk"] = token
    return build_message(MESSAGE_TYPE_DEPTH_UPDATE, values)


def build_heartbeat_ack_message(timestamp_seconds):
    """
    Build a heartbeat acknowledgement frame.

    Args:
        timestamp_seconds (int): The seconds the wire puts in its `hk` field.

    Returns:
        bytes: The frame.
    """
    return build_message(MESSAGE_TYPE_HEARTBEAT_ACK, {"hk": timestamp_seconds})


def build_authentication_not_ok_message():
    """
    Build a connect acknowledgement frame that refuses authentication.

    Returns:
        bytes: The frame.
    """
    return build_message(MESSAGE_TYPE_AUTHENTICATION_ACK, {"uid": "FT0000", "s": "Not_Ok"})


def build_order_update_message():
    """
    Build an order update frame, which a market data connection can still receive.

    Returns:
        bytes: The frame.
    """
    return build_message(MESSAGE_TYPE_ORDER_UPDATE, {"actid": "FT0000", "status": "Complete"})


def build_position_update_message():
    """
    Build a position update frame, which a market data connection can still receive.

    Returns:
        bytes: The frame.
    """
    return build_message(MESSAGE_TYPE_POSITION_UPDATE, {"uid": "FT0000", "netqty": "0"})


def check_short_frames_decode_to_nothing():
    """
    Empty frames, non-JSON frames and JSON that is not an object must all decode to nothing.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    passed = (
        decode_frame(b"", ARRIVAL_TIME) == []
        and decode_frame(b"not json at all", ARRIVAL_TIME) == []
        and decode_frame(b"[1, 2, 3]", ARRIVAL_TIME) == []
        and decode_frame(b"{}", ARRIVAL_TIME) == []
    )
    return ("short and garbage frames decode to nothing", passed, "empty, non-JSON, non-object and empty-object frames all yield no tick")


def check_touchline_ack_fields():
    """
    Every field of a full touchline snapshot must land on the contract key it belongs to.

    The prices are all different on purpose, so reading one wire key as another cannot pass.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    frame = build_touchline_ack_message(EXCHANGE, TOKEN, {
        "lp": "2418.55",
        "v": "123456",
        "ap": "2410.05",
        "o": "2390.10",
        "h": "2430.80",
        "l": "2385.00",
        "c": "2399.45",
        "oi": "15000",
        "ft": "1788609598",
    }, price_precision=2)
    ticks = decode_frame(frame, ARRIVAL_TIME)
    if len(ticks) != 1:
        return ("touchline snapshot fields", False, f"decoded {len(ticks)} ticks, expected exactly one")
    tick = ticks[0]
    problems = []
    if tick["exchange"] != EXCHANGE:
        problems.append(f"exchange {tick['exchange']}")
    if tick["token"] != TOKEN:
        problems.append(f"token {tick['token']}")
    if tick["tick_mode"] != "quote":
        problems.append(f"tick_mode {tick['tick_mode']}")
    if tick["tradable"] is not True:
        problems.append(f"tradable {tick['tradable']}")
    if tick["price_divisor"] != 100:
        problems.append(f"price_divisor {tick['price_divisor']}")
    if tick["last_price"] != 241855:
        problems.append(f"last_price {tick['last_price']}")
    if tick["volume_traded"] != 123456:
        problems.append(f"volume_traded {tick['volume_traded']}")
    if tick["average_traded_price"] != 241005:
        problems.append(f"average_traded_price {tick['average_traded_price']}")
    if tick["open_price"] != 239010:
        problems.append(f"open_price {tick['open_price']}")
    if tick["high_price"] != 243080:
        problems.append(f"high_price {tick['high_price']}")
    if tick["low_price"] != 238500:
        problems.append(f"low_price {tick['low_price']}")
    if tick["close_price"] != 239945:
        problems.append(f"close_price {tick['close_price']}")
    if tick["open_interest"] != 15000:
        problems.append(f"open_interest {tick['open_interest']}")
    if tick["exchange_timestamp"] != datetime.fromtimestamp(1788609598):
        problems.append(f"exchange_timestamp {tick['exchange_timestamp']}")
    if tick.get("last_traded_quantity") is not None or tick.get("bid_quantities") is not None:
        problems.append("fields the touchline does not carry were invented")

    passed = not problems
    return ("touchline snapshot fields", passed, "; ".join(problems) or "every snapshot field landed on its contract key")


def check_partial_update_merges_only_changed_fields():
    """
    A partial update must change only the fields it carried, and invent no zeros.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    assembler = packets.TickAssembler()
    snapshot_frame = build_touchline_ack_message(EXCHANGE, TOKEN, {
        "lp": "2418.55",
        "v": "123456",
        "ap": "2410.05",
        "o": "2390.10",
        "h": "2430.80",
        "l": "2385.00",
        "c": "2399.45",
        "ft": "1788609598",
    }, price_precision=2)
    update_frame = build_touchline_update_message(EXCHANGE, TOKEN, {"lp": "2419.00"})

    assembler.merge(decode_frame(snapshot_frame, ARRIVAL_TIME)[0])
    merged = assembler.merge(decode_frame(update_frame, ARRIVAL_TIME)[0])

    problems = []
    if merged["last_price"] != 241900:
        problems.append(f"last_price {merged['last_price']}")
    if merged["volume_traded"] != 123456:
        problems.append(f"volume_traded drifted to {merged['volume_traded']}")
    if merged["open_price"] != 239010:
        problems.append(f"open_price drifted to {merged['open_price']}")
    if merged["high_price"] != 243080:
        problems.append(f"high_price drifted to {merged['high_price']}")
    if merged["low_price"] != 238500:
        problems.append(f"low_price drifted to {merged['low_price']}")
    if merged["close_price"] != 239945:
        problems.append(f"close_price drifted to {merged['close_price']}")
    if merged["average_traded_price"] != 241005:
        problems.append(f"average_traded_price drifted to {merged['average_traded_price']}")
    if merged["price_divisor"] != 100:
        problems.append(f"price_divisor {merged['price_divisor']}")

    blank_assembler = packets.TickAssembler()
    blank_update_frame = build_touchline_update_message(EXCHANGE, TOKEN, {"lp": "2419.00"})
    blank_merged = blank_assembler.merge(decode_frame(blank_update_frame, ARRIVAL_TIME)[0])
    if blank_merged["open_price"] is not None:
        problems.append(f"a never seen open_price came back as {blank_merged['open_price']} instead of None")

    empty_timestamp_assembler = packets.TickAssembler()
    empty_timestamp_assembler.merge(decode_frame(snapshot_frame, ARRIVAL_TIME)[0])
    empty_timestamp_frame = build_touchline_update_message(EXCHANGE, TOKEN, {"ft": "0"})
    empty_timestamp_merged = empty_timestamp_assembler.merge(decode_frame(empty_timestamp_frame, ARRIVAL_TIME)[0])
    if empty_timestamp_merged["exchange_timestamp"] != datetime.fromtimestamp(1788609598):
        problems.append(f"an absent exchange timestamp erased the snapshot's one, leaving {empty_timestamp_merged['exchange_timestamp']}")

    passed = not problems
    return ("partial update merges only changed fields", passed, "; ".join(problems) or "an lp-only update left every other field at its snapshot value, never seen fields stayed None, and an empty timestamp did not erase the snapshot's one")


def check_price_precision_scales_the_integer():
    """
    Prices must be scaled by the precision the wire declares, not a fixed hundred.

    A two precision equity price, a four precision currency price and a message with no `pp` at all are all exercised, because the default is a choice this check pins.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    equity_frame = build_touchline_ack_message(EXCHANGE, TOKEN, {"lp": "2418.55"}, price_precision=2)
    currency_frame = build_touchline_ack_message("CDS", "13", {"lp": "0.0025"}, price_precision=4)
    missing_precision_frame = build_touchline_ack_message(EXCHANGE, TOKEN, {"lp": "2418.55"})

    equity_tick = decode_frame(equity_frame, ARRIVAL_TIME)[0]
    currency_tick = decode_frame(currency_frame, ARRIVAL_TIME)[0]
    missing_tick = decode_frame(missing_precision_frame, ARRIVAL_TIME)[0]

    problems = []
    if equity_tick["last_price"] != 241855 or equity_tick["price_divisor"] != 100:
        problems.append(f"two precision equity {equity_tick['last_price']} / {equity_tick['price_divisor']}")
    if currency_tick["last_price"] != 25 or currency_tick["price_divisor"] != 10000:
        problems.append(f"four precision currency {currency_tick['last_price']} / {currency_tick['price_divisor']}")
    if missing_tick["last_price"] != 241855 or missing_tick["price_divisor"] != 100:
        problems.append(f"missing precision defaulted to {missing_tick['last_price']} / {missing_tick['price_divisor']}")

    passed = not problems
    return ("price precision scales the integer", passed, "; ".join(problems) or "pp 2, pp 4 and the default of 2 all scale correctly")


def check_depth_arrays_are_five():
    """
    The depth arrays must be five long, in the wire's level order, with zeros kept.

    Level five is deliberately zero, so trimming empty levels or reading only four would be caught.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    values = {
        "lp": "2418.55",
        "ltt": "10:29:58",
        "ltq": "25",
        "tbq": "90000",
        "tsq": "75000",
    }
    for level in range(5):
        values[BID_QUANTITY_KEYS[level]] = str(100 + level)
        values[BID_PRICE_KEYS[level]] = str(2418.55 - level)
        values[BID_ORDER_KEYS[level]] = str(10 + level)
        values[ASK_QUANTITY_KEYS[level]] = str(0 if level == 4 else 200 + level)
        values[ASK_PRICE_KEYS[level]] = str(2419.00 + level)
        values[ASK_ORDER_KEYS[level]] = str(20 + level)
    frame = build_depth_ack_message(EXCHANGE, TOKEN, values, price_precision=2)

    tick = decode_frame(frame, ARRIVAL_TIME)[0]

    problems = []
    if tick["bid_quantities"] != [100, 101, 102, 103, 104]:
        problems.append(f"bid_quantities {tick['bid_quantities']}")
    if tick["bid_prices"] != [241855, 241755, 241655, 241555, 241455]:
        problems.append(f"bid_prices {tick['bid_prices']}")
    if tick["bid_orders"] != [10, 11, 12, 13, 14]:
        problems.append(f"bid_orders {tick['bid_orders']}")
    if tick["ask_quantities"] != [200, 201, 202, 203, 0]:
        problems.append(f"ask_quantities {tick['ask_quantities']}")
    if tick["ask_prices"] != [241900, 242000, 242100, 242200, 242300]:
        problems.append(f"ask_prices {tick['ask_prices']}")
    if tick["ask_orders"] != [20, 21, 22, 23, 24]:
        problems.append(f"ask_orders {tick['ask_orders']}")
    if tick["last_trade_time"] is None or tick["last_trade_time"].strftime("%H:%M:%S") != "10:29:58":
        problems.append(f"last_trade_time {tick['last_trade_time']}")
    if tick["total_buy_quantity"] != 90000 or tick["total_sell_quantity"] != 75000:
        problems.append(f"totals {tick['total_buy_quantity']}/{tick['total_sell_quantity']}")

    passed = not problems
    return ("depth arrays are five levels", passed, "; ".join(problems) or "five levels a side, in wire order, zeros kept")


def check_acks_and_control_messages_decode_to_nothing():
    """
    Acknowledgements, heartbeats and order and position updates must produce no tick.

    These messages share the socket with market data, and decoding any of them as a tick would put phantom rows in the stream.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    frames = [
        build_message(MESSAGE_TYPE_AUTHENTICATION_ACK, {"uid": "FT0000", "s": "OK"}),
        build_authentication_not_ok_message(),
        build_heartbeat_ack_message(1788609598),
        build_message(MESSAGE_TYPE_UNSUBSCRIBE_TOUCHLINE_ACK, {"k": "NSE|22"}),
        build_message(MESSAGE_TYPE_UNSUBSCRIBE_DEPTH_ACK, {"k": "NSE|22"}),
        build_message(MESSAGE_TYPE_HEARTBEAT, {}),
        build_order_update_message(),
        build_position_update_message(),
    ]
    decoded_ticks = [decode_frame(frame, ARRIVAL_TIME) for frame in frames]
    passed = all(ticks == [] for ticks in decoded_ticks)
    return ("acks and control messages decode to nothing", passed, f"{len(frames)} control frames, {sum(len(ticks) for ticks in decoded_ticks)} ticks")


def check_frame_packet_count():
    """
    The archive's frame packet counter must count data messages and nothing else.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    passed = (
        frame_packet_count(build_touchline_ack_message(EXCHANGE, TOKEN, {"lp": "1"}, price_precision=2)) == 1
        and frame_packet_count(build_touchline_update_message(EXCHANGE, TOKEN, {"lp": "1"})) == 1
        and frame_packet_count(build_depth_ack_message(EXCHANGE, TOKEN, {"lp": "1"}, price_precision=2)) == 1
        and frame_packet_count(build_depth_update_message(EXCHANGE, TOKEN, {"lp": "1"})) == 1
        and frame_packet_count(build_heartbeat_ack_message(0)) == 0
        and frame_packet_count(build_order_update_message()) == 0
        and frame_packet_count(b"") == 0
        and frame_packet_count(b"not json") == 0
    )
    return ("frame packet counts", passed, "four data message types count one, acks and garbage count zero")


def check_wire_message_type_strings():
    """
    The decoder's message type and wire key constants must sit at the literal values the real feed uses.

    The builders and the decoder share this module's constants, so renaming a key would leave the checks self-consistent and silently agree with themselves. This check pins the constants to their documented literal strings, so the constants cannot drift from the wire without a live run noticing.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    problems = []
    if packets.MESSAGE_TYPE_KEY != "t":
        problems.append("message type key")
    if packets.MESSAGE_TYPE_TOUCHLINE_ACK != "tk":
        problems.append("touchline ack")
    if packets.MESSAGE_TYPE_TOUCHLINE_UPDATE != "tf":
        problems.append("touchline update")
    if packets.MESSAGE_TYPE_DEPTH_ACK != "dk":
        problems.append("depth ack")
    if packets.MESSAGE_TYPE_DEPTH_UPDATE != "df":
        problems.append("depth update")
    if packets.MESSAGE_TYPE_AUTHENTICATION_ACK != "ak":
        problems.append("authentication ack")
    if packets.MESSAGE_TYPE_HEARTBEAT != "h":
        problems.append("heartbeat")
    if packets.MESSAGE_TYPE_HEARTBEAT_ACK != "hk":
        problems.append("heartbeat ack")
    if packets.MESSAGE_TYPE_UNSUBSCRIBE_TOUCHLINE_ACK != "uk":
        problems.append("unsubscribe touchline ack")
    if packets.MESSAGE_TYPE_UNSUBSCRIBE_DEPTH_ACK != "udk":
        problems.append("unsubscribe depth ack")
    if packets.MESSAGE_TYPE_ORDER_UPDATE != "o":
        problems.append("order update")
    if packets.MESSAGE_TYPE_POSITION_UPDATE != "p":
        problems.append("position update")
    if packets.EXCHANGE_KEY != "e":
        problems.append("exchange key")
    if packets.TOKEN_KEY != "tk":
        problems.append("token key")
    if packets.PRICE_PRECISION_KEY != "pp":
        problems.append("price precision key")
    if packets.LAST_PRICE_KEY != "lp":
        problems.append("last price key")
    if packets.VOLUME_TRADED_KEY != "v":
        problems.append("volume key")
    if packets.AVERAGE_TRADED_PRICE_KEY != "ap":
        problems.append("average price key")
    if packets.OPEN_PRICE_KEY != "o":
        problems.append("open price key")
    if packets.HIGH_PRICE_KEY != "h":
        problems.append("high price key")
    if packets.LOW_PRICE_KEY != "l":
        problems.append("low price key")
    if packets.CLOSE_PRICE_KEY != "c":
        problems.append("close price key")
    if packets.DEPTH_CLOSE_PRICE_KEY != "cp":
        problems.append("depth close price key")
    if packets.OPEN_INTEREST_KEY != "oi":
        problems.append("open interest key")
    if packets.FEED_TIME_KEY != "ft":
        problems.append("feed time key")
    if packets.LAST_TRADE_TIME_KEY != "ltt":
        problems.append("last trade time key")
    if packets.LAST_TRADED_QUANTITY_KEY != "ltq":
        problems.append("last traded quantity key")
    if packets.TOTAL_BUY_QUANTITY_KEY != "tbq":
        problems.append("total buy quantity key")
    if packets.TOTAL_SELL_QUANTITY_KEY != "tsq":
        problems.append("total sell quantity key")
    if packets.BID_PRICE_KEYS != ["bp1", "bp2", "bp3", "bp4", "bp5"]:
        problems.append("bid price keys")
    if packets.BID_QUANTITY_KEYS != ["bq1", "bq2", "bq3", "bq4", "bq5"]:
        problems.append("bid quantity keys")
    if packets.BID_ORDER_KEYS != ["bo1", "bo2", "bo3", "bo4", "bo5"]:
        problems.append("bid order keys")
    if packets.ASK_PRICE_KEYS != ["sp1", "sp2", "sp3", "sp4", "sp5"]:
        problems.append("ask price keys")
    if packets.ASK_QUANTITY_KEYS != ["sq1", "sq2", "sq3", "sq4", "sq5"]:
        problems.append("ask quantity keys")
    if packets.ASK_ORDER_KEYS != ["so1", "so2", "so3", "so4", "so5"]:
        problems.append("ask order keys")
    if set(packets.MARKET_DATA_MESSAGE_TYPES) != {"tk", "tf", "dk", "df"}:
        problems.append(f"market data types {sorted(packets.MARKET_DATA_MESSAGE_TYPES)}")

    passed = not problems
    return ("wire message type and key strings pinned", passed, "; ".join(problems) or "every message type and wire key matches its documented literal")


def check_assembler_keys_do_not_cross():
    """
    Two scrips merged through one assembler must not share state.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    assembler = packets.TickAssembler()
    first_frame = build_touchline_ack_message(EXCHANGE, TOKEN, {"lp": "2418.55"}, price_precision=2)
    second_frame = build_touchline_ack_message(INDEX_EXCHANGE, INDEX_TOKEN, {"lp": "24570.10"}, price_precision=2)

    assembler.merge(decode_frame(first_frame, ARRIVAL_TIME)[0])
    second_tick = assembler.merge(decode_frame(second_frame, ARRIVAL_TIME)[0])

    passed = (
        second_tick["token"] == INDEX_TOKEN
        and second_tick["last_price"] == 2457010
        and len(assembler.known_instruments()) == 2
    )
    return ("assembler keys do not cross", passed, f"{len(assembler.known_instruments())} instruments held separately")


def check_connection_message_builders():
    """
    The connection's outgoing messages must be spelled exactly as the wire expects.

    The connection builds the messages the server reads, and the decoder reads the messages the server sends, so the two halves of the protocol never touch the same code path. This check pins the builders' JSON to their literal field names and values, so a renamed field cannot pass the decoder checks unnoticed.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    connect_message = orjson.loads(connection.connect_message("FT0000", "token123"))
    touchline_subscribe = orjson.loads(connection.subscribe_message("touchline", ["NSE|22", "BSE|508123"]))
    depth_subscribe = orjson.loads(connection.subscribe_message("depth", ["NSE|22"]))
    touchline_unsubscribe = orjson.loads(connection.unsubscribe_message("touchline", ["NSE|22"]))
    depth_unsubscribe = orjson.loads(connection.unsubscribe_message("depth", ["NSE|22"]))
    heartbeat = orjson.loads(connection.heartbeat_message())

    problems = []
    if connect_message != {"ta": "a", "uid": "FT0000", "actid": "FT0000", "source": "API", "accesstoken": "token123"}:
        problems.append(f"connect message {connect_message}")
    if touchline_subscribe != {"t": "t", "k": "NSE|22#BSE|508123"}:
        problems.append(f"touchline subscribe {touchline_subscribe}")
    if depth_subscribe != {"t": "d", "k": "NSE|22"}:
        problems.append(f"depth subscribe {depth_subscribe}")
    if touchline_unsubscribe != {"t": "u", "k": "NSE|22"}:
        problems.append(f"touchline unsubscribe {touchline_unsubscribe}")
    if depth_unsubscribe != {"t": "ud", "k": "NSE|22"}:
        problems.append(f"depth unsubscribe {depth_unsubscribe}")
    if heartbeat != {"t": "h"}:
        problems.append(f"heartbeat {heartbeat}")
    if connection.WEBSOCKET_ROOT != "wss://piconnect.flattrade.in/PiConnectWSAPI/":
        problems.append(f"websocket root {connection.WEBSOCKET_ROOT}")
    if connection.HEARTBEAT_INTERVAL_SECONDS != 30.0:
        problems.append(f"heartbeat interval {connection.HEARTBEAT_INTERVAL_SECONDS}")

    passed = not problems
    return ("connection message builders pinned", passed, "; ".join(problems) or "connect, subscribe, unsubscribe and heartbeat messages match their documented literals")


def check_exchange_code_translation():
    """
    The master segment to Flattrade exchange code translation must cover every tradable segment and skip the rest.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    problems = []
    expected = [
        ("nse", "nse_equities", "NSE"),
        ("nse", "nse_equity_indices", "NSE"),
        ("nse", "nse_equity_futures", "NFO"),
        ("nse", "nse_equity_options", "NFO"),
        ("nse", "nse_equity_index_futures", "NFO"),
        ("nse", "nse_equity_index_options", "NFO"),
        ("nse", "nse_currency_futures", "CDS"),
        ("nse", "nse_currency_options", "CDS"),
        ("bse", "bse_equities", "BSE"),
        ("bse", "bse_equity_indices", "BSE"),
        ("bse", "bse_equity_futures", "BFO"),
        ("bse", "bse_equity_options", "BFO"),
        ("bse", "bse_equity_index_futures", "BFO"),
        ("bse", "bse_equity_index_options", "BFO"),
        ("mcx", "mcx_commodity_futures", "MCX"),
        ("mcx", "mcx_commodity_options", "MCX"),
        ("mcx", "mcx_commodity_index_futures", "MCX"),
        ("mcx", "mcx_commodity_index_options", "MCX"),
    ]
    for master_exchange, master_segment, exchange_code in expected:
        actual = flattrade_exchange_code(master_exchange, master_segment)
        if actual != exchange_code:
            problems.append(f"{master_exchange}/{master_segment} translated to {actual}, expected {exchange_code}")
    for master_exchange, master_segment in [
        ("nse", "nse_exchange_traded_funds"),
        ("bse", "bse_investment_trusts"),
        ("bse", "bse_uncategorised"),
        ("unknown", "uncategorised"),
    ]:
        if flattrade_exchange_code(master_exchange, master_segment) is not None:
            problems.append(f"{master_exchange}/{master_segment} should have translated to None")

    passed = not problems
    return ("exchange code translation pinned", passed, "; ".join(problems) or "all tradable segments map to their six codes and the untradable ones to None")


def check_compare_tick_to_quote():
    """
    The REST comparison must divide by the tick's own divisor and compare both depth sides.

    The tick and the quote are built from the same underlying prices, so an undivided comparison, a swapped side or a dropped field each shows up either as a false mismatch or as a mismatch count that changed.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    values = {"lp": "2418.55", "h": "2430.80", "l": "2385.00", "v": "123456", "ltq": "25"}
    for level in range(5):
        values[BID_QUANTITY_KEYS[level]] = str(100 + level)
        values[BID_PRICE_KEYS[level]] = str(2418.55 - level)
        values[ASK_QUANTITY_KEYS[level]] = str(200 + level)
        values[ASK_PRICE_KEYS[level]] = str(2419.00 + level)
    tick = TickAssembler().merge(decode_frame(build_depth_ack_message(EXCHANGE, TOKEN, values, price_precision=2), ARRIVAL_TIME)[0])

    quote = {"stat": "Ok", "lp": 2418.55, "h": 2430.80, "l": 2385.00, "v": "123456", "ltq": "25"}
    for level in range(5):
        quote[BID_PRICE_KEYS[level]] = str(2418.55 - level)
        quote[BID_QUANTITY_KEYS[level]] = str(100 + level)
        quote[ASK_PRICE_KEYS[level]] = str(2419.00 + level)
        quote[ASK_QUANTITY_KEYS[level]] = str(200 + level)

    compared, disagreements = compare_tick_to_quote(tick, quote)
    wrong_price_quote = dict(quote)
    wrong_price_quote["lp"] = 2419.56
    wrong_price_compared, wrong_price_disagreements = compare_tick_to_quote(tick, wrong_price_quote)
    wrong_volume_quote = dict(quote)
    wrong_volume_quote["v"] = "123457"
    wrong_volume_compared, wrong_volume_disagreements = compare_tick_to_quote(tick, wrong_volume_quote)
    sparse_quote = {"stat": "Ok", "lp": 2418.55, "h": 2430.80, "l": 2385.00, "v": "123456", "ltq": "25"}
    sparse_compared, sparse_disagreements = compare_tick_to_quote(tick, sparse_quote)

    passed = (
        compared == 15
        and not disagreements
        and wrong_price_compared == 15
        and len(wrong_price_disagreements) == 1
        and wrong_price_disagreements[0].startswith("last_price:")
        and len(wrong_volume_disagreements) == 1
        and wrong_volume_disagreements[0].startswith("volume_traded:")
        and sparse_compared == 5
        and not sparse_disagreements
    )
    return (
        "REST comparison matches a consistent quote",
        passed,
        f"agreeing tick and quote compared {compared} values with no disagreements, a wrong last price and a wrong volume each produced exactly one, and a quote without depth compared only the {sparse_compared} touchline values",
    )


def check_implied_scale_ratio():
    """
    The implied scale of a correctly scaled tick against its REST quote must be exactly one.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    first_tick = TickAssembler().merge(decode_frame(build_touchline_ack_message(EXCHANGE, TOKEN, {"lp": "2418.55"}, price_precision=2), ARRIVAL_TIME)[0])
    second_tick = TickAssembler().merge(decode_frame(build_touchline_ack_message(EXCHANGE, "13", {"lp": "500.00"}, price_precision=2), ARRIVAL_TIME)[0])
    third_tick = TickAssembler().merge(decode_frame(build_touchline_ack_message(EXCHANGE, "14", {"lp": "100.00"}, price_precision=2), ARRIVAL_TIME)[0])
    instruments = [
        {"exchange": EXCHANGE, "token": TOKEN, "key": "NSE|22", "master_segment": "manual"},
        {"exchange": EXCHANGE, "token": "13", "key": "NSE|13", "master_segment": "manual"},
        {"exchange": EXCHANGE, "token": "14", "key": "NSE|14", "master_segment": "manual"},
    ]
    ticks_by_key = {
        (EXCHANGE, TOKEN): first_tick,
        (EXCHANGE, "13"): second_tick,
        (EXCHANGE, "14"): third_tick,
    }
    quotes = {
        (EXCHANGE, TOKEN): {"lp": 2418.55},
        (EXCHANGE, "13"): {"lp": 500.00},
        (EXCHANGE, "14"): {"lp": 83.333333},
    }

    medians = implied_scale_ratios(instruments, ticks_by_key, quotes)
    passed = medians.get(EXCHANGE) == 1.0
    return ("implied scale ratio is one", passed, f"median ratio {medians.get(EXCHANGE)} across three samples, two exact and one off by a fifth")


SYNTHETIC_CHECKS = [
    check_short_frames_decode_to_nothing,
    check_touchline_ack_fields,
    check_partial_update_merges_only_changed_fields,
    check_price_precision_scales_the_integer,
    check_depth_arrays_are_five,
    check_acks_and_control_messages_decode_to_nothing,
    check_frame_packet_count,
    check_wire_message_type_strings,
    check_assembler_keys_do_not_cross,
    check_connection_message_builders,
    check_exchange_code_translation,
    check_compare_tick_to_quote,
    check_implied_scale_ratio,
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


def flattrade_exchange_code(master_exchange, master_segment):
    """
    Translate an instruments.master exchange and segment into Flattrade's exchange code.

    Flattrade's scrip master carries six exchange codes, NSE, BSE, NFO, BFO, CDS and MCX, confirmed live against the instrument tables. Equity derivatives ride NFO for NSE and BFO for BSE, currency derivatives ride CDS for both exchanges, and indices subscribe on their cash exchange. The labelled-but-untradable segments, exchange traded funds, investment trusts and the uncategorised remainder, translate to None and the cross-check skips them.

    Args:
        master_exchange (str): The canonical lowercase exchange stored in instruments.master, for example "nse".
        master_segment (str): The exchange-prefixed segment stored in instruments.master, for example "nse_equities".

    Returns:
        str | None: Flattrade's exchange code, or None when the cross-check should not subscribe to this segment.
    """
    bare_segment = master_segment.partition("_")[2]
    if master_exchange == "nse":
        if bare_segment in ("equities", "equity_indices"):
            return "NSE"
        if bare_segment in ("equity_futures", "equity_options", "equity_index_futures", "equity_index_options"):
            return "NFO"
        if bare_segment in ("currency_futures", "currency_options"):
            return "CDS"
    if master_exchange == "bse":
        if bare_segment in ("equities", "equity_indices"):
            return "BSE"
        if bare_segment in ("equity_futures", "equity_options", "equity_index_futures", "equity_index_options"):
            return "BFO"
    if master_exchange == "mcx" and bare_segment in ("commodity_futures", "commodity_options", "commodity_index_futures", "commodity_index_options"):
        return "MCX"
    return None


def select_verification_instruments(engine, per_exchange):
    """
    Choose Flattrade instruments to check against Flattrade's own quote endpoint, spanning as many exchange codes as possible.

    Expired contracts are excluded because the quote endpoint will not price them and they would produce gaps rather than comparisons. Futures are preferred over options within a derivative segment, since they are more likely to have traded and therefore to carry a full set of values worth comparing.

    Args:
        engine: A SQLAlchemy engine for the black_box database.
        per_exchange (int): How many instruments to take from each Flattrade exchange code.

    Returns:
        list[dict]: One entry per instrument with keys "exchange", "token", "key" and "master_segment", where the key is the "EXCHANGE|TOKEN" string the websocket subscription and the quote endpoint both expect.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the instrument tables cannot be read.
    """
    statement = sql_text(
        "SELECT broker_token, exchange, segment, shape FROM ("
        "  SELECT b.broker_token AS broker_token, m.exchange AS exchange, m.segment AS segment, m.shape AS shape,"
        "         row_number() OVER ("
        "             PARTITION BY m.exchange, m.segment, m.shape"
        "             ORDER BY CASE WHEN m.shape = 'future' THEN 0 ELSE 1 END, m.symbol"
        "         ) AS rank"
        "  FROM instruments.broker_mappings b"
        "  JOIN instruments.master m ON m.instrument_id = b.instrument_id"
        "  WHERE b.broker = 'flattrade'"
        "    AND b.mapping_date = (SELECT max(mapping_date) FROM instruments.broker_mappings WHERE broker = 'flattrade')"
        "    AND (m.expiry_date IS NULL OR m.expiry_date > CURRENT_DATE)"
        ") ranked WHERE rank <= :per_exchange"
    )
    with engine.connect() as db_connection:
        rows = db_connection.execute(statement, {"per_exchange": per_exchange}).all()

    chosen = {}
    for broker_token, master_exchange, master_segment, master_shape in rows:
        exchange_code = flattrade_exchange_code(master_exchange, master_segment)
        if exchange_code is None:
            continue
        token = str(broker_token)
        if (exchange_code, token) in chosen:
            continue
        chosen[(exchange_code, token)] = {
            "exchange": exchange_code,
            "token": token,
            "key": f"{exchange_code}|{token}",
            "master_segment": f"{master_segment}/{master_shape}",
        }

    by_exchange = {}
    for entry in chosen.values():
        by_exchange.setdefault(entry["exchange"], []).append(entry)
    instruments = []
    for exchange_code in sorted(by_exchange):
        exchange_entries = by_exchange[exchange_code][:per_exchange]
        for entry in exchange_entries:
            instruments.append(entry)
    return instruments


def capture_ticks(instruments, seconds):
    """
    Open one live depth connection, collect whatever it sends, and merge it into complete ticks.

    The touchline and the depth feed differ only in the subscribe message and the extra fields the snapshot carries, so the depth feed is used here because it is the superset: it sends everything the touchline does plus the five levels a side the quote endpoint also reports. Outside market hours the capture can come back empty, and the caller must treat that as an inconclusive run rather than a passed one.

    Args:
        instruments (list[dict]): The instruments to subscribe to, as select_verification_instruments returns them.
        seconds (float): How long to stay connected before closing.

    Returns:
        tuple: A (uid, access_token, ticks_by_key) triple, where ticks_by_key maps each (exchange, token) pair to the most recently merged tick for it. The credentials are returned so the REST comparison can reuse the same login.

    Raises:
        stream.flattrade.credentials.FlattradeCredentialsError: If there is no usable user identifier or access token.
        stream.flattrade.connection.FlattradeConnectionError: If the connection could not be established.
    """
    frames = []

    async def capture():
        """
        Hold one connection open for the requested time and let the callback collect frames.

        Returns:
            tuple: A (uid, access_token) pair, returned so the caller can reuse the same credentials for the REST comparison.
        """
        uid, access_token = websocket_credentials()
        feed_connection = FlattradeConnection(
            uid=uid,
            access_token=access_token,
            instruments=[instrument["key"] for instrument in instruments],
            on_frame=lambda arrival, frame: frames.append((arrival, frame)),
            mode=connection.MODE_DEPTH,
            maximum_reconnect_attempts=0,
        )
        stop_event = asyncio.Event()
        run_task = asyncio.create_task(feed_connection.run(stop_event))
        await asyncio.sleep(seconds)
        stop_event.set()
        try:
            await asyncio.wait_for(run_task, timeout=10)
        except asyncio.TimeoutError:
            run_task.cancel()
        return (uid, access_token)

    uid, access_token = asyncio.run(capture())

    assembler = TickAssembler()
    ticks_by_key = {}
    for arrival, frame in frames:
        for tick in decode_frame(frame, datetime.fromtimestamp(arrival / 1e9)):
            ticks_by_key[(tick["exchange"], tick["token"])] = assembler.merge(tick)
    return (uid, access_token, ticks_by_key)


def fetch_quotes(uid, access_token, instruments):
    """
    Ask Flattrade's REST quote endpoint what it thinks these instruments are worth.

    The endpoint prices one instrument per request, with the query inside a jData form field and the session token beside it in jKey. A one second pause between requests keeps the run well inside what a read-only endpoint should be asked to serve.

    Args:
        uid (str): The Flattrade user identifier, sent inside jData.
        access_token (str): An access token issued today, sent as jKey.
        instruments (list[dict]): The instruments to price, as select_verification_instruments returns them.

    Returns:
        dict: The endpoint's response per instrument, keyed by (exchange, token). Instruments it declines to price are simply absent.

    Raises:
        requests.HTTPError: If the endpoint returned an error status.
    """
    quotes = {}
    for position, instrument in enumerate(instruments):
        if position > 0:
            time.sleep(QUOTE_REQUEST_PAUSE_SECONDS)
        query = {"uid": uid, "exch": instrument["exchange"], "token": instrument["token"]}
        response = requests.post(
            QUOTE_ENDPOINT,
            data={
                "jData": json.dumps(query),
                "jKey": access_token,
            },
            timeout=30,
        )
        response.raise_for_status()
        quote = response.json()
        if quote.get("stat") != "Ok":
            continue
        quotes[(instrument["exchange"], instrument["token"])] = quote
    return quotes


def compare_tick_to_quote(tick, quote):
    """
    Compare one decoded tick against Flattrade's own quote for the same instrument.

    Prices are divided by the tick's own divisor before comparing, which is what makes this a real test of the precision handling rather than only of the field names. Quantities and volume are compared as they are, since no divisor applies to them. The quote endpoint carries no open, close or open interest, so those contract fields simply go uncompared here.

    Args:
        tick (dict): A decoded, merged tick from stream.flattrade.packets.
        quote (dict): One instrument's response from the quote endpoint.

    Returns:
        tuple: A (compared_count, disagreements) pair, where disagreements is a list of readable strings describing each value that did not match.
    """
    divisor = tick["price_divisor"]
    compared = 0
    disagreements = []

    prices = [
        ("last_price", tick.get("last_price"), quote.get("lp")),
        ("high_price", tick.get("high_price"), quote.get("h")),
        ("low_price", tick.get("low_price"), quote.get("l")),
    ]
    for name, ours, theirs in prices:
        if ours is None or theirs is None:
            continue
        compared = compared + 1
        ours_value = ours / divisor
        if abs(float(ours_value) - float(theirs)) >= VERIFICATION_TOLERANCE:
            disagreements.append(f"{name}: ours {ours_value} theirs {theirs}")

    quantities = [
        ("volume_traded", tick.get("volume_traded"), quote.get("v")),
        ("last_traded_quantity", tick.get("last_traded_quantity"), quote.get("ltq")),
    ]
    for name, ours, theirs in quantities:
        if ours is None or theirs is None:
            continue
        compared = compared + 1
        if int(ours) != int(theirs):
            disagreements.append(f"{name}: ours {ours} theirs {theirs}")

    sides = [
        ("bid", tick.get("bid_prices"), tick.get("bid_quantities"), packets.BID_PRICE_KEYS, packets.BID_QUANTITY_KEYS),
        ("ask", tick.get("ask_prices"), tick.get("ask_quantities"), packets.ASK_PRICE_KEYS, packets.ASK_QUANTITY_KEYS),
    ]
    for side_name, our_prices, our_quantities, price_keys, quantity_keys in sides:
        if not our_prices:
            continue
        for level in range(5):
            their_price = quote.get(price_keys[level])
            their_quantity = quote.get(quantity_keys[level])
            if their_price is None and their_quantity is None:
                continue
            compared = compared + 1
            our_price = our_prices[level] / divisor
            if their_price is not None and abs(our_price - float(their_price)) >= VERIFICATION_TOLERANCE:
                disagreements.append(f"depth {side_name} level {level + 1} price: ours {our_price} theirs {their_price}")
            if their_quantity is not None and our_quantities[level] != int(their_quantity):
                disagreements.append(f"depth {side_name} level {level + 1} quantity: ours {our_quantities[level]} theirs {their_quantity}")

    return (compared, disagreements)


def implied_scale_ratios(instruments, ticks_by_key, quotes):
    """
    Measure what price scale the wire really carries, exchange code by exchange code.

    The decoder scales prices by the `pp` precision each message declares, and this is the check that settles whether it read that precision right. Each instrument's last price is turned back into rupees and divided by the REST quote's own last price. A median ratio of one means the precision handling is right; a median of ten or a tenth would mean the declared precision is not the one the prices are written in.

    Args:
        instruments (list[dict]): The instruments that were compared, as select_verification_instruments returns them.
        ticks_by_key (dict): Merged ticks keyed by (exchange, token), as capture_ticks returns them.
        quotes (dict): REST quotes keyed by (exchange, token), as fetch_quotes returns them.

    Returns:
        dict: One entry per exchange code with a nonzero ratio sample, mapping the code to the median ratio for it.
    """
    ratios_by_exchange = {}
    for instrument in instruments:
        key = (instrument["exchange"], instrument["token"])
        tick = ticks_by_key.get(key)
        quote = quotes.get(key)
        if tick is None or quote is None:
            continue
        our_price = tick.get("last_price")
        their_price = quote.get("lp")
        if not our_price or not their_price or float(their_price) == 0:
            continue
        ratio = (our_price / tick["price_divisor"]) / float(their_price)
        ratios_by_exchange.setdefault(instrument["exchange"], []).append(ratio)

    medians = {}
    for exchange_code, ratios in ratios_by_exchange.items():
        medians[exchange_code] = statistics.median(ratios)
    return medians


def run_against_rest(per_exchange, seconds, manual_instruments=None):
    """
    Check decoded websocket ticks against Flattrade's own REST quotes for the same instruments.

    This is the check the synthetic ones cannot replace. Those prove the parser agrees with this file's own idea of the format, since every byte they read was written here; this one uses the broker as the oracle, so it catches a field that both the parser and the synthetic checks are wrong about in the same direction.

    Args:
        per_exchange (int): How many instruments to take from each Flattrade exchange code.
        seconds (float): How long to hold the websocket connection open.
        manual_instruments (list[str] | None): Instrument keys of the form "EXCHANGE|TOKEN" to check instead of the automatic selection, or None to select from the instrument tables.

    Returns:
        int: The number of instruments that disagreed with the quote endpoint.

    Raises:
        stream.flattrade.credentials.FlattradeCredentialsError: If there is no usable user identifier or access token.
        requests.HTTPError: If the quote endpoint returned an error status.
    """
    if manual_instruments:
        instruments = []
        for key in manual_instruments:
            exchange, token = key.split("|", 1)
            instruments.append({
                "exchange": exchange,
                "token": token,
                "key": key,
                "master_segment": "manual",
            })
    else:
        engine = create_engine(postgres_configuration["connection_string"])
        instruments = select_verification_instruments(engine, per_exchange)
    print(f"Checking {len(instruments)} instruments across {len({i['exchange'] for i in instruments})} Flattrade exchange codes against Flattrade's quote endpoint.")
    print()

    uid, access_token, ticks_by_key = capture_ticks(instruments, seconds)
    if not ticks_by_key:
        print("  NOTE  the websocket delivered no ticks at all; outside market hours that is the expected answer, and during a session it would mean Flattrade sent no snapshot on subscribe")
        print("        run this again during market hours")
        return 0

    quotes = fetch_quotes(uid, access_token, instruments)

    total_compared = 0
    disagreeing_instruments = 0
    unquotable = 0
    undelivered = 0

    for instrument in instruments:
        key = (instrument["exchange"], instrument["token"])
        tick = ticks_by_key.get(key)
        quote = quotes.get(key)
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
            print(f"  MISMATCH  {instrument['key']} ({instrument['master_segment']}, divisor {tick['price_divisor']})")
            for disagreement in disagreements:
                print(f"        {disagreement}")
        else:
            print(f"  ok        {instrument['key']:20s} {instrument['master_segment']:42s} {compared:>3d} values")

    print()
    scale_medians = implied_scale_ratios(instruments, ticks_by_key, quotes)
    for exchange_code in sorted(scale_medians):
        median = scale_medians[exchange_code]
        marker = "ok " if abs(median - 1.0) < 0.1 else "BAD"
        print(f"  {marker} implied scale for {exchange_code}: median ratio {median:.4f}")
    if not scale_medians:
        print("  NOTE  no instruments had both a websocket price and a REST price, so the implied scale could not be measured")
    print()

    print(f"{total_compared} values compared, {disagreeing_instruments} instruments disagreed.")
    if undelivered:
        print(f"{undelivered} instruments were not delivered by the websocket.")
    if unquotable:
        print(f"{unquotable} instruments the quote endpoint would not price, so they could not be compared.")
    scale_problems = sum(1 for median in scale_medians.values() if abs(median - 1.0) >= 0.1)
    return disagreeing_instruments + scale_problems


def main():
    """
    Run the checks the command line asked for.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(description="Check that Flattrade's websocket frames are decoded correctly.")
    parser.add_argument("--synthetic", action="store_true", help="Run the synthetic decoding checks, which need no network.")
    parser.add_argument("--against-rest", action="store_true", help="Compare decoded websocket ticks against Flattrade's own REST quotes; needs market hours and credentials.")
    parser.add_argument("--per-exchange", type=int, default=3, help="How many instruments to take from each Flattrade exchange code for --against-rest.")
    parser.add_argument("--instrument", action="append", help="An instrument to check as EXCHANGE|TOKEN, for example NSE|22; repeat for more; replaces the automatic selection in --against-rest.")
    parser.add_argument("--seconds", type=float, default=12.0, help="How long to hold a live socket open.")
    arguments = parser.parse_args()

    if not arguments.synthetic and not arguments.against_rest:
        parser.error("nothing to do: pass --synthetic, --against-rest, or both")

    failures = 0
    if arguments.synthetic:
        failures = failures + run_synthetic()
    if arguments.against_rest:
        if arguments.synthetic:
            print()
        failures = failures + run_against_rest(arguments.per_exchange, arguments.seconds, arguments.instrument)

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()