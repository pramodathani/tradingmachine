"""
Decoding of Dhan's binary live market feed frames.

A frame is one or more packets stacked one after another, each introduced by an eight byte little endian header: one byte response code, a two byte message length, one byte exchange segment, and a four byte security identifier. The response code, not the length, decides how the packet is read, because every response code has a fixed total size and a length field can lie.

Every price on the wire is an IEEE float. The ticks table stores integers with a divisor, so each price is converted to paise here, once, by multiplying by a hundred and rounding. This is the one deliberate difference from the Zerodha decoder, whose wire values are already integers: a float cannot be stored in a BIGINT column untouched, so the conversion has to happen somewhere, and here is the only place anything is interpreted. The raw float bits remain recoverable from the archive, which stores frames verbatim. A float32 carries roughly seven significant decimal digits, so prices are exact to the paisa up to about one lakh and seventy seven thousand rupees, above which the wire itself can no longer represent every paisa; that is a property of what the exchange sends, not of this conversion.

This module knows nothing about instrument identities, shards, Redis or the database, exactly like its Zerodha counterpart. It imports `struct` and `datetime` and nothing else, so it can be tested completely on bytes alone.
"""

import struct
from datetime import datetime

HEADER_LENGTH = 8
INDEX_PACKET_LENGTH = 16
TICKER_PACKET_LENGTH = 16
FIVE_LEVEL_DEPTH_PACKET_LENGTH = 112
QUOTE_PACKET_LENGTH = 50
OI_PACKET_LENGTH = 12
PREV_CLOSE_PACKET_LENGTH = 16
MARKET_STATUS_PACKET_LENGTH = 8
FULL_PACKET_LENGTH = 162
DISCONNECT_PACKET_LENGTH = 10

RESPONSE_CODE_INDEX = 1
RESPONSE_CODE_TICKER = 2
RESPONSE_CODE_FIVE_LEVEL_DEPTH = 3
RESPONSE_CODE_QUOTE = 4
RESPONSE_CODE_OPEN_INTEREST = 5
RESPONSE_CODE_PREV_CLOSE = 6
RESPONSE_CODE_MARKET_STATUS = 7
RESPONSE_CODE_FULL = 8
RESPONSE_CODE_DISCONNECT = 50

PACKET_TOTAL_SIZES = {
    RESPONSE_CODE_INDEX: INDEX_PACKET_LENGTH,
    RESPONSE_CODE_TICKER: TICKER_PACKET_LENGTH,
    RESPONSE_CODE_FIVE_LEVEL_DEPTH: FIVE_LEVEL_DEPTH_PACKET_LENGTH,
    RESPONSE_CODE_QUOTE: QUOTE_PACKET_LENGTH,
    RESPONSE_CODE_OPEN_INTEREST: OI_PACKET_LENGTH,
    RESPONSE_CODE_PREV_CLOSE: PREV_CLOSE_PACKET_LENGTH,
    RESPONSE_CODE_MARKET_STATUS: MARKET_STATUS_PACKET_LENGTH,
    RESPONSE_CODE_FULL: FULL_PACKET_LENGTH,
    RESPONSE_CODE_DISCONNECT: DISCONNECT_PACKET_LENGTH,
}

DEPTH_LEVELS_PER_SIDE = 5
DEPTH_ENTRY_LENGTH = 20

INDICES_SEGMENT = 0

PRICE_DIVISOR = 100
PAISE_PER_RUPEE = 100

MAXIMUM_PLAUSIBLE_EPOCH_SECONDS = 4102444800

SEGMENT_NAMES = {
    0: "idx_i",
    1: "nse_eq",
    2: "nse_fno",
    3: "nse_currency",
    4: "bse_eq",
    5: "mcx_comm",
    7: "bse_currency",
    8: "bse_fno",
}

DISCONNECT_REASONS = {
    805: "connection_limit_exceeded",
    806: "data_api_subscription_missing",
    807: "access_token_expired",
    808: "invalid_client_id",
    809: "authentication_failed",
}

