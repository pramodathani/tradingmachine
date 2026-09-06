"""
Decoding of Groww's market data messages.

Groww is the only broker here whose feed is a message bus rather than a stream of broker-specific frames. The transport is NATS carried over a websocket, and the record this module decodes is one complete NATS `MSG` operation: a header line naming the subject and the payload length, then that many bytes of Protocol Buffers. The connection driver reassembles those boundaries and archives the whole operation, header included, so a record replayed out of the archive decodes exactly as it did live. That is why the subject is parsed here rather than passed in alongside the bytes.

Parsing the subject is not decoration. Groww's payload carries the instrument's symbol, its exchange and its segment, but it does not carry the exchange token, and the exchange token is what `instruments.groww` and the mapping tables key on. The token exists only in the subject the message arrived on.

The messages are decoded by hand rather than by generated code, for the same reasons `stream/fyers/depth_packets.py` gives. The schema is four messages, it uses two of the six protobuf wire types, and a varint reader with a tag loop covers it in less code than a generated module's import machinery. It adds no dependency and it keeps this module testable on bytes alone. The schema was read out of the descriptor embedded in `growwapi`'s generated `stocks_socket_response_pb2`, and the checks in `verify_stream.py` pin this reader against payloads that module encoded.

Two things about this schema are worth knowing before reading the field tables.

Every scalar is a `double`, including the ones that are plainly counts: volume, bid quantity, offer quantity and open interest all arrive as floating point. So does the timestamp, in milliseconds. Nothing here is an integer on the wire.

It is proto3 without wrappers, so a field whose value is the default is not transmitted at all. An absent field and a zero one are the same bytes. This module reports absent as None rather than as zero, because None is what the tick table's nullable columns mean and because a price of zero and a price that was not sent are different claims. The consequence, which cannot be worked around from this end, is that a genuine zero also reads as None.
"""

import struct
from datetime import datetime

WIRE_TYPE_VARINT = 0
WIRE_TYPE_SIXTY_FOUR_BIT = 1
WIRE_TYPE_LENGTH_DELIMITED = 2
WIRE_TYPE_THIRTY_TWO_BIT = 5

DOUBLE_STRUCT = struct.Struct("<d")

RESPONSE_SYMBOL_FIELD = 1
RESPONSE_SEGMENT_FIELD = 2
RESPONSE_EXCHANGE_FIELD = 3
RESPONSE_LIVE_PRICE_FIELD = 4
RESPONSE_MARKET_DEPTH_FIELD = 5
RESPONSE_LIVE_INDICES_FIELD = 6

LIVE_PRICE_FIELD_NAMES = {
    1: "timestamp_milliseconds",
    2: "open_price",
    3: "high_price",
    4: "low_price",
    5: "close_price",
    6: "volume_traded",
    7: "traded_value",
    8: "total_buy_quantity",
    9: "total_sell_quantity",
    10: "average_traded_price",
    11: "high_price_range",
    12: "low_price_range",
    13: "last_price",
    14: "open_interest",
    15: "low_trade_range",
    16: "high_trade_range",
}

LIVE_INDICES_FIELD_NAMES = {
    1: "timestamp_milliseconds",
    2: "last_price",
}

PRICE_FIELDS = (
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "traded_value",
    "average_traded_price",
    "high_price_range",
    "low_price_range",
    "last_price",
    "low_trade_range",
    "high_trade_range",
)

QUANTITY_FIELDS = (
    "volume_traded",
    "total_buy_quantity",
    "total_sell_quantity",
    "open_interest",
)

EXCHANGE_NAMES = {
    0: "BSE",
    1: "NSE",
    2: "MCX",
    3: "MCXSX",
    4: "NCDEX",
    5: "GLOBAL",
    6: "US",
}

SEGMENT_NAMES = {
    0: "CASH",
    1: "FNO",
    2: "CURRENCY",
    3: "COMMODITY",
}

TICK_MODE_PRICE_DETAILED = "price_detailed"
TICK_MODE_INDEX_VALUE = "index_value"

PRICE_DIVISOR = 10000

MESSAGE_OPERATION = b"MSG"

LINE_TERMINATOR = b"\r\n"

MILLISECONDS_PER_SECOND = 1000.0

MAXIMUM_PLAUSIBLE_EPOCH_MILLISECONDS = 4102444800000


