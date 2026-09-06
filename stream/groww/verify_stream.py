"""
Checks that Groww's messages are being decoded correctly.

The synthetic checks in this module build NATS message operations byte by byte from known values and assert that every field comes back exactly, which needs no network and no market hours. They exist because Groww's feed fails in ways that are silent, and each check targets one specific way this decoder could be wrong rather than exercising a happy path.

The risks are twofold. The protobuf payload is self-describing, so it cannot be misaligned, but a hand-written reader can disagree with the schema: a wrong field number produces a plausible number in the wrong place, and the index arm putting its value in the price arm's open field is exactly such a trap. The golden frames here were encoded by Groww's own generated `stocks_socket_response_pb2` module from the descriptor embedded in its SDK, and are stored as hex literals, so every run pins this project's reader against the official encoder without the SDK needing to be installed.

The framing layer has its own risks, because the websocket carries a NATS byte stream rather than self-contained frames. One websocket frame may hold half a message, several of them, or a tail plus a head, so the checks pin that the ProtocolReader reassembles the declared payload length and is not confused by control operations or by a payload containing the two bytes that end a control line.

Run with: python3 -m stream.groww.verify_stream --synthetic

The --against-rest mode is the oracle check: it captures live websocket ticks for a spread of instruments, asks Groww's own REST quote endpoint what the same instruments are worth, and compares every value the two share. It needs a login from today and market hours, because nothing trades otherwise.

Run with: python3 -m stream.groww.verify_stream --against-rest --per-exchange 3 --seconds 12
"""

import argparse
import asyncio
import json
import statistics
import struct
import time
from datetime import datetime

import requests
from sqlalchemy import create_engine, text as sql_text

from stream.groww import connection, packets
from stream.groww.connection import GrowwConnection, GrowwConnectionError, ProtocolReader
from stream.groww.credentials import stored_access_token, websocket_credentials
from utilities.configuration import postgres_configuration

ARRIVAL_TIME = datetime(2026, 9, 7, 10, 30, 0)

QUOTE_ENDPOINT = "https://api.groww.in/v1/live-data/quote"
QUOTE_REQUEST_PAUSE_SECONDS = 1.0
VERIFICATION_TOLERANCE = 0.011

EQUITY_SUBJECT = "/ld/eq/nse/price_detailed.2885"
BSE_EQUITY_SUBJECT = "/ld/eq/bse/price_detailed.11536"
DERIVATIVE_SUBJECT = "/ld/fo/nse/price_detailed.35001"
BSE_DERIVATIVE_SUBJECT = "/ld/fo/bse/price_detailed.35001"
INDEX_SUBJECT = "/ld/indices/nse/price.26000"
BSE_INDEX_SUBJECT = "/ld/indices/bse/price.26000"

EQUITY_PAYLOAD = bytes.fromhex(
    "0a0852454c49414e43451801228801090000403b8e917942116666666666e49540190000000000459640213333333333d09540299a99999999df954031000000c06bbe5f41390000002cd6e20542410000000000889340490000000000cea84051fe65f7e46111964059c3f5285c8f0f984061713d0ad7a3af93406900000000002b964079000000000050944081010000000000709740"
)
DERIVATIVE_PAYLOAD = bytes.fromhex(
    "0a114e49465459323653455032353030304345100118012224090080e93e8e9179423100000000389c3c416933333333338773407100000080df175041"
)
INDEX_PAYLOAD = bytes.fromhex(
    "0a054e494654591801321209000093428e917942116666666636d6d840"
)
CURRENCY_PAYLOAD = bytes.fromhex(
    "0a0e555344494e52323553455046555410021801221b0900803c468e91794229e17a14ae47195640698fc2f5285c1b5640"
)
CARRIAGE_RETURN_PAYLOAD = bytes.fromhex(
    "0a04410d0a422212090000e6498e917942690000000000002a40"
)
DEPTH_PAYLOAD = bytes.fromhex(
    "0a0852454c49414e434518012a210900808f4d8e91794212160800121209cdcccccccc2a9640110000000000407f40"
)

PRICE_PAYLOAD_VALUES = {
    1: 1757059200000.0,
    2: 1401.1,
    3: 1425.25,
    4: 1396.05,
    5: 1399.9,
    6: 8321455.0,
    7: 11750000000.0,
    8: 1250.0,
    9: 3175.0,
    10: 1412.3456,
    11: 1539.89,
    12: 1259.91,
    13: 1418.75,
    14: 4218750.0,
    15: 1300.0,
    16: 1500.0,
}


def encode_varint(value):
    """
    Encode one integer in protobuf varint form.

    Args:
        value (int): The integer to encode, zero or positive.

    Returns:
        bytes: The encoded integer, one byte per seven bits, most significant group first.
    """
    encoded = bytearray()
    while True:
        group = value & 0x7F
        value = value >> 7
        if value:
            encoded.append(group | 0x80)
        else:
            encoded.append(group)
            return bytes(encoded)


def encode_field_tag(field_number, wire_type):
    """
    Encode one field's tag.

    Args:
        field_number (int): The field's number in the schema.
        wire_type (int): The field's wire type.

    Returns:
        bytes: The tag varint.
    """
    return encode_varint((field_number << 3) | wire_type)


def encode_double_field(field_number, value):
    """
    Encode one fixed sixty four bit field carrying a double.

    Args:
        field_number (int): The field's number in the schema.
        value (float): The value to encode.

    Returns:
        bytes: The tag followed by eight little endian bytes.
    """
    return encode_field_tag(field_number, packets.WIRE_TYPE_SIXTY_FOUR_BIT) + struct.pack("<d", value)


def encode_length_field(field_number, payload):
    """
    Encode one length delimited field carrying a nested message or a string.

    Args:
        field_number (int): The field's number in the schema.
        payload (bytes): The bytes the field carries.

    Returns:
        bytes: The tag, the payload's length as a varint, and the payload.
    """
    return encode_field_tag(field_number, packets.WIRE_TYPE_LENGTH_DELIMITED) + encode_varint(len(payload)) + payload


def encode_live_price_payload(values_by_field):
    """
    Encode a StocksLivePriceProto from field numbers to doubles.

    Args:
        values_by_field (dict): One (field_number, value) entry per field to carry.

    Returns:
        bytes: The encoded message.
    """
    payload = b""
    for field_number in sorted(values_by_field):
        payload = payload + encode_double_field(field_number, values_by_field[field_number])
    return payload