HEADER_STRUCT = struct.Struct("<BHBI")
LTP_TIMESTAMP_PAYLOAD_STRUCT = struct.Struct("<fI")
OPEN_INTEREST_PAYLOAD_STRUCT = struct.Struct("<I")
QUOTE_PAYLOAD_STRUCT = struct.Struct("<fHIfIIIffff")
FULL_PAYLOAD_STRUCT = struct.Struct("<fHIfIIIIIIffff")
DEPTH_ENTRY_STRUCT = struct.Struct("<IIHHff")
DISCONNECT_REASON_STRUCT = struct.Struct("<H")


def segment_name(exchange_segment):
    """
    Give the short name of an exchange segment number.

    The eight segments Dhan documents are all in the table. An unknown segment is reported by number rather than treated as an error, because refusing to decode a real instrument would be far worse than naming it awkwardly.

    Args:
        exchange_segment (int): The segment byte from a packet header.

    Returns:
        str: The segment name, for example "nse_eq", or a string such as "segment_9" when the segment is not one of the known ones.
    """
    if exchange_segment in SEGMENT_NAMES:
        return SEGMENT_NAMES[exchange_segment]
    return f"segment_{exchange_segment}"


def price_divisor(exchange_segment):
    """
    Give the number that turns this instrument's stored prices into rupees.

    Every Dhan segment uses the same divisor, because the decoder converts prices to paise itself and one hundred paise make a rupee. The function exists so that the decoded tick carries the same key as a Zerodha tick, which lets one database writer and one Redis publisher serve both brokers without branching on the broker. If a segment ever turns out to scale differently, the fix belongs in price_in_paise, keyed on the segment, exactly as the Zerodha decoder keys its divisors.

    Args:
        exchange_segment (int): The segment byte from a packet header.

    Returns:
        int: The divisor to apply to this tick's stored prices, which is always 100.
    """
    return PRICE_DIVISOR


def price_in_paise(price):
    """
    Convert a wire price to whole paise, the unit the ticks table stores.

    Args:
        price (float): The price in rupees as it arrived on the wire.

    Returns:
        int: The price in paise, rounded to the nearest paisa.
    """
    return round(price * PAISE_PER_RUPEE)


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


def response_code(frame):
    """
    Give the response code in a frame's first header byte.

    The live feed puts the code first, unlike the depth feed, which puts the message length first. A frame too short to carry a header has no code.

    Args:
        frame (bytes): One binary websocket frame as received.

    Returns:
        int | None: The response code, or None when the frame is shorter than one byte.
    """
    if len(frame) < 1:
        return None
    return frame[0]


def decode_disconnect(frame):
    """
    Decode a disconnect packet into the reason the feed is closing.

    The reason is a two byte code that follows the header. Codes Dhan documents are named; anything else is reported by number, because an unknown reason is still worth recording.

    Args:
        frame (bytes): The whole disconnect packet, header included.

    Returns:
        str | None: The disconnect reason, for example "access_token_expired", or "reason_812" for an undocumented code, or None when the frame is too short to carry one.
    """
    if len(frame) < DISCONNECT_PACKET_LENGTH:
        return None
    reason = DISCONNECT_REASON_STRUCT.unpack_from(frame, HEADER_LENGTH)[0]
    if reason in DISCONNECT_REASONS:
        return DISCONNECT_REASONS[reason]
    return f"reason_{reason}"