def read_varint(data, offset):
    """
    Read one variable length integer.

    Args:
        data (bytes): The buffer to read from.
        offset (int): Byte offset of the first byte of the integer.

    Returns:
        tuple: A (value, offset) pair, where value is None when the buffer ends before the integer does, and offset is the byte after it.
    """
    value = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        offset = offset + 1
        value = value | ((byte & 0x7F) << shift)
        if not byte & 0x80:
            return (value, offset)
        shift = shift + 7
        if shift > 63:
            return (None, offset)
    return (None, offset)


def read_double(data, offset):
    """
    Read one eight byte IEEE 754 double.

    Args:
        data (bytes): The buffer to read from.
        offset (int): Byte offset of the first of the eight bytes.

    Returns:
        float | None: The value, or None when fewer than eight bytes remain.
    """
    if offset + 8 > len(data):
        return None
    return DOUBLE_STRUCT.unpack_from(data, offset)[0]


def skip_field(data, offset, wire_type):
    """
    Step over a field this decoder does not read.

    Skipping by wire type rather than by field number means a field added to the schema later is stepped over rather than misread. The market depth arm of the response is skipped this way, because five level depth is not carried on this branch.

    Args:
        data (bytes): The buffer to read from.
        offset (int): Byte offset of the field's payload.
        wire_type (int): The field's wire type from its tag.

    Returns:
        int | None: The byte after the field, or None when the buffer ends first or the wire type is not one this decoder knows.
    """
    if wire_type == WIRE_TYPE_VARINT:
        value, offset = read_varint(data, offset)
        if value is None:
            return None
        return offset
    if wire_type == WIRE_TYPE_SIXTY_FOUR_BIT:
        if offset + 8 > len(data):
            return None
        return offset + 8
    if wire_type == WIRE_TYPE_THIRTY_TWO_BIT:
        if offset + 4 > len(data):
            return None
        return offset + 4
    if wire_type == WIRE_TYPE_LENGTH_DELIMITED:
        length, offset = read_varint(data, offset)
        if length is None or offset + length > len(data):
            return None
        return offset + length
    return None


def read_length_delimited(data, offset):
    """
    Read one length delimited field's payload.

    Args:
        data (bytes): The buffer to read from.
        offset (int): Byte offset of the field's length.

    Returns:
        tuple: A (payload, offset) pair, where payload is None when the buffer ends before the field does.
    """
    length, offset = read_varint(data, offset)
    if length is None or offset + length > len(data):
        return (None, len(data))
    return (data[offset:offset + length], offset + length)


def iterate_fields(data):
    """
    Yield every field in one encoded message, in the order it appears.

    Args:
        data (bytes): One encoded message.

    Yields:
        tuple: A (field_number, wire_type, value) triple per field, where value is the varint for a varint field, the payload bytes for a length delimited one, the float for a sixty four bit one, and None for a thirty two bit one, which this schema does not use. Iteration stops rather than raising when the buffer ends mid-field, because this runs inside the socket read loop.
    """
    offset = 0
    while offset < len(data):
        tag, offset = read_varint(data, offset)
        if tag is None:
            return
        field_number = tag >> 3
        wire_type = tag & 0x07

        if wire_type == WIRE_TYPE_VARINT:
            value, offset = read_varint(data, offset)
            if value is None:
                return
            yield (field_number, wire_type, value)
        elif wire_type == WIRE_TYPE_LENGTH_DELIMITED:
            payload, offset = read_length_delimited(data, offset)
            if payload is None:
                return
            yield (field_number, wire_type, payload)
        elif wire_type == WIRE_TYPE_SIXTY_FOUR_BIT:
            value = read_double(data, offset)
            if value is None:
                return
            offset = offset + 8
            yield (field_number, wire_type, value)
        else:
            next_offset = skip_field(data, offset, wire_type)
            if next_offset is None:
                return
            yield (field_number, wire_type, None)
            offset = next_offset


def scaled_price(value):
    """
    Turn a price in rupees into the integer the tick table stores.

    Groww is the only broker here that sends prices as floating point rupees rather than as integer paise. The tick table stores raw integers alongside a per-row divisor, so the value is multiplied by the divisor and rounded. Ten thousand is used rather than a hundred so that the four decimal places a currency instrument quotes in survive.

    Args:
        value (float | None): The price as it arrived, in rupees.

    Returns:
        int | None: The scaled integer, or None when the message did not carry the field.
    """
    if value is None:
        return None
    return round(value * PRICE_DIVISOR)


def rounded_quantity(value):
    """
    Turn a quantity into an integer.

    Volume, open interest and the two touchline quantities are counts, but Groww sends them as doubles like everything else. They are rounded rather than scaled, because a count has no divisor.

    Args:
        value (float | None): The quantity as it arrived.

    Returns:
        int | None: The rounded integer, or None when the message did not carry the field.
    """
    if value is None:
        return None
    return round(value)