def encode_live_indices_payload(timestamp_milliseconds, value):
    """
    Encode a StocksLiveIndicesProto, whose value sits in field 2.

    Args:
        timestamp_milliseconds (float): The timestamp in milliseconds.
        value (float): The index level.

    Returns:
        bytes: The encoded message.
    """
    return encode_double_field(1, timestamp_milliseconds) + encode_double_field(2, value)


def encode_response(symbol, segment, exchange, arm_field_number, arm_payload):
    """
    Encode a StocksSocketResponseProtoDto carrying one arm of the oneof.

    Args:
        symbol (str): The instrument's symbol as the payload reports it.
        segment (int): The segment enum value, or None to omit the field.
        exchange (int): The exchange enum value, or None to omit the field.
        arm_field_number (int): Which oneof arm carries the payload, 4 for price, 6 for indices.
        arm_payload (bytes): The encoded arm message.

    Returns:
        bytes: The encoded response message.
    """
    response = encode_length_field(packets.RESPONSE_SYMBOL_FIELD, symbol.encode("utf-8"))
    if segment is not None:
        response = response + encode_field_tag(packets.RESPONSE_SEGMENT_FIELD, packets.WIRE_TYPE_VARINT) + encode_varint(segment)
    if exchange is not None:
        response = response + encode_field_tag(packets.RESPONSE_EXCHANGE_FIELD, packets.WIRE_TYPE_VARINT) + encode_varint(exchange)
    return response + encode_length_field(arm_field_number, arm_payload)


def nats_message(subject, payload, subscription_identifier=1):
    """
    Wrap one protobuf payload in the NATS message operation the connection archives.

    Args:
        subject (str): The subject the message was published on.
        payload (bytes): The protobuf payload.
        subscription_identifier (int): The subscription identifier the header carries.

    Returns:
        bytes: The header line, the payload and the trailing terminator, as the server sends them.
    """
    header = f"MSG {subject} {subscription_identifier} {len(payload)}".encode("ascii") + packets.LINE_TERMINATOR
    return header + payload + packets.LINE_TERMINATOR


def check_field_tables_are_pinned_literally():
    """
    The field tables are exactly these names in exactly this order.

    Every other check reads the field tables out of the decoder and compares against them, so all of them move together if a table is reordered and none of them can notice. This check writes the expected tables out in full, so it is the only thing standing between a reordered table and a silent, plausible mislabelling of every field that moved.

    The names here were transcribed from the descriptor embedded in Groww's generated `stocks_socket_response_pb2` and must not be changed to match a modified decoder. If this check fails, the decoder is wrong until the wire is shown to have changed.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []

    expected_price_fields = [
        "timestamp_milliseconds",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume_traded",
        "traded_value",
        "total_buy_quantity",
        "total_sell_quantity",
        "average_traded_price",
        "high_price_range",
        "low_price_range",
        "last_price",
        "open_interest",
        "low_trade_range",
        "high_trade_range",
    ]
    if list(packets.LIVE_PRICE_FIELD_NAMES.values()) != expected_price_fields:
        failures.append(f"LIVE_PRICE_FIELD_NAMES is {list(packets.LIVE_PRICE_FIELD_NAMES.values())!r}")

    expected_index_fields = [
        "timestamp_milliseconds",
        "last_price",
    ]
    if list(packets.LIVE_INDICES_FIELD_NAMES.values()) != expected_index_fields:
        failures.append(f"LIVE_INDICES_FIELD_NAMES is {list(packets.LIVE_INDICES_FIELD_NAMES.values())!r}")

    if list(packets.PRICE_FIELDS) == expected_price_fields:
        failures.append("PRICE_FIELDS should not carry the timestamp, but does")

    if packets.EXCHANGE_NAMES != {
        0: "BSE",
        1: "NSE",
        2: "MCX",
        3: "MCXSX",
        4: "NCDEX",
        5: "GLOBAL",
        6: "US",
    }:
        failures.append(f"EXCHANGE_NAMES is {packets.EXCHANGE_NAMES!r}")

    if packets.SEGMENT_NAMES != {
        0: "CASH",
        1: "FNO",
        2: "CURRENCY",
        3: "COMMODITY",
    }:
        failures.append(f"SEGMENT_NAMES is {packets.SEGMENT_NAMES!r}")

    pinned_constants = [
        ("RESPONSE_SYMBOL_FIELD", packets.RESPONSE_SYMBOL_FIELD, 1),
        ("RESPONSE_SEGMENT_FIELD", packets.RESPONSE_SEGMENT_FIELD, 2),
        ("RESPONSE_EXCHANGE_FIELD", packets.RESPONSE_EXCHANGE_FIELD, 3),
        ("RESPONSE_LIVE_PRICE_FIELD", packets.RESPONSE_LIVE_PRICE_FIELD, 4),
        ("RESPONSE_MARKET_DEPTH_FIELD", packets.RESPONSE_MARKET_DEPTH_FIELD, 5),
        ("RESPONSE_LIVE_INDICES_FIELD", packets.RESPONSE_LIVE_INDICES_FIELD, 6),
        ("PRICE_DIVISOR", packets.PRICE_DIVISOR, 10000),
        ("MESSAGE_OPERATION", packets.MESSAGE_OPERATION, b"MSG"),
        ("LINE_TERMINATOR", packets.LINE_TERMINATOR, b"\r\n"),
        ("TICK_MODE_PRICE_DETAILED", packets.TICK_MODE_PRICE_DETAILED, "price_detailed"),
        ("TICK_MODE_INDEX_VALUE", packets.TICK_MODE_INDEX_VALUE, "index_value"),
    ]
    for constant_name, actual, expected in pinned_constants:
        if actual != expected:
            failures.append(f"{constant_name} is {actual!r}, expected {expected!r}")
    return failures


def check_every_price_field_round_trips():
    """
    Every one of the sixteen price fields comes back under the right name.

    This is the check that a shifted field table has to fail. The values are deliberately all different, so a swap of any two shows up rather than being masked by two fields that happen to be equal. Prices are compared after scaling, quantities after rounding, and the timestamp after conversion, because those are the transformations the tick carries.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    payload = encode_live_price_payload(PRICE_PAYLOAD_VALUES)
    frame = nats_message(EQUITY_SUBJECT, encode_response("RELIANCE", None, 1, packets.RESPONSE_LIVE_PRICE_FIELD, payload))
    decoded = packets.decode_frame(frame, ARRIVAL_TIME)
    if len(decoded) != 1:
        return [f"expected one tick, got {len(decoded)}"]

    tick = decoded[0]
    expected_prices = {
        "open_price": 14011000,
        "high_price": 14252500,
        "low_price": 13960500,
        "close_price": 13999000,
        "traded_value": 117500000000000,
        "average_traded_price": 14123456,
        "high_price_range": 15398900,
        "low_price_range": 12599100,
        "last_price": 14187500,
        "low_trade_range": 13000000,
        "high_trade_range": 15000000,
    }
    expected_quantities = {
        "volume_traded": 8321455,
        "total_buy_quantity": 1250,
        "total_sell_quantity": 3175,
        "open_interest": 4218750,
    }
    for field_name, expected in expected_prices.items():
        if tick.get(field_name) != expected:
            failures.append(f"{field_name} came back as {tick.get(field_name)!r}, expected {expected}")
    for field_name, expected in expected_quantities.items():
        if tick.get(field_name) != expected:
            failures.append(f"{field_name} came back as {tick.get(field_name)!r}, expected {expected}")

    if tick["exchange_timestamp"] != packets.epoch_milliseconds_to_datetime(PRICE_PAYLOAD_VALUES[1]):
        failures.append(f"exchange_timestamp came back as {tick['exchange_timestamp']!r}")
    if tick["symbol"] != "RELIANCE":
        failures.append(f"symbol came back as {tick['symbol']!r}")
    if tick["exchange"] != "NSE":
        failures.append(f"exchange came back as {tick['exchange']!r}")
    if tick["token"] != "2885":
        failures.append(f"token came back as {tick['token']!r}")
    if tick["tick_mode"] != packets.TICK_MODE_PRICE_DETAILED:
        failures.append(f"tick mode came back as {tick['tick_mode']!r}")
    if not tick["tradable"]:
        failures.append("a tradeable scrip came back as not tradeable")
    if tick["price_divisor"] != packets.PRICE_DIVISOR:
        failures.append(f"price divisor came back as {tick['price_divisor']!r}")
    if tick["arrival_time"] != ARRIVAL_TIME:
        failures.append("the arrival time was not carried onto the tick")
    return failures