def decode_index_packet(frame, offset, arrival_time):
    """
    Decode a sixteen byte index packet, response code 1.

    Dhan names this response code but publishes no layout for it. Sixteen bytes with the ticker's layout, a float price followed by a four byte epoch, is the reading that fits the size, so this module decodes it that way and marks the packet as an index rather than as traded data. The first live run should confirm the layout, and if it disagrees the bytes are in the archive to settle it.

    Args:
        frame (bytes): The whole websocket frame the packet sits inside.
        offset (int): Byte offset of the start of the packet within the frame.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        dict: The decoded tick, with prices converted to paise.
    """
    last_price, last_trade_seconds = LTP_TIMESTAMP_PAYLOAD_STRUCT.unpack_from(frame, offset + HEADER_LENGTH)
    exchange_segment = frame[offset + 3]
    security_id = HEADER_STRUCT.unpack_from(frame, offset)[3]
    return {
        "arrival_time": arrival_time,
        "security_id": security_id,
        "exchange_segment": exchange_segment,
        "dhan_segment": segment_name(exchange_segment),
        "price_divisor": price_divisor(exchange_segment),
        "tick_mode": "index",
        "tradable": False,
        "exchange_timestamp": None,
        "last_trade_time": epoch_seconds_to_datetime(last_trade_seconds),
        "last_price": price_in_paise(last_price),
    }


def decode_ticker_packet(frame, offset, arrival_time):
    """
    Decode a sixteen byte ticker packet, response code 2.

    It carries only the last traded price and the last traded time.

    Args:
        frame (bytes): The whole websocket frame the packet sits inside.
        offset (int): Byte offset of the start of the packet within the frame.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        dict: The decoded tick, with the price converted to paise.
    """
    last_price, last_trade_seconds = LTP_TIMESTAMP_PAYLOAD_STRUCT.unpack_from(frame, offset + HEADER_LENGTH)
    exchange_segment = frame[offset + 3]
    security_id = HEADER_STRUCT.unpack_from(frame, offset)[3]
    return {
        "arrival_time": arrival_time,
        "security_id": security_id,
        "exchange_segment": exchange_segment,
        "dhan_segment": segment_name(exchange_segment),
        "price_divisor": price_divisor(exchange_segment),
        "tick_mode": "ticker",
        "tradable": exchange_segment != INDICES_SEGMENT,
        "exchange_timestamp": None,
        "last_trade_time": epoch_seconds_to_datetime(last_trade_seconds),
        "last_price": price_in_paise(last_price),
    }


def decode_five_level_depth_packet(frame, offset, arrival_time):
    """
    Decode a one hundred and twelve byte packet, response code 3, which carries the last traded price and five market depth levels.

    Dhan's written documentation does not mention this packet; it exists in Dhan's own client library, whose unpack string fixes both its size and its field order. The five depth entries are interleaved: each twenty byte entry holds a bid quantity, an ask quantity, a bid order count, an ask order count, a bid price and an ask price, so level two's ask sits two entries after level one's bid rather than five entries after it.

    Args:
        frame (bytes): The whole websocket frame the packet sits inside.
        offset (int): Byte offset of the start of the packet within the frame.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        dict: The decoded tick, with prices converted to paise.
    """
    exchange_segment = frame[offset + 3]
    security_id = HEADER_STRUCT.unpack_from(frame, offset)[3]
    last_price = struct.unpack_from("<f", frame, offset + HEADER_LENGTH)[0]

    bid_quantities = []
    bid_prices = []
    bid_orders = []
    ask_quantities = []
    ask_prices = []
    ask_orders = []

    depth_offset = offset + HEADER_LENGTH + 4
    for level in range(DEPTH_LEVELS_PER_SIDE):
        bid_quantity, ask_quantity, bid_order_count, ask_order_count, bid_price, ask_price = DEPTH_ENTRY_STRUCT.unpack_from(frame, depth_offset + level * DEPTH_ENTRY_LENGTH)
        bid_quantities.append(bid_quantity)
        bid_prices.append(price_in_paise(bid_price))
        bid_orders.append(bid_order_count)
        ask_quantities.append(ask_quantity)
        ask_prices.append(price_in_paise(ask_price))
        ask_orders.append(ask_order_count)

    return {
        "arrival_time": arrival_time,
        "security_id": security_id,
        "exchange_segment": exchange_segment,
        "dhan_segment": segment_name(exchange_segment),
        "price_divisor": price_divisor(exchange_segment),
        "tick_mode": "depth",
        "tradable": exchange_segment != INDICES_SEGMENT,
        "exchange_timestamp": None,
        "last_trade_time": None,
        "last_price": price_in_paise(last_price),
        "bid_quantities": bid_quantities,
        "bid_prices": bid_prices,
        "bid_orders": bid_orders,
        "ask_quantities": ask_quantities,
        "ask_prices": ask_prices,
        "ask_orders": ask_orders,
    }


