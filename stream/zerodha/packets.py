"""
Decoding of Zerodha's binary market data frames.

A frame arriving on the websocket carries a two byte count followed by that many packets, each introduced by its own two byte length. Every number is big endian, and every four byte number is unsigned. There is no field anywhere in a packet that says what kind of packet it is: the shape is inferred entirely from its length, which is why the lengths are named constants here and why an unrecognised length is skipped rather than guessed at.

Prices are not converted here. Each packet's prices are left exactly as they arrived on the wire and the divisor needed to turn them into rupees is reported alongside them, because the ticks table stores the raw integers and applies the divisor in a view. The Redis publisher divides when it encodes, so the one decoded dictionary serves both without either having to undo the other's work.

This module knows nothing about instrument identities, shards, Redis or the database. That is deliberate: it is the piece whose correctness matters most and it can be tested completely on bytes alone.
"""

import struct
from datetime import datetime

LTP_PACKET_LENGTH = 8
INDEX_QUOTE_PACKET_LENGTH = 28
INDEX_FULL_PACKET_LENGTH = 32
QUOTE_PACKET_LENGTH = 44
FULL_PACKET_LENGTH = 184

DEPTH_START_OFFSET = 64
DEPTH_ENTRY_LENGTH = 12
DEPTH_LEVELS_PER_SIDE = 5

INDICES_SEGMENT = 9
NSE_CURRENCY_SEGMENT = 3
BSE_CURRENCY_SEGMENT = 6
NSE_COMMODITY_SEGMENT = 12

NSE_CURRENCY_PRICE_DIVISOR = 10000000
BSE_CURRENCY_PRICE_DIVISOR = 10000
NSE_COMMODITY_PRICE_DIVISOR = 10000
DEFAULT_PRICE_DIVISOR = 100

MAXIMUM_PLAUSIBLE_EPOCH_SECONDS = 4102444800

SEGMENT_NAMES = {
    1: "nse",
    2: "nfo",
    3: "cds",
    4: "bse",
    5: "bfo",
    6: "bcd",
    7: "mcx",
    8: "mcxsx",
    9: "indices",
    12: "nco",
}

PACKET_COUNT_STRUCT = struct.Struct(">H")
PACKET_LENGTH_STRUCT = struct.Struct(">H")
UNSIGNED_INTEGER_STRUCT = struct.Struct(">I")
DEPTH_ENTRY_STRUCT = struct.Struct(">IIH2x")


def exchange_segment(instrument_token):
    """
    Work out which exchange segment an instrument token belongs to.

    Zerodha encodes the segment in the low byte of the token, so this needs no lookup of any kind.

    Args:
        instrument_token (int): The Zerodha instrument token.

    Returns:
        int: The segment number, for example 1 for NSE cash or 9 for indices.
    """
    return instrument_token & 0xFF


def segment_name(instrument_token):
    """
    Give the short name of the exchange segment an instrument token belongs to.

    Segments that Zerodha has added since its own client libraries were written are not in the table, the clearest case being segment 12, which is NSE Commodity and covers roughly a quarter of the instruments Zerodha lists. An unknown segment is reported by number rather than treated as an error, because refusing to decode a real instrument would be far worse than naming it awkwardly.

    Args:
        instrument_token (int): The Zerodha instrument token.

    Returns:
        str: The segment name, for example "nse", or a string such as "segment_17" when the segment is not one of the known ones.
    """
    segment = instrument_token & 0xFF
    if segment in SEGMENT_NAMES:
        return SEGMENT_NAMES[segment]
    return f"segment_{segment}"


def price_divisor(instrument_token):
    """
    Give the number that turns this instrument's wire prices into rupees.

    Three segments differ from the ordinary hundred. Zerodha's own written documentation is wrong about the two currency segments, claiming that all currencies divide by ten million and never mentioning BSE currency at all, so those follow its Python and Go client libraries instead, which agree with each other.

    NSE Commodity, segment 12, appears in neither the documentation nor either client library, both of whose segment tables stop at 9. Its divisor of ten thousand was established by comparing decoded ticks against Zerodha's own REST quote endpoint for fourteen instruments, every one of which implied exactly ten thousand. Guessing it from tick sizes gives the wrong answer: they run from one paisa upwards and suggest a hundred, which is out by a factor of a hundred.

    Every remaining segment, known or not, divides by a hundred.

    Args:
        instrument_token (int): The Zerodha instrument token.

    Returns:
        int: The divisor to apply to every price in this instrument's packets, which is 10000000 for NSE currency, 10000 for BSE currency and NSE Commodity, and 100 for everything else.
    """
    segment = instrument_token & 0xFF
    if segment == NSE_CURRENCY_SEGMENT:
        return NSE_CURRENCY_PRICE_DIVISOR
    if segment == BSE_CURRENCY_SEGMENT:
        return BSE_CURRENCY_PRICE_DIVISOR
    if segment == NSE_COMMODITY_SEGMENT:
        return NSE_COMMODITY_PRICE_DIVISOR
    return DEFAULT_PRICE_DIVISOR