def check_index_decodes_through_field_six():
    """
    An index message is read as an index, not as a price message missing most of its fields.

    StocksLiveIndicesProto puts its value in field 2, which in a price message is the day's open. Reading an index with the price reader would report the NIFTY level as an opening price and leave the last price empty, and nothing about the result would look wrong. The arm is therefore chosen by the response's field number, and this check pins that choice.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    payload = encode_live_indices_payload(1757059230000.0, 25432.85)
    frame = nats_message(INDEX_SUBJECT, encode_response("NIFTY", None, 1, packets.RESPONSE_LIVE_INDICES_FIELD, payload))
    decoded = packets.decode_frame(frame, ARRIVAL_TIME)
    if len(decoded) != 1:
        return [f"expected one tick, got {len(decoded)}"]

    tick = decoded[0]
    if tick["last_price"] != 254328500:
        failures.append(f"last_price came back as {tick['last_price']!r}, expected 254328500")
    if tick.get("open_price") is not None:
        failures.append(f"open_price came back as {tick.get('open_price')!r}, which means the index was read with the price field table")
    if tick.get("volume_traded") is not None:
        failures.append("an index reported a traded volume, which means it was read with the price field table")
    if tick["tick_mode"] != packets.TICK_MODE_INDEX_VALUE:
        failures.append(f"tick mode came back as {tick['tick_mode']!r}")
    if tick["tradable"]:
        failures.append("an index came back as tradeable")
    if tick["symbol"] != "NIFTY":
        failures.append(f"symbol came back as {tick['symbol']!r}")
    if tick["token"] != "26000":
        failures.append(f"token came back as {tick['token']!r}")
    return failures


def check_subject_parsing_all_six_families():
    """
    Every subject family the feed subscribes to parses to its exchange, group and token.

    The subject is the only place the exchange token appears, so a mis-parse attributes one instrument's data to another, which is the worst failure this decoder can make.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    expected_subjects = [
        (EQUITY_SUBJECT, "eq", "nse", "price_detailed", "2885"),
        (BSE_EQUITY_SUBJECT, "eq", "bse", "price_detailed", "11536"),
        (DERIVATIVE_SUBJECT, "fo", "nse", "price_detailed", "35001"),
        (BSE_DERIVATIVE_SUBJECT, "fo", "bse", "price_detailed", "35001"),
        (INDEX_SUBJECT, "indices", "nse", "price", "26000"),
        (BSE_INDEX_SUBJECT, "indices", "bse", "price", "26000"),
    ]
    for subject, expected_group, expected_exchange, expected_feed, expected_token in expected_subjects:
        group, exchange, feed_name, exchange_token = packets.parse_subject(subject)
        if (group, exchange, feed_name, exchange_token) != (expected_group, expected_exchange, expected_feed, expected_token):
            failures.append(f"{subject} parsed to {(group, exchange, feed_name, exchange_token)!r}")

    for malformed in ("ld/eq/nse/price", "/x/y/z/price.1", "/ld/eq/nse/price.", "/ld/eq/nse/price_detailed", "", "MSG"):
        if packets.parse_subject(malformed) != (None, None, None, None):
            failures.append(f"the malformed subject {malformed!r} parsed to something")
    return failures


def check_message_header_variants():
    """
    The message header is read correctly with and without a reply-to, and rejected when unreadable.

    The declared payload count is the only safe boundary, because a protobuf payload can contain the same two bytes that end the header line. A reply-to subject would shift the count's position, so the parser takes the last field rather than a fixed one.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    payload = INDEX_PAYLOAD

    plain = b"MSG /ld/indices/nse/price.26000 7 " + str(len(payload)).encode() + packets.LINE_TERMINATOR + payload + packets.LINE_TERMINATOR
    subject, read_payload = packets.parse_message_header(plain)
    if subject != INDEX_SUBJECT or read_payload != payload:
        failures.append("a plain header parsed wrongly")

    with_reply = b"MSG /ld/indices/nse/price.26000 7 _INBOX.abc " + str(len(payload)).encode() + packets.LINE_TERMINATOR + payload + packets.LINE_TERMINATOR
    subject, read_payload = packets.parse_message_header(with_reply)
    if subject != INDEX_SUBJECT or read_payload != payload:
        failures.append("a header carrying a reply-to parsed wrongly")

    for broken in (
        b"PING\r\n",
        b"MSG\r\n",
        b"MSG /ld/indices/nse/price.26000 7 notanumber\r\n",
        b"MSG /ld/indices/nse/price.26000 7 999\r\nshort",
        b"MSG /ld/indices/nse/price.26000 7 -1\r\n",
        b"MSG /ld/indices/nse/price.26000 7 5",
    ):
        if packets.parse_message_header(broken) != (None, None):
            failures.append(f"the broken frame {broken!r} parsed to something")
        if packets.frame_packet_count(broken) != 0:
            failures.append(f"the broken frame {broken!r} counted a packet")

    good = plain
    if packets.frame_packet_count(good) != 1:
        failures.append(f"a market data message counted {packets.frame_packet_count(good)} packets, expected 1")
    return failures


def check_payload_containing_crlf_is_not_truncated():
    """
    A payload containing the two bytes that end a control line is not cut at them.

    This is the case the line-splitting approach would get wrong, and why the declared length is the only boundary honoured. The golden carriage return payload carries one inside its symbol field.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    frame = nats_message(EQUITY_SUBJECT.replace("2885", "11536"), CARRIAGE_RETURN_PAYLOAD)
    decoded = packets.decode_frame(frame, ARRIVAL_TIME)
    if len(decoded) != 1:
        return [f"expected one tick, got {len(decoded)}"]

    tick = decoded[0]
    if tick["symbol"] != "A\r\nB":
        failures.append(f"the symbol came back as {tick['symbol']!r}, expected 'A\\r\\nB'")
    if tick["last_price"] != 130000:
        failures.append(f"last_price came back as {tick['last_price']!r}, expected 130000")
    return failures