def epoch_milliseconds_to_datetime(epoch_milliseconds):
    """
    Turn an exchange timestamp into a datetime, rejecting the implausible ones.

    Args:
        epoch_milliseconds (float | None): Milliseconds since the Unix epoch as they arrived on the wire.

    Returns:
        datetime.datetime | None: The corresponding local time, or None when the value is absent, not positive, or outside the plausible range.
    """
    if epoch_milliseconds is None or epoch_milliseconds <= 0:
        return None
    if epoch_milliseconds >= MAXIMUM_PLAUSIBLE_EPOCH_MILLISECONDS:
        return None
    return datetime.fromtimestamp(epoch_milliseconds / MILLISECONDS_PER_SECOND)


def parse_message_header(frame):
    """
    Split one NATS message operation into its subject and its payload.

    The header is `MSG <subject> <sid> [reply-to] <byte count>` followed by a carriage return and newline, and then exactly that many payload bytes. The declared count is the only safe boundary, because the payload is protobuf and can contain the same two bytes the header line ends with. A reply-to subject is accepted even though this feed never sends one, because ignoring the count and taking the last field is what makes that tolerance free.

    Args:
        frame (bytes): One complete NATS message operation as archived.

    Returns:
        tuple: A (subject, payload) pair, or (None, None) when the frame is not a well formed message operation.
    """
    terminator = frame.find(LINE_TERMINATOR)
    if terminator < 0:
        return (None, None)

    parts = frame[:terminator].split()
    if len(parts) < 4 or parts[0] != MESSAGE_OPERATION:
        return (None, None)

    try:
        payload_length = int(parts[-1])
    except ValueError:
        return (None, None)

    start = terminator + len(LINE_TERMINATOR)
    if payload_length < 0 or start + payload_length > len(frame):
        return (None, None)

    return (parts[1].decode("ascii", errors="ignore"), frame[start:start + payload_length])


def parse_subject(subject):
    """
    Read the instrument's identity out of the subject it arrived on.

    Groww's market data subjects are a fixed path with the exchange token appended after a full stop, for example `/ld/eq/nse/price_detailed.2885` for a cash instrument, `/ld/fo/nse/price_detailed.35001` for a derivative and `/ld/indices/nse/price.26000` for an index. The token is split off from the right, so a feed name containing a full stop would not confuse it.

    Args:
        subject (str | None): The subject from the message header.

    Returns:
        tuple: A (subject_group, exchange, feed_name, exchange_token) tuple, where subject_group is "eq", "fo" or "indices" and exchange is lower case. Every element is None when the subject is not one this feed subscribes to.
    """
    if not subject:
        return (None, None, None, None)

    parts = subject.strip("/").split("/")
    if len(parts) != 4 or parts[0] != "ld":
        return (None, None, None, None)

    if "." not in parts[3]:
        return (None, None, None, None)

    feed_name, exchange_token = parts[3].rsplit(".", 1)
    if not feed_name or not exchange_token:
        return (None, None, None, None)

    return (parts[1], parts[2], feed_name, exchange_token)


def decode_live_price(payload):
    """
    Decode the detailed live price arm of the response.

    Args:
        payload (bytes): The encoded StocksLivePriceProto message.

    Returns:
        dict: The fields the message carried, named as in LIVE_PRICE_FIELD_NAMES, with every field the message omitted set to None.
    """
    values = {name: None for name in LIVE_PRICE_FIELD_NAMES.values()}
    for field_number, wire_type, value in iterate_fields(payload):
        if wire_type != WIRE_TYPE_SIXTY_FOUR_BIT:
            continue
        name = LIVE_PRICE_FIELD_NAMES.get(field_number)
        if name is not None:
            values[name] = value
    return values


def decode_live_indices(payload):
    """
    Decode the index arm of the response.

    An index message is not a shortened price message. It carries only a timestamp and a value, and its value sits in field 2, which in a price message is the day's open. Decoding an index with the price reader would therefore report the index level as an opening price and leave the last price empty, which is why the two arms are read by separate functions and distinguished by the response's field number rather than by length or by content.

    Args:
        payload (bytes): The encoded StocksLiveIndicesProto message.

    Returns:
        dict: The fields the message carried, named as in LIVE_INDICES_FIELD_NAMES, with every field the message omitted set to None.
    """
    values = {name: None for name in LIVE_INDICES_FIELD_NAMES.values()}
    for field_number, wire_type, value in iterate_fields(payload):
        if wire_type != WIRE_TYPE_SIXTY_FOUR_BIT:
            continue
        name = LIVE_INDICES_FIELD_NAMES.get(field_number)
        if name is not None:
            values[name] = value
    return values