def decode_quote_packet(frame, offset, arrival_time):
    """
    Decode a fifty byte quote packet, response code 4.

    The day's four prices appear here in the order open, close, high, low, which is the order both the documentation's byte table and Dhan's own client library agree on. Nothing in the bytes marks which of the four is which, so reading them as open, high, low, close silently puts the close where the high belongs and the low where the close belongs, which is why the synthetic checks build the packet with four distinct prices.

    Args:
        frame (bytes): The whole websocket frame the packet sits inside.
        offset (int): Byte offset of the start of the packet within the frame.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        dict: The decoded tick, with prices converted to paise.
    """
    exchange_segment = frame[offset + 3]
    security_id = HEADER_STRUCT.unpack_from(frame, offset)[3]
    last_price, last_traded_quantity, last_trade_seconds, average_traded_price, volume_traded, total_sell_quantity, total_buy_quantity, open_price, close_price, high_price, low_price = QUOTE_PAYLOAD_STRUCT.unpack_from(frame, offset + HEADER_LENGTH)
    return {
        "arrival_time": arrival_time,
        "security_id": security_id,
        "exchange_segment": exchange_segment,
        "dhan_segment": segment_name(exchange_segment),
        "price_divisor": price_divisor(exchange_segment),
        "tick_mode": "quote",
        "tradable": exchange_segment != INDICES_SEGMENT,
        "exchange_timestamp": None,
        "last_trade_time": epoch_seconds_to_datetime(last_trade_seconds),
        "last_price": price_in_paise(last_price),
        "last_traded_quantity": last_traded_quantity,
        "average_traded_price": price_in_paise(average_traded_price),
        "volume_traded": volume_traded,
        "total_sell_quantity": total_sell_quantity,
        "total_buy_quantity": total_buy_quantity,
        "open_price": price_in_paise(open_price),
        "high_price": price_in_paise(high_price),
        "low_price": price_in_paise(low_price),
        "close_price": price_in_paise(close_price),
    }


def decode_open_interest_packet(frame, offset, arrival_time):
    """
    Decode a twelve byte open interest packet, response code 5.

    It carries nothing but a four byte open interest figure, and the feed sends it alongside quote subscriptions for instruments that have one.

    Args:
        frame (bytes): The whole websocket frame the packet sits inside.
        offset (int): Byte offset of the start of the packet within the frame.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        dict: The decoded tick, whose only value is the open interest.
    """
    exchange_segment = frame[offset + 3]
    security_id = HEADER_STRUCT.unpack_from(frame, offset)[3]
    open_interest = OPEN_INTEREST_PAYLOAD_STRUCT.unpack_from(frame, offset + HEADER_LENGTH)[0]
    return {
        "arrival_time": arrival_time,
        "security_id": security_id,
        "exchange_segment": exchange_segment,
        "dhan_segment": segment_name(exchange_segment),
        "price_divisor": price_divisor(exchange_segment),
        "tick_mode": "oi",
        "tradable": exchange_segment != INDICES_SEGMENT,
        "exchange_timestamp": None,
        "last_trade_time": None,
        "last_price": None,
        "open_interest": open_interest,
    }