def check_multiple_messages_in_one_websocket_frame():
    """
    One websocket frame carrying several message operations yields several ticks.

    NATS writes messages as it publishes them, so coalescing is the normal case under load rather than an edge.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    blob = (
        b"INFO {\"nonce\":\"abc\"}\r\n"
        + nats_message(EQUITY_SUBJECT, EQUITY_PAYLOAD, 1)
        + b"PING\r\n"
        + nats_message(INDEX_SUBJECT, INDEX_PAYLOAD, 2)
        + b"+OK\r\n"
        + nats_message(BSE_EQUITY_SUBJECT, CURRENCY_PAYLOAD, 3)
    )
    messages = [content for kind, content in ProtocolReader().feed(blob) if kind == connection.PROTOCOL_MESSAGE_KIND]
    if len(messages) != 3:
        return [f"the reader split the frame into {len(messages)} messages, expected 3"]

    symbols = []
    for message in messages:
        decoded = packets.decode_frame(message, ARRIVAL_TIME)
        if len(decoded) != 1:
            failures.append(f"a coalesced message decoded to {len(decoded)} ticks")
        else:
            symbols.append(decoded[0]["symbol"])
    if symbols != ["RELIANCE", "NIFTY", "USDINR25SEPFUT"]:
        failures.append(f"the coalesced messages decoded to {symbols!r}")
    return failures


def check_message_split_across_two_frames():
    """
    A message split across websocket frames, at every possible cut point, reassembles into one tick.

    The websocket fragments the byte stream wherever the transport decides, so the reader has to be right about every boundary, not just a convenient one.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    whole = nats_message(EQUITY_SUBJECT, EQUITY_PAYLOAD, 1)
    for cut in range(1, len(whole)):
        reader = ProtocolReader()
        first = list(reader.feed(whole[:cut]))
        second = list(reader.feed(whole[cut:]))
        messages = [content for kind, content in first + second if kind == connection.PROTOCOL_MESSAGE_KIND]
        if len(messages) != 1:
            failures.append(f"cut at {cut}: {len(messages)} messages instead of 1")
            continue
        decoded = packets.decode_frame(messages[0], ARRIVAL_TIME)
        if len(decoded) != 1 or decoded[0]["symbol"] != "RELIANCE":
            failures.append(f"cut at {cut}: the reassembled message decoded to {decoded!r}")
    return failures


def check_control_operations_do_not_disturb_framing():
    """
    PING, PONG, +OK and -ERR operations interleaved with data leave every message intact.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    blob = (
        nats_message(EQUITY_SUBJECT, EQUITY_PAYLOAD, 1)
        + b"PING\r\n"
        + nats_message(INDEX_SUBJECT, INDEX_PAYLOAD, 2)
        + b"+OK\r\n-ERR 'something'\r\nPONG\r\n"
        + nats_message(BSE_EQUITY_SUBJECT, CURRENCY_PAYLOAD, 3)
    )
    reader = ProtocolReader()
    kinds = [kind for kind, _ in reader.feed(blob)]
    if kinds.count(connection.PROTOCOL_MESSAGE_KIND) != 3:
        failures.append(f"the reader yielded {kinds.count(connection.PROTOCOL_MESSAGE_KIND)} messages among {kinds!r}")
    if kinds.count(connection.PROTOCOL_OPERATION_KIND) != 4:
        failures.append(f"the reader yielded {kinds.count(connection.PROTOCOL_OPERATION_KIND)} control operations, expected 4")

    for kind, content in ProtocolReader().feed(blob):
        if kind == connection.PROTOCOL_OPERATION_KIND and content.startswith(b"-ERR"):
            if content != b"-ERR 'something'":
                failures.append(f"the error line came through as {content!r}")
    return failures


def check_truncated_payload_stops_cleanly():
    """
    A message cut off anywhere yields what was readable and never raises.

    This runs inside the socket read loop and inside archive replay, so one malformed record must not take down a connection carrying thousands of instruments.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    whole = nats_message(EQUITY_SUBJECT, EQUITY_PAYLOAD, 1)
    for cut in range(1, len(whole)):
        try:
            packets.decode_frame(whole[:cut], ARRIVAL_TIME)
        except Exception as error:
            failures.append(f"a message cut to {cut} bytes raised {type(error).__name__}: {error}")
            break

    for cut in range(1, len(EQUITY_PAYLOAD)):
        try:
            packets.decode_live_price(EQUITY_PAYLOAD[:cut])
        except Exception as error:
            failures.append(f"a payload cut to {cut} bytes raised {type(error).__name__}: {error}")
            break
    return failures