def epoch_seconds_to_datetime(epoch_seconds):
    """
    Turn an exchange timestamp into a datetime, rejecting the implausible ones.

    The exchange sends zero when it has no timestamp to give, and occasionally sends a value that is not a time at all. Storing either would put a row in the wrong place, since the ticks table is partitioned by time, so anything outside a sane range becomes no timestamp rather than a wrong one.

    Args:
        epoch_seconds (int): Seconds since the Unix epoch as they arrived on the wire.

    Returns:
        datetime.datetime | None: The corresponding local time, or None when the value is zero or outside the plausible range.
    """
    if epoch_seconds <= 0:
        return None
    if epoch_seconds >= MAXIMUM_PLAUSIBLE_EPOCH_SECONDS:
        return None
    return datetime.fromtimestamp(epoch_seconds)


def decode_ltp_packet(frame, offset, arrival_time):
    """
    Decode an eight byte packet, which carries only the last traded price.

    An index and a tradeable instrument produce identically shaped packets in this mode, so the only thing that distinguishes them is the segment in the token.

    Args:
        frame (bytes): The whole websocket frame the packet sits inside.
        offset (int): Byte offset of the start of the packet within the frame.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        dict: The decoded tick, with prices left as they arrived on the wire.
    """
    instrument_token = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset)[0]
    last_price = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 4)[0]
    segment = instrument_token & 0xFF
    return {
        "arrival_time": arrival_time,
        "instrument_token": instrument_token,
        "exchange_segment": segment,
        "kite_segment": segment_name(instrument_token),
        "price_divisor": price_divisor(instrument_token),
        "tick_mode": "ltp",
        "tradable": segment != INDICES_SEGMENT,
        "exchange_timestamp": None,
        "last_trade_time": None,
        "last_price": last_price,
    }


def decode_index_packet(frame, offset, packet_length, arrival_time):
    """
    Decode a twenty eight or thirty two byte index packet.

    An index packet is not a shortened tradeable packet. After the last traded price it carries high, low, open and close, in that order, whereas a tradeable packet carries open, high, low and close. Nothing in the bytes distinguishes the two orderings, so decoding an index with the tradeable reader silently swaps the day's open with its high and its low with its close. That is why this function shares no code with the tradeable one, even though the two look similar enough to invite it.

    An index has no traded volume, no open interest and no market depth, so those keys are absent rather than present and empty. The four byte field at offset 24 is the exchange's own price change, which is ignored here exactly as Zerodha's own client libraries ignore it, because it is read as unsigned and a falling index would therefore report an enormous positive number.

    Args:
        frame (bytes): The whole websocket frame the packet sits inside.
        offset (int): Byte offset of the start of the packet within the frame.
        packet_length (int): Either 28 for an index quote packet or 32 for an index full packet.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        dict: The decoded tick, with prices left as they arrived on the wire.
    """
    instrument_token = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset)[0]
    last_price = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 4)[0]
    high_price = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 8)[0]
    low_price = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 12)[0]
    open_price = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 16)[0]
    close_price = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 20)[0]

    exchange_timestamp = None
    if packet_length >= INDEX_FULL_PACKET_LENGTH:
        exchange_timestamp = epoch_seconds_to_datetime(UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 28)[0])

    tick_mode = "index_quote"
    if packet_length >= INDEX_FULL_PACKET_LENGTH:
        tick_mode = "index_full"

    return {
        "arrival_time": arrival_time,
        "instrument_token": instrument_token,
        "exchange_segment": instrument_token & 0xFF,
        "kite_segment": segment_name(instrument_token),
        "price_divisor": price_divisor(instrument_token),
        "tick_mode": tick_mode,
        "tradable": False,
        "exchange_timestamp": exchange_timestamp,
        "last_trade_time": None,
        "last_price": last_price,
        "open_price": open_price,
        "high_price": high_price,
        "low_price": low_price,
        "close_price": close_price,
    }