def decode_prev_close_packet(frame, offset, arrival_time):
    """
    Decode a sixteen byte previous close packet, response code 6.

    The feed sends one for every subscribed instrument whenever a subscription is accepted, which is what makes it a completeness signal for the capacity probe outside market hours as well as yesterday's close price. The open interest it carries is the previous day's.

    Args:
        frame (bytes): The whole websocket frame the packet sits inside.
        offset (int): Byte offset of the start of the packet within the frame.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        dict: The decoded tick, with the previous close converted to paise.
    """
    exchange_segment = frame[offset + 3]
    security_id = HEADER_STRUCT.unpack_from(frame, offset)[3]
    previous_close, previous_open_interest = LTP_TIMESTAMP_PAYLOAD_STRUCT.unpack_from(frame, offset + HEADER_LENGTH)
    return {
        "arrival_time": arrival_time,
        "security_id": security_id,
        "exchange_segment": exchange_segment,
        "dhan_segment": segment_name(exchange_segment),
        "price_divisor": price_divisor(exchange_segment),
        "tick_mode": "prev_close",
        "tradable": exchange_segment != INDICES_SEGMENT,
        "exchange_timestamp": None,
        "last_trade_time": None,
        "last_price": None,
        "close_price": price_in_paise(previous_close),
        "open_interest": previous_open_interest,
    }


def decode_full_packet(frame, offset, arrival_time):
    """
    Decode a one hundred and sixty two byte full packet, response code 8.

    The three open interest fields sit between the buy and sell quantities and the day's prices, so a full packet read with the quote reader puts the open interest where the open belongs. The day's prices are open, close, high, low, as in the quote packet. After them come five interleaved twenty byte depth entries of the shape decode_five_level_depth_packet describes.

    Args:
        frame (bytes): The whole websocket frame the packet sits inside.
        offset (int): Byte offset of the start of the packet within the frame.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        dict: The decoded tick, with prices converted to paise and five depth levels a side.
    """
    exchange_segment = frame[offset + 3]
    security_id = HEADER_STRUCT.unpack_from(frame, offset)[3]
    last_price, last_traded_quantity, last_trade_seconds, average_traded_price, volume_traded, total_sell_quantity, total_buy_quantity, open_interest, open_interest_day_high, open_interest_day_low, open_price, close_price, high_price, low_price = FULL_PAYLOAD_STRUCT.unpack_from(frame, offset + HEADER_LENGTH)

    bid_quantities = []
    bid_prices = []
    bid_orders = []
    ask_quantities = []
    ask_prices = []
    ask_orders = []

    depth_offset = offset + HEADER_LENGTH + FULL_PAYLOAD_STRUCT.size
    for level in range(DEPTH_LEVELS_PER_SIDE):
        bid_quantity, ask_quantity, bid_order_count, ask_order_count, bid_price, ask_price = DEPTH_ENTRY_STRUCT.unpack_from(frame, depth_offset + level * DEPTH_ENTRY_LENGTH)
        bid_quantities.append(bid_quantity)
        bid_prices.append(price_in_paise(bid_price))
        bid_orders.append(bid_order_count)
        ask_quantities.append(ask_quantity)
        ask_prices.append(price_in_paise(ask_price))
        ask_orders.append(ask_order_count)

    return {
        "arrival_time": arrival_time,
        "security_id": security_id,
        "exchange_segment": exchange_segment,
        "dhan_segment": segment_name(exchange_segment),
        "price_divisor": price_divisor(exchange_segment),
        "tick_mode": "full",
        "tradable": exchange_segment != INDICES_SEGMENT,
        "exchange_timestamp": None,
        "last_trade_time": epoch_seconds_to_datetime(last_trade_seconds),
        "last_price": price_in_paise(last_price),
        "last_traded_quantity": last_traded_quantity,
        "average_traded_price": price_in_paise(average_traded_price),
        "volume_traded": volume_traded,
        "total_sell_quantity": total_sell_quantity,
        "total_buy_quantity": total_buy_quantity,
        "open_interest": open_interest,
        "open_interest_day_high": open_interest_day_high,
        "open_interest_day_low": open_interest_day_low,
        "open_price": price_in_paise(open_price),
        "high_price": price_in_paise(high_price),
        "low_price": price_in_paise(low_price),
        "close_price": price_in_paise(close_price),
        "bid_quantities": bid_quantities,
        "bid_prices": bid_prices,
        "bid_orders": bid_orders,
        "ask_quantities": ask_quantities,
        "ask_prices": ask_prices,
        "ask_orders": ask_orders,
    }