def check_unknown_fields_are_skipped():
    """
    An unknown field number and an unknown oneof arm are stepped over rather than misread.

    Groww can add fields to the schema at any time, and the market depth arm is deliberately not decoded on this branch, so skipping by wire type is what keeps a schema addition from breaking the reader.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []

    decorated = (
        encode_varint((99 << 3) | packets.WIRE_TYPE_VARINT) + encode_varint(12345)
        + encode_field_tag(15, packets.WIRE_TYPE_THIRTY_TWO_BIT) + b"\x00\x00\x00\x00"
        + encode_length_field(packets.RESPONSE_MARKET_DEPTH_FIELD, DEPTH_PAYLOAD)
        + EQUITY_PAYLOAD
    )
    decoded = packets.decode_frame(nats_message(EQUITY_SUBJECT, decorated, 1), ARRIVAL_TIME)
    if len(decoded) != 1:
        failures.append(f"a response carrying unknown fields decoded to {len(decoded)} ticks, expected 1")
    elif decoded[0]["symbol"] != "RELIANCE" or decoded[0]["last_price"] != 14187500:
        failures.append(f"the unknown fields disturbed the known ones: {decoded[0]!r}")

    depth_only = encode_response("RELIANCE", None, 1, packets.RESPONSE_MARKET_DEPTH_FIELD, DEPTH_PAYLOAD)
    if packets.decode_frame(nats_message(EQUITY_SUBJECT, depth_only, 1), ARRIVAL_TIME) != []:
        failures.append("a depth-only response decoded to a tick, but depth is not decoded on this branch")
    return failures


def check_price_scaling_is_exact():
    """
    Prices scale exactly for the values the wire actually carries.

    A currency price has four decimal places and a rupee price often has no exact binary representation, so the rounding at divisor 10000 has to land on the right integer for both.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    cases = [
        (88.4275, 884275),
        (1418.75, 14187500),
        (1401.1, 14011000),
        (25432.85, 254328500),
        (0.0, 0),
        (13.0, 130000),
    ]
    for value, expected in cases:
        actual = packets.scaled_price(value)
        if actual != expected:
            failures.append(f"scaled_price({value!r}) came back as {actual!r}, expected {expected}")

    if packets.scaled_price(None) is not None:
        failures.append("scaled_price(None) came back as something")

    for value, expected in ((8321455.0, 8321455), (4218750.0, 4218750), (0.5, 0)):
        if packets.rounded_quantity(value) != expected:
            failures.append(f"rounded_quantity({value!r}) came back as {packets.rounded_quantity(value)!r}, expected {expected}")
    return failures


def check_epoch_timestamps():
    """
    The millisecond timestamp converts, and the implausible ones convert to nothing.

    Groww sends the timestamp as a double in milliseconds. A value of zero, an absent one and one from beyond the plausible range all read as None rather than as a date in 1970 or fifty years out.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    if packets.epoch_milliseconds_to_datetime(None) is not None:
        failures.append("an absent timestamp came back as something")
    if packets.epoch_milliseconds_to_datetime(0.0) is not None:
        failures.append("a zero timestamp came back as something")
    if packets.epoch_milliseconds_to_datetime(-1.0) is not None:
        failures.append("a negative timestamp came back as something")
    if packets.epoch_milliseconds_to_datetime(4102444800000.0) is not None:
        failures.append("a timestamp beyond the plausible range came back as something")

    converted = packets.epoch_milliseconds_to_datetime(1757059200000.0)
    if not isinstance(converted, datetime):
        failures.append(f"a valid timestamp came back as {converted!r}, which is not a datetime")
    return failures


def check_golden_frames():
    """
    Payloads encoded by Groww's own generated code decode here to exactly the values they were built from.

    This is what pins the hand-written protobuf reader against the official encoder. The bytes were produced once by Groww's generated `stocks_socket_response_pb2` module and stored, so the check needs neither the SDK nor a network. They must not be regenerated with this project's own encoder.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []

    equity_frame = nats_message(EQUITY_SUBJECT, EQUITY_PAYLOAD, 1)
    decoded = packets.decode_frame(equity_frame, ARRIVAL_TIME)
    if len(decoded) != 1:
        return [f"the golden equity payload decoded to {len(decoded)} ticks, expected 1"]
    equity = decoded[0]
    expected_equity = {
        "symbol": "RELIANCE",
        "exchange": "NSE",
        "segment": None,
        "token": "2885",
        "tick_mode": "price_detailed",
        "tradable": True,
        "open_price": 14011000,
        "high_price": 14252500,
        "low_price": 13960500,
        "close_price": 13999000,
        "volume_traded": 8321455,
        "traded_value": 117500000000000,
        "total_buy_quantity": 1250,
        "total_sell_quantity": 3175,
        "average_traded_price": 14123456,
        "high_price_range": 15398900,
        "low_price_range": 12599100,
        "last_price": 14187500,
        "open_interest": None,
        "low_trade_range": 13000000,
        "high_trade_range": 15000000,
        "price_divisor": 10000,
    }
    for field_name, expected in expected_equity.items():
        if equity.get(field_name) != expected:
            failures.append(f"equity {field_name} came back as {equity.get(field_name)!r}, expected {expected!r}")
    if equity["exchange_timestamp"] != packets.epoch_milliseconds_to_datetime(1757059200000.0):
        failures.append(f"equity exchange_timestamp came back as {equity['exchange_timestamp']!r}")
    if packets.frame_packet_count(equity_frame) != 1:
        failures.append("the golden equity message counted the wrong number of packets")

    decoded = packets.decode_frame(nats_message(DERIVATIVE_SUBJECT, DERIVATIVE_PAYLOAD, 1), ARRIVAL_TIME)
    if len(decoded) != 1:
        failures.append(f"the golden derivative payload decoded to {len(decoded)} ticks, expected 1")
    else:
        derivative = decoded[0]
        expected_derivative = {
            "symbol": "NIFTY26SEP25000CE",
            "exchange": "NSE",
            "segment": "FNO",
            "token": "35001",
            "last_price": 3124500,
            "volume_traded": 1875000,
            "open_interest": 4218750,
            "open_price": None,
            "total_buy_quantity": None,
        }
        for field_name, expected in expected_derivative.items():
            if derivative.get(field_name) != expected:
                failures.append(f"derivative {field_name} came back as {derivative.get(field_name)!r}, expected {expected!r}")

    decoded = packets.decode_frame(nats_message(INDEX_SUBJECT, INDEX_PAYLOAD, 1), ARRIVAL_TIME)
    if len(decoded) != 1:
        failures.append(f"the golden index payload decoded to {len(decoded)} ticks, expected 1")
    else:
        index = decoded[0]
        expected_index = {
            "symbol": "NIFTY",
            "exchange": "NSE",
            "token": "26000",
            "tick_mode": "index_value",
            "tradable": False,
            "last_price": 254328500,
            "open_price": None,
            "volume_traded": None,
        }
        for field_name, expected in expected_index.items():
            if index.get(field_name) != expected:
                failures.append(f"index {field_name} came back as {index.get(field_name)!r}, expected {expected!r}")

    decoded = packets.decode_frame(nats_message(BSE_EQUITY_SUBJECT, CURRENCY_PAYLOAD, 1), ARRIVAL_TIME)
    if len(decoded) != 1:
        failures.append(f"the golden currency payload decoded to {len(decoded)} ticks, expected 1")
    else:
        currency = decoded[0]
        expected_currency = {
            "symbol": "USDINR25SEPFUT",
            "segment": "CURRENCY",
            "close_price": 883950,
            "last_price": 884275,
            "open_price": None,
        }
        for field_name, expected in expected_currency.items():
            if currency.get(field_name) != expected:
                failures.append(f"currency {field_name} came back as {currency.get(field_name)!r}, expected {expected!r}")

    decoded = packets.decode_frame(nats_message(EQUITY_SUBJECT.replace("2885", "11536"), CARRIAGE_RETURN_PAYLOAD, 1), ARRIVAL_TIME)
    if len(decoded) != 1:
        failures.append(f"the golden carriage return payload decoded to {len(decoded)} ticks, expected 1")
    else:
        carriage = decoded[0]
        if carriage["symbol"] != "A\r\nB" or carriage["last_price"] != 130000:
            failures.append(f"the carriage return message came back as {carriage!r}")

    if packets.decode_frame(nats_message(EQUITY_SUBJECT, DEPTH_PAYLOAD, 1), ARRIVAL_TIME) != []:
        failures.append("the golden depth payload decoded to a tick, but depth is not decoded on this branch")
    return failures