def build_tick(values, tradable, tick_mode, symbol, exchange, segment, exchange_token, arrival_time):
    """
    Turn one decoded arm into the tick the rest of the system consumes.

    Args:
        values (dict): The named fields from decode_live_price or decode_live_indices.
        tradable (bool): Whether this instrument can be traded, which is False for an index.
        tick_mode (str): Which arm produced it, TICK_MODE_PRICE_DETAILED or TICK_MODE_INDEX_VALUE.
        symbol (str | None): Groww's own symbol for the instrument, from the payload.
        exchange (str | None): The exchange name, from the payload's enum.
        segment (str | None): The segment name, from the payload's enum.
        exchange_token (str | None): The exchange token, from the subject.
        arrival_time (datetime.datetime | None): The moment the message was read off the socket.

    Returns:
        dict: The tick, with prices scaled to integers and the divisor alongside them.
    """
    tick = {
        "arrival_time": arrival_time,
        "token": exchange_token,
        "symbol": symbol,
        "exchange": exchange,
        "segment": segment,
        "price_divisor": PRICE_DIVISOR,
        "tick_mode": tick_mode,
        "tradable": tradable,
        "exchange_timestamp": epoch_milliseconds_to_datetime(values.get("timestamp_milliseconds")),
    }

    for name in PRICE_FIELDS:
        if name in values:
            tick[name] = scaled_price(values[name])

    for name in QUANTITY_FIELDS:
        if name in values:
            tick[name] = rounded_quantity(values[name])

    return tick


def decode_frame(frame, arrival_time):
    """
    Decode one archived NATS message operation into the ticks it carries.

    A NATS message carries exactly one instrument, so this returns a list of one or of none rather than of many. The list is kept for the same reason every other broker's decoder returns one: the shard that drives the connection does not want to know how many instruments a broker packs into a record.

    Nothing here raises. A frame that is not a message operation, that names a subject this feed did not subscribe to, or that ends mid-message decodes to nothing, because this runs inside the socket read loop and one malformed record must not take down a connection.

    Args:
        frame (bytes): One complete NATS message operation, header line included.
        arrival_time (datetime.datetime | None): The moment the frame was read off the socket.

    Returns:
        list[dict]: One tick, or none at all.
    """
    subject, payload = parse_message_header(frame)
    if payload is None:
        return []

    _, _, _, exchange_token = parse_subject(subject)
    if exchange_token is None:
        return []

    symbol = None
    exchange = None
    segment = None
    live_price = None
    live_indices = None

    for field_number, wire_type, value in iterate_fields(payload):
        if field_number == RESPONSE_SYMBOL_FIELD and wire_type == WIRE_TYPE_LENGTH_DELIMITED:
            symbol = value.decode("utf-8", errors="ignore")
        elif field_number == RESPONSE_SEGMENT_FIELD and wire_type == WIRE_TYPE_VARINT:
            segment = SEGMENT_NAMES.get(value)
        elif field_number == RESPONSE_EXCHANGE_FIELD and wire_type == WIRE_TYPE_VARINT:
            exchange = EXCHANGE_NAMES.get(value)
        elif field_number == RESPONSE_LIVE_PRICE_FIELD and wire_type == WIRE_TYPE_LENGTH_DELIMITED:
            live_price = value
        elif field_number == RESPONSE_LIVE_INDICES_FIELD and wire_type == WIRE_TYPE_LENGTH_DELIMITED:
            live_indices = value

    if live_price is not None:
        return [
            build_tick(
                decode_live_price(live_price),
                True,
                TICK_MODE_PRICE_DETAILED,
                symbol,
                exchange,
                segment,
                exchange_token,
                arrival_time,
            )
        ]

    if live_indices is not None:
        return [
            build_tick(
                decode_live_indices(live_indices),
                False,
                TICK_MODE_INDEX_VALUE,
                symbol,
                exchange,
                segment,
                exchange_token,
                arrival_time,
            )
        ]

    return []


def frame_packet_count(frame):
    """
    Count the instruments one archived record carries, for the archive manifest.

    The archive is broker agnostic and must not interpret broker records itself, so the counting decision lives in each broker's parser and the archive calls the function it is given.

    Args:
        frame (bytes): One complete NATS message operation.

    Returns:
        int: The number of instruments the record carries, which is one for a market data message and zero for anything else.
    """
    return len(decode_frame(frame, None))
