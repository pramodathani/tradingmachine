"""
Decoding of Fyers' tick-by-tick fifty level market depth frames.

This feed is the opposite of the quote feed in every way that matters. Fyers documents it fully, publishes its schema at https://public.fyers.in/tbtproto/1.0.0/msg.proto, and encodes it in Protocol Buffers rather than a private binary layout. What it does not do is carry many instruments: five per connection and three connections, so fifteen at a time, which makes it a watched-symbol feature rather than a way to cover the universe. It sits beside the quote feed here the way Dhan's two hundred level depth socket sits beside its live feed.

The messages are decoded by hand rather than by generated code. The schema uses only two of the six protobuf wire types, every scalar is wrapped in a standard wrapper message whose single field is the value, and the whole of what this project needs is four message types. A varint reader and a tag loop cover it in less code than a generated module's import machinery, it adds no dependency, and it keeps this module testable on bytes alone exactly like every other decoder here.

Fyers sends a snapshot for a new subscription and differences afterwards, and says so in each message rather than leaving it to be inferred. A difference carries only the levels that moved, so `DepthAssembler` holds the last full book per instrument and applies changes to it. Unlike the quote feed, every message here names its instrument, so a difference is at least self-identifying.
"""

from datetime import datetime

WIRE_TYPE_VARINT = 0
WIRE_TYPE_SIXTY_FOUR_BIT = 1
WIRE_TYPE_LENGTH_DELIMITED = 2
WIRE_TYPE_THIRTY_TWO_BIT = 5

SOCKET_MESSAGE_TYPE_FIELD = 1
SOCKET_MESSAGE_FEEDS_FIELD = 2
SOCKET_MESSAGE_SNAPSHOT_FIELD = 3
SOCKET_MESSAGE_TEXT_FIELD = 4
SOCKET_MESSAGE_ERROR_FIELD = 5

MAP_ENTRY_KEY_FIELD = 1
MAP_ENTRY_VALUE_FIELD = 2

MARKET_FEED_DEPTH_FIELD = 5
MARKET_FEED_FEED_TIME_FIELD = 6
MARKET_FEED_SEND_TIME_FIELD = 7
MARKET_FEED_TOKEN_FIELD = 8
MARKET_FEED_SEQUENCE_NUMBER_FIELD = 9
MARKET_FEED_SNAPSHOT_FIELD = 10
MARKET_FEED_TICKER_FIELD = 11

DEPTH_TOTAL_BUY_QUANTITY_FIELD = 1
DEPTH_TOTAL_SELL_QUANTITY_FIELD = 2
DEPTH_ASKS_FIELD = 3
DEPTH_BIDS_FIELD = 4

MARKET_LEVEL_PRICE_FIELD = 1
MARKET_LEVEL_QUANTITY_FIELD = 2
MARKET_LEVEL_ORDERS_FIELD = 3
MARKET_LEVEL_NUMBER_FIELD = 4

WRAPPER_VALUE_FIELD = 1

MESSAGE_TYPE_DEPTH = 6
MESSAGE_TYPE_RESPONSE = 8

DEPTH_LEVELS = 50

SIGNED_SIXTY_FOUR_BIT_LIMIT = 1 << 63
UNSIGNED_SIXTY_FOUR_BIT_MASK = (1 << 64) - 1

MAXIMUM_PLAUSIBLE_EPOCH_SECONDS = 4102444800

PRICE_DIVISOR = 100

CONTRACT_FIELDS = (
    "exchange_timestamp",
    "send_timestamp",
    "sequence_number",
    "total_buy_quantity",
    "total_sell_quantity",
    "bid_prices",
    "bid_quantities",
    "bid_orders",
    "ask_prices",
    "ask_quantities",
    "ask_orders",
)


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


def signed_value(value):
    """
    Reinterpret an unsigned varint as the signed integer it encodes.

    Protocol Buffers writes a negative int64 as its two's complement in ten bytes rather than zigzag encoding it, so a negative price reads as an enormous positive number unless it is converted back. This schema uses Int64Value for prices, so this matters here even though prices are not expected to be negative.

    Args:
        value (int): The value as read by read_varint.

    Returns:
        int: The signed integer.
    """
    if value >= SIGNED_SIXTY_FOUR_BIT_LIMIT:
        return value - (UNSIGNED_SIXTY_FOUR_BIT_MASK + 1)
    return value