def check_connect_command_shape():
    """
    The CONNECT operation carries the fields the NATS handshake expects.

    The connection builder and the server would otherwise agree with themselves about a renamed field, so this pins the JSON rather than the names.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    command = connection.build_connect_command("jwt-token", "signature-text")
    if not command.startswith(b"CONNECT ") or not command.endswith(packets.LINE_TERMINATOR):
        failures.append(f"the CONNECT command is {command[:20]!r}...{command[-10:]!r}")
        return failures

    document = json.loads(command[len(b"CONNECT "):-len(packets.LINE_TERMINATOR)])
    if document.get("jwt") != "jwt-token":
        failures.append(f"the CONNECT command carries jwt {document.get('jwt')!r}")
    if document.get("sig") != "signature-text":
        failures.append(f"the CONNECT command carries sig {document.get('sig')!r}")
    if document.get("verbose") is not False or document.get("pedantic") is not False:
        failures.append("the CONNECT command did not set verbose and pedantic to false")
    if document.get("protocol") != 1:
        failures.append(f"the CONNECT command declared protocol {document.get('protocol')!r}, expected 1")
    return failures


def check_reader_rejects_unreadable_headers():
    """
    A message header that cannot be read ends the session rather than desynchronising the stream.

    Once the reader loses the message boundaries, every subsequent byte is garbage and the only honest recovery is to drop the socket and reconnect. A header declaring an implausible payload is treated the same way.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    for broken in (
        b"MSG /ld/eq/nse/price_detailed.2885 1 notanumber\r\n",
        b"MSG /ld/eq/nse/price_detailed.2885 1 999999999999\r\n",
    ):
        try:
            list(ProtocolReader().feed(broken + b"\x00" * 64))
        except GrowwConnectionError:
            continue
        except Exception as error:
            failures.append(f"the broken header {broken!r} raised {type(error).__name__}, expected GrowwConnectionError")
            continue
        failures.append(f"the broken header {broken!r} was accepted")
    return failures


def check_compare_tick_to_quote():
    """
    The comparison used by the oracle mode agrees when it should and disagrees when it should.

    The oracle is only as good as its comparison, so the comparison is checked here on values whose answer is known rather than only being exercised against a live market.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    tick = {
        "last_price": 4269000,
        "open_price": 4250000,
        "high_price": 4280000,
        "low_price": 4240000,
        "close_price": 4252000,
        "average_traded_price": 4260000,
        "volume_traded": 3045212,
        "price_divisor": 10000,
    }
    quote = {
        "last_price": 426.90,
        "ohlc": {
            "open": 425.00,
            "high": 428.00,
            "low": 424.00,
            "close": 425.20,
        },
        "average_price": 426.00,
        "volume": 3045212,
    }
    agreements, disagreements = compare_tick_to_quote(tick, quote)
    if disagreements:
        failures.append(f"an exact match reported disagreements: {disagreements!r}")
    if len(agreements) != 7:
        failures.append(f"an exact match compared {len(agreements)} fields, expected 7")

    wrong = dict(tick)
    wrong["last_price"] = 426900
    _, disagreements = compare_tick_to_quote(wrong, quote)
    if not disagreements:
        failures.append("a price out by a factor of ten was not reported")
    return failures


def check_implied_scale_ratio():
    """
    The implied scale measurement recovers a divisor it was not told.

    This is the check that settles whether the ticks' divisor agrees with Groww's own REST prices. If the divisor is wrong, this measurement shows a clean factor rather than noise, so it has to be right before the live run rather than after it.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    ticks_by_symbol = {
        "RELIANCE": {"last_price": 4269000, "price_divisor": 10000},
        "INFY": {"last_price": 15005000, "price_divisor": 10000},
    }
    quotes = {
        "RELIANCE": {"last_price": 426.90},
        "INFY": {"last_price": 1500.50},
    }
    ratios = implied_scale_ratios(ticks_by_symbol, quotes)
    if not ratios:
        return ["the implied scale measurement produced nothing"]
    median = statistics.median(ratios)
    if abs(median - 1.0) > 0.01:
        failures.append(f"the implied scale measured {median}, expected 1.0")
    return failures


SYNTHETIC_CHECKS = [
    check_field_tables_are_pinned_literally,
    check_every_price_field_round_trips,
    check_index_decodes_through_field_six,
    check_subject_parsing_all_six_families,
    check_message_header_variants,
    check_payload_containing_crlf_is_not_truncated,
    check_multiple_messages_in_one_websocket_frame,
    check_message_split_across_two_frames,
    check_control_operations_do_not_disturb_framing,
    check_truncated_payload_stops_cleanly,
    check_unknown_fields_are_skipped,
    check_price_scaling_is_exact,
    check_epoch_timestamps,
    check_golden_frames,
    check_connect_command_shape,
    check_reader_rejects_unreadable_headers,
    check_compare_tick_to_quote,
    check_implied_scale_ratio,
]


def run_synthetic():
    """
    Run every synthetic check and report what failed.

    Returns:
        int: 0 when every check passed, 1 otherwise.
    """
    failed_checks = 0
    for check in SYNTHETIC_CHECKS:
        failures = check()
        if failures:
            failed_checks = failed_checks + 1
            print(f"FAIL  {check.__name__}")
            for failure in failures:
                print(f"        {failure}")
        else:
            print(f"ok    {check.__name__}")

    print()
    print(f"{len(SYNTHETIC_CHECKS) - failed_checks} of {len(SYNTHETIC_CHECKS)} checks passed.")
    if failed_checks:
        return 1
    return 0