DECODERS_BY_RESPONSE_CODE = {
    RESPONSE_CODE_INDEX: decode_index_packet,
    RESPONSE_CODE_TICKER: decode_ticker_packet,
    RESPONSE_CODE_FIVE_LEVEL_DEPTH: decode_five_level_depth_packet,
    RESPONSE_CODE_QUOTE: decode_quote_packet,
    RESPONSE_CODE_OPEN_INTEREST: decode_open_interest_packet,
    RESPONSE_CODE_PREV_CLOSE: decode_prev_close_packet,
    RESPONSE_CODE_FULL: decode_full_packet,
}


def frame_packet_count(frame):
    """
    Count the packets one websocket frame carries, for the archive manifest.

    The archive is broker agnostic and must not interpret broker frames itself, so the counting decision lives in each broker's parser and the archive calls it. An unknown response code with a plausible message length counts as a packet, since the manifest counts frames' claims rather than deciding what they contain.

    Args:
        frame (bytes): One binary websocket frame as received.

    Returns:
        int: The number of packets the frame carries, which is zero for a frame too short to hold a header.
    """
    frame_length = len(frame)
    if frame_length < HEADER_LENGTH:
        return 0

    packets = 0
    offset = 0
    while offset + HEADER_LENGTH <= frame_length:
        response_code_value, message_length = HEADER_STRUCT.unpack_from(frame, offset)[:2]
        total_length = PACKET_TOTAL_SIZES.get(response_code_value)
        if total_length is None:
            if message_length < HEADER_LENGTH or offset + message_length > frame_length:
                break
            offset = offset + message_length
            packets = packets + 1
            continue
        if offset + total_length > frame_length:
            break
        packets = packets + 1
        offset = offset + total_length
    return packets


def decode_frame(frame, arrival_time):
    """
    Decode every packet in one binary websocket frame.

    Dispatch is by response code, never by the header's message length, because each response code has a fixed total size and a corrupted length field would otherwise drive the walk off the end of the frame. The length field's coverage, whether it counts the header or only the payload, is unverified against live bytes; it is used only to skip an unrecognised code, and the synthetic checks pin the convention chosen here, that it counts the whole packet.

    A frame shorter than a header decodes to nothing at all rather than raising. A frame that ends in the middle of a packet stops the loop and the packets read so far are returned. Raising instead would be worse than useless: this runs inside the socket read loop, so one malformed frame would take down a connection carrying thousands of instruments.

    Args:
        frame (bytes): One complete binary websocket frame as received.
        arrival_time (datetime.datetime): The moment the frame was read off the socket, recorded by the caller so that every tick in the frame shares one timestamp.

    Returns:
        list[dict]: One decoded tick per data packet, in the order the packets appeared. Market status packets carry no tick and disconnect packets are decoded by decode_disconnect, so neither appears here.
    """
    frame_length = len(frame)
    if frame_length < HEADER_LENGTH:
        return []

    ticks = []
    offset = 0
    while offset + HEADER_LENGTH <= frame_length:
        code = frame[offset]
        total_length = PACKET_TOTAL_SIZES.get(code)
        if total_length is None:
            message_length = HEADER_STRUCT.unpack_from(frame, offset)[1]
            if message_length < HEADER_LENGTH or offset + message_length > frame_length:
                break
            offset = offset + message_length
            continue
        if offset + total_length > frame_length:
            break

        if code in DECODERS_BY_RESPONSE_CODE:
            ticks.append(DECODERS_BY_RESPONSE_CODE[code](frame, offset, arrival_time))
        offset = offset + total_length

    return ticks