def skip_field(data, offset, wire_type):
    """
    Step over a field this decoder does not read.

    The schema carries quote, extended quote, daily quote, candle and symbol detail messages that the depth subscription does not need, and skipping them by wire type rather than by field number means a field added to the schema later is stepped over rather than misread.

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
        tuple: A (field_number, wire_type, value, offset) tuple per field, where value is the varint for a varint field and the payload bytes for a length delimited one, and None for the fixed width types this schema does not use. Iteration stops rather than raising when the buffer ends mid-field, because this runs inside the socket read loop.
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
            yield (field_number, wire_type, value, offset)
        elif wire_type == WIRE_TYPE_LENGTH_DELIMITED:
            payload, offset = read_length_delimited(data, offset)
            if payload is None:
                return
            yield (field_number, wire_type, payload, offset)
        else:
            next_offset = skip_field(data, offset, wire_type)
            if next_offset is None:
                return
            yield (field_number, wire_type, None, next_offset)
            offset = next_offset


def read_wrapper_value(payload, signed=False):
    """
    Read the value out of one of the standard wrapper messages.

    Every scalar in this schema is wrapped, so that a field the server did not set is absent rather than zero. A wrapper is a message carrying the value in field 1, and a wrapper that is present but empty means the value really is zero.

    Args:
        payload (bytes): The encoded wrapper message.
        signed (bool): Whether to reinterpret the value as a signed integer.

    Returns:
        int: The wrapped value, which is zero for a present but empty wrapper.
    """
    value = 0
    for field_number, wire_type, field_value, _ in iterate_fields(payload):
        if field_number == WRAPPER_VALUE_FIELD and wire_type == WIRE_TYPE_VARINT:
            value = field_value
    if signed:
        return signed_value(value)
    return value


def epoch_seconds_to_datetime(epoch_seconds):
    """
    Turn an exchange timestamp into a datetime, rejecting the implausible ones.

    Args:
        epoch_seconds (int | None): Seconds since the Unix epoch as they arrived on the wire.

    Returns:
        datetime.datetime | None: The corresponding local time, or None when the value is absent, zero, or outside the plausible range.
    """
    if epoch_seconds is None or epoch_seconds <= 0:
        return None
    if epoch_seconds >= MAXIMUM_PLAUSIBLE_EPOCH_SECONDS:
        return None
    return datetime.fromtimestamp(epoch_seconds)


def decode_market_level(payload):
    """
    Decode one price level of one side of the book.

    Args:
        payload (bytes): The encoded MarketLevel message.

    Returns:
        dict: The level, with keys "price", "quantity", "orders" and "number". The number is the level's position in the book, zero based, and is what a difference message uses to say which level it is changing.
    """
    level = {
        "price": None,
        "quantity": None,
        "orders": None,
        "number": None,
    }
    for field_number, wire_type, value, _ in iterate_fields(payload):
        if wire_type != WIRE_TYPE_LENGTH_DELIMITED:
            continue
        if field_number == MARKET_LEVEL_PRICE_FIELD:
            level["price"] = read_wrapper_value(value, signed=True)
        elif field_number == MARKET_LEVEL_QUANTITY_FIELD:
            level["quantity"] = read_wrapper_value(value)
        elif field_number == MARKET_LEVEL_ORDERS_FIELD:
            level["orders"] = read_wrapper_value(value)
        elif field_number == MARKET_LEVEL_NUMBER_FIELD:
            level["number"] = read_wrapper_value(value)
    return level


def decode_depth(payload):
    """
    Decode one instrument's book, which may be a full one or only the levels that moved.

    Args:
        payload (bytes): The encoded Depth message.

    Returns:
        dict: The book, with keys "total_buy_quantity", "total_sell_quantity", "bids" and "asks". The two lists hold whatever levels the message carried, which is every level in a snapshot and only the changed ones in a difference.
    """
    depth = {
        "total_buy_quantity": None,
        "total_sell_quantity": None,
        "bids": [],
        "asks": [],
    }
    for field_number, wire_type, value, _ in iterate_fields(payload):
        if wire_type != WIRE_TYPE_LENGTH_DELIMITED:
            continue
        if field_number == DEPTH_TOTAL_BUY_QUANTITY_FIELD:
            depth["total_buy_quantity"] = read_wrapper_value(value)
        elif field_number == DEPTH_TOTAL_SELL_QUANTITY_FIELD:
            depth["total_sell_quantity"] = read_wrapper_value(value)
        elif field_number == DEPTH_ASKS_FIELD:
            depth["asks"].append(decode_market_level(value))
        elif field_number == DEPTH_BIDS_FIELD:
            depth["bids"].append(decode_market_level(value))
    return depth


def decode_market_feed(payload, arrival_time):
    """
    Decode one instrument's feed message into a partial tick.

    The schema's quote, extended quote, daily quote, candle and symbol detail messages are stepped over, because a depth subscription does not populate them and Fyers' own documentation says the other fields can be ignored.

    Args:
        payload (bytes): The encoded MarketFeed message.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        dict: The partial tick, carrying the instrument's identity, its timestamps and whatever levels the message held.
    """
    tick = {
        "arrival_time": arrival_time,
        "token": None,
        "ticker": None,
        "sequence_number": None,
        "is_snapshot": False,
        "exchange_timestamp": None,
        "send_timestamp": None,
        "price_divisor": PRICE_DIVISOR,
        "tick_mode": "depth_fifty",
        "tradable": True,
        "depth": None,
    }

    for field_number, wire_type, value, _ in iterate_fields(payload):
        if field_number == MARKET_FEED_DEPTH_FIELD and wire_type == WIRE_TYPE_LENGTH_DELIMITED:
            tick["depth"] = decode_depth(value)
        elif field_number == MARKET_FEED_FEED_TIME_FIELD and wire_type == WIRE_TYPE_LENGTH_DELIMITED:
            tick["exchange_timestamp"] = epoch_seconds_to_datetime(read_wrapper_value(value))
        elif field_number == MARKET_FEED_SEND_TIME_FIELD and wire_type == WIRE_TYPE_LENGTH_DELIMITED:
            tick["send_timestamp"] = epoch_seconds_to_datetime(read_wrapper_value(value))
        elif field_number == MARKET_FEED_TOKEN_FIELD and wire_type == WIRE_TYPE_LENGTH_DELIMITED:
            tick["token"] = value.decode("utf-8", errors="ignore")
        elif field_number == MARKET_FEED_SEQUENCE_NUMBER_FIELD and wire_type == WIRE_TYPE_VARINT:
            tick["sequence_number"] = value
        elif field_number == MARKET_FEED_SNAPSHOT_FIELD and wire_type == WIRE_TYPE_VARINT:
            tick["is_snapshot"] = bool(value)
        elif field_number == MARKET_FEED_TICKER_FIELD and wire_type == WIRE_TYPE_LENGTH_DELIMITED:
            tick["ticker"] = value.decode("utf-8", errors="ignore")

    return tick


def decode_map_entry(payload, arrival_time):
    """
    Decode one entry of the map from ticker to feed.

    A protobuf map is encoded as a repeated message of key and value, so the ticker appears both here and inside the feed itself. The key wins when the two disagree, because the key is what the server used to address the entry.

    Args:
        payload (bytes): The encoded map entry.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        dict | None: The partial tick, or None when the entry carried no feed.
    """
    key = None
    tick = None
    for field_number, wire_type, value, _ in iterate_fields(payload):
        if wire_type != WIRE_TYPE_LENGTH_DELIMITED:
            continue
        if field_number == MAP_ENTRY_KEY_FIELD:
            key = value.decode("utf-8", errors="ignore")
        elif field_number == MAP_ENTRY_VALUE_FIELD:
            tick = decode_market_feed(value, arrival_time)

    if tick is None:
        return None
    if key:
        tick["ticker"] = key
    return tick


def decode_frame(frame, arrival_time):
    """
    Decode one websocket frame into the partial ticks it carries.

    A frame carrying an error decodes to nothing, because its feeds map is empty by definition and the connection driver reads the error text for itself.

    Nothing here raises. A frame that ends mid-message yields the entries read so far, for the same reason the other decoders in this project do not raise: this runs inside the socket read loop and one malformed frame must not take down a connection.

    Args:
        frame (bytes): One complete websocket frame as received.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        list[dict]: One partial tick per instrument the frame carried.
    """
    ticks = []
    is_error = False

    for field_number, wire_type, value, _ in iterate_fields(frame):
        if field_number == SOCKET_MESSAGE_ERROR_FIELD and wire_type == WIRE_TYPE_VARINT:
            is_error = bool(value)
        elif field_number == SOCKET_MESSAGE_FEEDS_FIELD and wire_type == WIRE_TYPE_LENGTH_DELIMITED:
            tick = decode_map_entry(value, arrival_time)
            if tick is not None:
                ticks.append(tick)

    if is_error:
        return []
    return ticks


def frame_error_text(frame):
    """
    Give the error text a frame carries, when it carries one.

    Args:
        frame (bytes): One complete websocket frame as received.

    Returns:
        str | None: The error message, or None when the frame reports no error.
    """
    is_error = False
    text = None
    for field_number, wire_type, value, _ in iterate_fields(frame):
        if field_number == SOCKET_MESSAGE_ERROR_FIELD and wire_type == WIRE_TYPE_VARINT:
            is_error = bool(value)
        elif field_number == SOCKET_MESSAGE_TEXT_FIELD and wire_type == WIRE_TYPE_LENGTH_DELIMITED:
            text = value.decode("utf-8", errors="ignore")
    if not is_error:
        return None
    return text


def frame_packet_count(frame):
    """
    Count the instruments one websocket frame carries, for the archive manifest.

    The archive is broker agnostic and must not interpret broker frames itself, so the counting decision lives in each broker's parser and the archive calls the function it is given. A frame reporting an error carries no instruments, so the error replies never inflate the manifest's reconciliation.

    Args:
        frame (bytes): One complete websocket frame as received.

    Returns:
        int: The number of instruments the frame carries.
    """
    return len(decode_frame(frame, None))


class DepthAssembler:
    """
    Merges snapshots and differences into complete fifty level books, one instrument at a time.

    Fyers sends the full book once when a subscription starts and only the levels that moved afterwards, so no single difference message describes an instrument. This holds the last full book per ticker and applies each difference to it.

    Unlike the quote feed's assembler, this one needs no topic table, because every message on this socket names its instrument. It still belongs to one connection, because a book half built from one session and half from another would be neither.

    Attributes:
        books_by_ticker (dict): The last known book for every instrument seen, keyed on ticker.
    """

    def __init__(self):
        """
        Start with no instrument state at all.

        Returns:
            None.
        """
        self.books_by_ticker = {}

    def empty_book(self, ticker, token):
        """
        Build the state an instrument starts from before its first snapshot.

        Args:
            ticker (str): The instrument's ticker.
            token (str | None): The instrument's Fyers token, when the message carried one.

        Returns:
            dict: The empty book, with every contract field present and the six level arrays fifty long.
        """
        book = {
            "ticker": ticker,
            "token": token,
            "tick_mode": "depth_fifty",
            "tradable": True,
            "price_divisor": PRICE_DIVISOR,
        }
        for field in CONTRACT_FIELDS:
            book[field] = None
        for side in ("bid", "ask"):
            book[f"{side}_prices"] = [None] * DEPTH_LEVELS
            book[f"{side}_quantities"] = [None] * DEPTH_LEVELS
            book[f"{side}_orders"] = [None] * DEPTH_LEVELS
        return book

    def apply_levels(self, book, levels, side):
        """
        Write one message's levels into one side of a book.

        A level says which position it occupies, so a difference carrying three levels updates those three places and leaves the other forty seven alone. A level whose number is missing or out of range is skipped rather than appended, because appending would lengthen the array and make one instrument's book a different shape from another's.

        Args:
            book (dict): The book to write into.
            levels (list[dict]): The levels the message carried.
            side (str): Which side they belong to, "bid" or "ask".

        Returns:
            None.
        """
        prices = book[f"{side}_prices"]
        quantities = book[f"{side}_quantities"]
        orders = book[f"{side}_orders"]

        for level in levels:
            number = level["number"]
            if number is None or number < 0 or number >= DEPTH_LEVELS:
                continue
            if level["price"] is not None:
                prices[number] = level["price"]
            if level["quantity"] is not None:
                quantities[number] = level["quantity"]
            if level["orders"] is not None:
                orders[number] = level["orders"]

    def merge(self, tick):
        """
        Merge one partial tick into its instrument's book and return the complete book.

        A snapshot clears the book first, because a snapshot describes the whole book and levels left over from before it would be stale rather than merely old. A difference is applied on top of whatever is there, which is the point of holding the state at all.

        Args:
            tick (dict): One partial tick from decode_frame.

        Returns:
            dict | None: The complete book for this instrument, or None when the tick named no instrument.
        """
        ticker = tick.get("ticker")
        if not ticker:
            return None

        if tick.get("is_snapshot") or ticker not in self.books_by_ticker:
            self.books_by_ticker[ticker] = self.empty_book(ticker, tick.get("token"))
        book = self.books_by_ticker[ticker]

        if tick.get("token"):
            book["token"] = tick["token"]
        if tick.get("exchange_timestamp") is not None:
            book["exchange_timestamp"] = tick["exchange_timestamp"]
        if tick.get("send_timestamp") is not None:
            book["send_timestamp"] = tick["send_timestamp"]
        if tick.get("sequence_number") is not None:
            book["sequence_number"] = tick["sequence_number"]

        depth = tick.get("depth")
        if depth is not None:
            if depth["total_buy_quantity"] is not None:
                book["total_buy_quantity"] = depth["total_buy_quantity"]
            if depth["total_sell_quantity"] is not None:
                book["total_sell_quantity"] = depth["total_sell_quantity"]
            self.apply_levels(book, depth["bids"], "bid")
            self.apply_levels(book, depth["asks"], "ask")

        complete = dict(book)
        complete["arrival_time"] = tick["arrival_time"]
        for side in ("bid", "ask"):
            complete[f"{side}_prices"] = list(book[f"{side}_prices"])
            complete[f"{side}_quantities"] = list(book[f"{side}_quantities"])
            complete[f"{side}_orders"] = list(book[f"{side}_orders"])
        return complete

    def known_instruments(self):
        """
        List the instruments this assembler has state for.

        Returns:
            list[str]: One ticker per instrument seen so far.
        """
        return list(self.books_by_ticker)