def select_verification_instruments(engine, per_exchange):
    """
    Choose a spread of live instruments to compare, a few from each segment.

    A spread matters more than a large sample. Groww's segments differ in what they send, so a hundred NSE equities would settle one segment and say nothing about the others, while a few from each settles all of them.

    The two dates are looked up first and passed in as parameters rather than written as sub-selects inside the main query. Both raw tables are TimescaleDB hypertables, and a sub-select makes the partitioning column's value a runtime value, which under a parallel plan makes chunk exclusion intermittently exclude every chunk and return no rows. The same query returned the right rows on some runs and none on others, on fresh connections. Resolving the dates first makes them plan-time constants and the result stable.

    Args:
        engine: A SQLAlchemy engine for the tradingmachine database.
        per_exchange (int): How many instruments to take from each segment.

    Returns:
        list[dict]: One dict per instrument with keys "exchange", "segment", "trading_symbol" and "exchange_token".

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the instrument tables cannot be read.
    """
    with engine.connect() as database_connection:
        download_date = database_connection.execute(sql_text(
            "SELECT max(download_date) FROM instruments.groww"
        )).scalar()
        mapping_date = database_connection.execute(sql_text(
            "SELECT max(mapping_date) FROM instruments.broker_mappings WHERE broker = 'groww'"
        )).scalar()
        if download_date is None or mapping_date is None:
            return []

        rows = database_connection.execute(
            sql_text(
                "SELECT g.exchange, g.segment, g.trading_symbol, g.exchange_token "
                "FROM instruments.groww g "
                "JOIN instruments.broker_mappings b ON b.broker_token = g.exchange_token AND b.broker = 'groww' "
                "JOIN instruments.master m ON m.instrument_id = b.instrument_id "
                "WHERE g.download_date = :download_date "
                "  AND b.mapping_date = :mapping_date "
                "  AND (m.expiry_date IS NULL OR m.expiry_date > CURRENT_DATE)"
            ),
            {
                "download_date": download_date,
                "mapping_date": mapping_date,
            },
        ).all()

    by_segment = {}
    for row in rows:
        if not row.segment or row.segment not in ("CASH", "FNO"):
            continue
        if row.segment not in by_segment:
            by_segment[row.segment] = []
        if len(by_segment[row.segment]) >= per_exchange:
            continue
        by_segment[row.segment].append({
            "exchange": row.exchange,
            "segment": row.segment,
            "trading_symbol": row.trading_symbol,
            "exchange_token": row.exchange_token,
        })

    chosen = []
    for segment in sorted(by_segment):
        chosen.extend(by_segment[segment])
    return chosen


def subject_for_instrument(instrument):
    """
    Build the price_detailed subject one instrument's quote is published on.

    Args:
        instrument (dict): One row from select_verification_instruments.

    Returns:
        str: The subject, for example "/ld/eq/nse/price_detailed.2885".
    """
    if instrument["segment"] == "FNO":
        subject_group = "fo"
    else:
        subject_group = "eq"
    return f"/ld/{subject_group}/{instrument['exchange'].lower()}/price_detailed.{instrument['exchange_token']}"


async def capture_ticks_async(socket_token, seed, instruments, seconds):
    """
    Open one connection, subscribe the chosen instruments and collect what arrives.

    Args:
        socket_token (str): The socket token minted for this session's key.
        seed (bytes): The private key that signs each session's nonce.
        instruments (list[dict]): The instruments to subscribe.
        seconds (float): How long to keep the connection open.

    Returns:
        dict: The most recent complete tick per exchange token.

    Raises:
        stream.groww.connection.GrowwAuthenticationError: If Groww rejected the credentials.
    """
    subjects = [subject_for_instrument(instrument) for instrument in instruments]
    ticks_by_token = {}

    def on_frame(arrival_time_nanoseconds, frame):
        arrival_time = datetime.fromtimestamp(arrival_time_nanoseconds / 1_000_000_000)
        for tick in packets.decode_frame(frame, arrival_time):
            if tick["token"] is not None:
                ticks_by_token[tick["token"]] = tick

    live_connection = GrowwConnection(
        socket_token=socket_token,
        seed=seed,
        subjects=subjects,
        on_frame=on_frame,
        maximum_reconnect_attempts=0,
    )
    stop_event = asyncio.Event()
    task = asyncio.create_task(live_connection.run(stop_event))

    await asyncio.sleep(seconds)
    stop_event.set()
    if not task.done():
        try:
            await asyncio.wait_for(task, timeout=10)
        except (asyncio.TimeoutError, Exception):
            task.cancel()

    return ticks_by_token


def fetch_quote(access_token, instrument):
    """
    Ask Groww's REST endpoint what one instrument is worth.

    The endpoint takes one instrument per call against ten requests a second and three hundred a minute, so this is paced by its caller rather than going as fast as it can.

    Args:
        access_token (str): Today's Groww access token.
        instrument (dict): One row from select_verification_instruments.

    Returns:
        dict | None: The quote's payload, or None when the endpoint did not answer for this instrument.

    Raises:
        requests.RequestException: If the endpoint cannot be reached.
    """
    response = requests.get(
        QUOTE_ENDPOINT,
        params={
            "exchange": instrument["exchange"],
            "segment": instrument["segment"],
            "trading_symbol": instrument["trading_symbol"],
        },
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "x-client-id": "growwapi",
            "x-client-platform": "growwapi-python-client",
            "x-api-version": "1.0",
        },
        timeout=30,
    )
    body = response.json()
    payload = body.get("payload", body)
    if not isinstance(payload, dict):
        return None
    return payload


COMPARABLE_FIELDS = [
    ("last_price", "last_price"),
    ("open_price", "ohlc.open"),
    ("high_price", "ohlc.high"),
    ("low_price", "ohlc.low"),
    ("close_price", "ohlc.close"),
    ("average_traded_price", "average_price"),
]


