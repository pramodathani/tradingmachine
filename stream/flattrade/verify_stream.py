"""
Checks that Flattrade's JSON frames are being decoded correctly.

The synthetic checks in this module build messages field by field from known values and assert that every field comes back exactly, which needs no network and no market hours. They exist because a JSON parser fails differently from a binary one: every field is named, so there are no offsets to get wrong, but a wrong wire key reads as absent, a wrong precision silently rescales every price, and a merge that replaces instead of updating quietly drops every field an incremental message did not repeat.

Each check targets a specific way this decoder could be wrong rather than simply exercising the happy path. The wire string check pins the literal message types and field names, because the builders and the decoder share one module's constants and would otherwise agree with themselves about a renamed key, and the depth check pins that the five arrays stay five long and keep their zeros, because trimming empty levels would be an easy and wrong convenience.

Run with: python3 -m stream.flattrade.verify_stream --synthetic
"""

import argparse
from datetime import datetime

import orjson

from stream.flattrade import packets
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
    decode_frame,
    frame_packet_count,
)

ARRIVAL_TIME = datetime(2026, 9, 6, 10, 30, 0)

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


def main():
    """
    Run the checks the command line asked for.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(description="Checks that Flattrade's websocket frames are being decoded correctly.")
    parser.add_argument("--synthetic", action="store_true", help="Run the synthetic decoding checks, which need no network.")
    arguments = parser.parse_args()
    if not arguments.synthetic:
        parser.print_help()
        return
    failures = run_synthetic()
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()