def decode_tradable_packet(frame, offset, packet_length, arrival_time):
    """
    Decode a forty four or one hundred and eighty four byte packet for a tradeable instrument.

    The day's four prices appear here as open, high, low and close, which is a different order from the one an index packet uses. See decode_index_packet for why the two are kept apart.

    A full packet adds the last trade time, open interest and one hundred and twenty bytes of market depth. Each depth entry is a four byte quantity, a four byte price, a two byte order count and two bytes of padding, and the order count really is two bytes: reading it as four shifts every entry after it and produces numbers that still look like plausible order counts, which is what makes the mistake hard to notice.

    Args:
        frame (bytes): The whole websocket frame the packet sits inside.
        offset (int): Byte offset of the start of the packet within the frame.
        packet_length (int): Either 44 for a quote packet or 184 for a full packet.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        dict: The decoded tick, with prices left as they arrived on the wire. Depth keys are present only for a full packet.
    """
    instrument_token = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset)[0]
    last_price = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 4)[0]
    last_traded_quantity = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 8)[0]
    average_traded_price = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 12)[0]
    volume_traded = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 16)[0]
    total_buy_quantity = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 20)[0]
    total_sell_quantity = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 24)[0]
    open_price = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 28)[0]
    high_price = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 32)[0]
    low_price = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 36)[0]
    close_price = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 40)[0]

    tick = {
        "arrival_time": arrival_time,
        "instrument_token": instrument_token,
        "exchange_segment": instrument_token & 0xFF,
        "kite_segment": segment_name(instrument_token),
        "price_divisor": price_divisor(instrument_token),
        "tick_mode": "quote",
        "tradable": True,
        "exchange_timestamp": None,
        "last_trade_time": None,
        "last_price": last_price,
        "last_traded_quantity": last_traded_quantity,
        "average_traded_price": average_traded_price,
        "volume_traded": volume_traded,
        "total_buy_quantity": total_buy_quantity,
        "total_sell_quantity": total_sell_quantity,
        "open_price": open_price,
        "high_price": high_price,
        "low_price": low_price,
        "close_price": close_price,
    }

    if packet_length < FULL_PACKET_LENGTH:
        return tick

    tick["tick_mode"] = "full"
    tick["last_trade_time"] = epoch_seconds_to_datetime(UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 44)[0])
    tick["open_interest"] = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 48)[0]
    tick["open_interest_day_high"] = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 52)[0]
    tick["open_interest_day_low"] = UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 56)[0]
    tick["exchange_timestamp"] = epoch_seconds_to_datetime(UNSIGNED_INTEGER_STRUCT.unpack_from(frame, offset + 60)[0])

    bid_quantities = []
    bid_prices = []
    bid_orders = []
    ask_quantities = []
    ask_prices = []
    ask_orders = []

    depth_offset = offset + DEPTH_START_OFFSET
    for level in range(DEPTH_LEVELS_PER_SIDE):
        quantity, price, orders = DEPTH_ENTRY_STRUCT.unpack_from(frame, depth_offset + level * DEPTH_ENTRY_LENGTH)
        bid_quantities.append(quantity)
        bid_prices.append(price)
        bid_orders.append(orders)

    ask_offset = depth_offset + DEPTH_LEVELS_PER_SIDE * DEPTH_ENTRY_LENGTH
    for level in range(DEPTH_LEVELS_PER_SIDE):
        quantity, price, orders = DEPTH_ENTRY_STRUCT.unpack_from(frame, ask_offset + level * DEPTH_ENTRY_LENGTH)
        ask_quantities.append(quantity)
        ask_prices.append(price)
        ask_orders.append(orders)

    tick["bid_quantities"] = bid_quantities
    tick["bid_prices"] = bid_prices
    tick["bid_orders"] = bid_orders
    tick["ask_quantities"] = ask_quantities
    tick["ask_prices"] = ask_prices
    tick["ask_orders"] = ask_orders
    return tick


def decode_frame(frame, arrival_time):
    """
    Decode every packet in one binary websocket frame.

    A frame shorter than two bytes is the one byte heartbeat Zerodha sends every few seconds when there is nothing to report, and it decodes to nothing at all rather than raising.

    A frame that ends in the middle of a packet stops the loop and the packets read so far are returned. Raising instead would be worse than useless: this runs inside the socket read loop, so one malformed frame would take down a connection carrying several thousand instruments.

    Args:
        frame (bytes): One complete binary websocket frame as received.
        arrival_time (datetime.datetime): The moment the frame was read off the socket, recorded by the caller so that every tick in the frame shares one timestamp.

    Returns:
        list[dict]: One decoded tick per packet, in the order the packets appeared. Packets whose length is not a recognised one are skipped.
    """
    frame_length = len(frame)
    if frame_length < 2:
        return []

    ticks = []
    packet_count = PACKET_COUNT_STRUCT.unpack_from(frame, 0)[0]
    offset = 2

    for packet_number in range(packet_count):
        if offset + 2 > frame_length:
            break
        packet_length = PACKET_LENGTH_STRUCT.unpack_from(frame, offset)[0]
        offset = offset + 2
        if offset + packet_length > frame_length:
            break

        if packet_length == LTP_PACKET_LENGTH:
            ticks.append(decode_ltp_packet(frame, offset, arrival_time))
        elif packet_length == INDEX_QUOTE_PACKET_LENGTH or packet_length == INDEX_FULL_PACKET_LENGTH:
            ticks.append(decode_index_packet(frame, offset, packet_length, arrival_time))
        elif packet_length == QUOTE_PACKET_LENGTH or packet_length == FULL_PACKET_LENGTH:
            ticks.append(decode_tradable_packet(frame, offset, packet_length, arrival_time))

        offset = offset + packet_length

    return ticks