def read_quote_value(quote, quote_field):
    """
    Read one value out of a REST quote, following dotted paths into nested objects.

    Args:
        quote (dict): The quote's payload.
        quote_field (str): The field to read, dotted for a nested one.

    Returns:
        float | None: The value, or None when it is absent.
    """
    value = quote
    for part in quote_field.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def compare_tick_to_quote(tick, quote):
    """
    Compare one decoded tick against the REST endpoint's view of the same instrument.

    Prices are divided by the tick's own divisor before comparing, which is the whole point: a divisor that is wrong shows up here as every price being out by the same factor, rather than as one field looking odd.

    Args:
        tick (dict): One tick from the decoder.
        quote (dict): The REST endpoint's payload for the same instrument.

    Returns:
        tuple: An (agreements, disagreements) pair of lists, each holding one description per field compared.
    """
    agreements = []
    disagreements = []
    divisor = tick.get("price_divisor") or 1

    for tick_field, quote_field in COMPARABLE_FIELDS:
        tick_value = tick.get(tick_field)
        quote_value = read_quote_value(quote, quote_field)
        if tick_value is None or quote_value is None:
            continue
        converted = tick_value / divisor
        if quote_value == 0:
            difference = abs(converted)
        else:
            difference = abs(converted - quote_value) / abs(quote_value)
        if difference <= VERIFICATION_TOLERANCE:
            agreements.append(f"{tick_field}={converted:.4f}")
        else:
            disagreements.append(f"{tick_field}: websocket {converted:.4f} vs REST {quote_value:.4f}")

    tick_volume = tick.get("volume_traded")
    quote_volume = quote.get("volume")
    if tick_volume is not None and quote_volume is not None:
        if tick_volume == quote_volume:
            agreements.append(f"volume_traded={tick_volume}")
        else:
            disagreements.append(f"volume_traded: websocket {tick_volume} vs REST {quote_volume}")

    return (agreements, disagreements)


def implied_scale_ratios(ticks_by_symbol, quotes):
    """
    Measure what divisor the ticks' prices actually imply, ignoring what the decoder assumed.

    Dividing the tick's price, already divided by its own divisor, by the REST price gives the scale directly, so a decoder scaling wrongly shows up as a clean factor rather than as noise.

    Args:
        ticks_by_symbol (dict): One tick per trading symbol.
        quotes (dict): The REST payload per the same trading symbols.

    Returns:
        list[float]: One implied scale per instrument that could be measured.
    """
    ratios = []
    for symbol, tick in ticks_by_symbol.items():
        quote = quotes.get(symbol)
        if quote is None:
            continue
        wire_price = tick.get("last_price")
        divisor = tick.get("price_divisor") or 1
        rest_price = quote.get("last_price")
        if not wire_price or not rest_price:
            continue
        ratios.append(wire_price / divisor / rest_price)
    return ratios


def run_against_rest(per_exchange, seconds):
    """
    Capture live ticks, ask the REST endpoint about the same instruments, and compare.

    Args:
        per_exchange (int): How many instruments to take from each segment.
        seconds (float): How long to hold the websocket open.

    Returns:
        int: 0 when every instrument that could be compared agreed, 1 otherwise.

    Raises:
        stream.groww.credentials.GrowwCredentialsError: If the credentials are missing or expired.
    """
    socket_token, seed = websocket_credentials()
    access_token = stored_access_token()

    engine = create_engine(postgres_configuration["connection_string"])
    instruments = select_verification_instruments(engine, per_exchange)
    print(f"comparing {len(instruments)} instruments across {len({instrument['segment'] for instrument in instruments})} segments")

    ticks_by_token = asyncio.run(capture_ticks_async(socket_token, seed, instruments, seconds))
    print(f"captured ticks for {len(ticks_by_token)} of {len(instruments)} instruments in {seconds:.0f} seconds")

    ticks_by_symbol = {}
    for instrument in instruments:
        if instrument["exchange_token"] in ticks_by_token:
            ticks_by_symbol[instrument["trading_symbol"]] = ticks_by_token[instrument["exchange_token"]]

    missing = [instrument["trading_symbol"] for instrument in instruments if instrument["trading_symbol"] not in ticks_by_symbol]
    if missing:
        print(f"no tick arrived for {len(missing)}: {', '.join(missing[:10])}{' ...' if len(missing) > 10 else ''}")

    quotes = {}
    for instrument in instruments:
        symbol = instrument["trading_symbol"]
        if symbol not in ticks_by_symbol or symbol in quotes:
            continue
        quotes[symbol] = fetch_quote(access_token, instrument)
        time.sleep(QUOTE_REQUEST_PAUSE_SECONDS)
    answered = {symbol: quote for symbol, quote in quotes.items() if quote is not None}
    print(f"the REST endpoint answered for {len(answered)} of them")
    print()

    total_disagreements = 0
    for symbol in sorted(answered):
        agreements, disagreements = compare_tick_to_quote(ticks_by_symbol[symbol], answered[symbol])
        if disagreements:
            total_disagreements = total_disagreements + len(disagreements)
            print(f"MISMATCH {symbol}")
            for disagreement in disagreements:
                print(f"           {disagreement}")
        else:
            print(f"ok       {symbol}  ({len(agreements)} fields agree)")

    print()
    print("implied price scale per segment")
    by_segment = {}
    for instrument in instruments:
        symbol = instrument["trading_symbol"]
        if symbol not in ticks_by_symbol or symbol not in answered:
            continue
        by_segment.setdefault(instrument["segment"], {})[symbol] = ticks_by_symbol[symbol]

    for segment in sorted(by_segment):
        ratios = implied_scale_ratios(by_segment[segment], answered)
        if not ratios:
            continue
        print(
            f"  {segment:8} measured {statistics.median(ratios):8.4f}   "
            f"decoder used divisor {next(iter(by_segment[segment].values())).get('price_divisor')}   "
            f"({len(ratios)} instruments)"
        )

    print()
    if total_disagreements:
        print(f"{total_disagreements} disagreements.")
        return 1
    print("every field that could be compared agrees.")
    return 0


def main():
    """
    Parse the command line and run the requested checks.

    Returns:
        None.

    Raises:
        SystemExit: Always, with the checks' exit status.
    """
    parser = argparse.ArgumentParser(description="Verify the Groww stream decoder.")
    parser.add_argument("--synthetic", action="store_true", help="Run the offline checks, which need no network.")
    parser.add_argument("--against-rest", action="store_true", help="Compare live websocket ticks against Groww's own REST quotes.")
    parser.add_argument("--per-exchange", type=int, default=3, help="How many instruments to take from each segment.")
    parser.add_argument("--seconds", type=float, default=12.0, help="How long to hold the websocket open.")
    arguments = parser.parse_args()

    if not arguments.synthetic and not arguments.against_rest:
        parser.error("choose --synthetic, --against-rest, or both.")

    status = 0
    if arguments.synthetic:
        status = run_synthetic()
    if arguments.against_rest:
        print()
        status = max(status, run_against_rest(arguments.per_exchange, arguments.seconds))
    raise SystemExit(status)


if __name__ == "__main__":
    main()