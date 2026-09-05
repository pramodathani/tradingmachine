"""
Decoding of Dhan's full market depth frames, for the twenty level and two hundred level depth sockets.

A depth frame is one or more sections stacked one after another, each introduced by a twelve byte little endian header whose first field is a two byte message length, followed by one byte response code, one byte exchange segment, a four byte security identifier, and a four byte field that is a sequence number on the twenty level socket and a row count on the two hundred level socket. A section holds one side of one instrument's book, bids under response code 41 and asks under response code 51, and a single frame may carry one instrument's bids followed by its asks, or several instruments in subscription order.

Every depth entry is sixteen bytes: a float64 price, an unsigned four byte quantity and an unsigned four byte order count. The float64 price is exact for any realistic price, so converting it to paise loses nothing, exactly as the live feed decoder's float32 conversion does not.

This module imports `struct` and nothing else, and deliberately shares no code with the live feed's packets module: the two feeds are different wire formats with differently ordered headers, and a shared helper that papers over that would be one argument away from reading one header with the other's offsets. The segment name and disconnect reason tables are duplicated here, and a synthetic check pins the two tables to the same numbers so they cannot drift apart silently.
"""

import struct

HEADER_LENGTH = 12
DEPTH_ENTRY_LENGTH = 16

BID_RESPONSE_CODE = 41
ASK_RESPONSE_CODE = 51
DISCONNECT_RESPONSE_CODE = 50

TWENTY_DEPTH_LEVELS = 20
MAXIMUM_DEPTH_ROWS = 200

PRICE_DIVISOR = 100
PAISE_PER_RUPEE = 100

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

DEPTH_HEADER_STRUCT = struct.Struct("<hBBiI")
DEPTH_ENTRY_STRUCT = struct.Struct("<dII")
DISCONNECT_REASON_STRUCT = struct.Struct("<H")


def segment_name(exchange_segment):
    """
    Give the short name of an exchange segment number.

    This table is a duplicate of the live feed decoder's, pinned to it by a synthetic check, because the two decoders are standalone by design.

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

    Depth prices are converted to paise by this module's decoder, so the divisor is always one hundred, exactly as in the live feed decoder.

    Args:
        exchange_segment (int): The segment byte from a packet header.

    Returns:
        int: The divisor to apply to this tick's stored prices, which is always 100.
    """
    return PRICE_DIVISOR


def price_in_paise(price):
    """
    Convert a depth price to whole paise, the unit the ticks table stores.

    Args:
        price (float): The price in rupees as it arrived on the wire.

    Returns:
        int: The price in paise, rounded to the nearest paisa.
    """
    return round(price * PAISE_PER_RUPEE)


def decode_disconnect(frame):
    """
    Decode a depth disconnect packet into the reason the feed is closing.

    A depth disconnect is a twelve byte header carrying response code 50, followed by a two byte reason code. The live feed's disconnect is a ten byte packet built on an eight byte header, so the reason sits at a different offset here.

    Args:
        frame (bytes): The whole disconnect packet, header included.

    Returns:
        str | None: The disconnect reason, for example "access_token_expired", or "reason_812" for an undocumented code, or None when the frame is too short to carry one.
    """
    if len(frame) < HEADER_LENGTH + DISCONNECT_REASON_STRUCT.size:
        return None
    reason = DISCONNECT_REASON_STRUCT.unpack_from(frame, HEADER_LENGTH)[0]
    if reason in DISCONNECT_REASONS:
        return DISCONNECT_REASONS[reason]
    return f"reason_{reason}"


def depth_rows(sequence_or_rows, depth_level):
    """
    Work out how many depth rows a section carries.

    On the twenty level socket the header's last field is a sequence number that means nothing to us, and the row count comes from the subscription's depth level, since a twenty level book is always twenty rows. On the two hundred level socket the last field is the number of rows that follow, capped at two hundred because that is the socket's maximum.

    Args:
        sequence_or_rows (int): The header's last four byte field.
        depth_level (int): The depth level the connection subscribed to, 20 or 200.

    Returns:
        int: The number of sixteen byte entries that follow the section's header.
    """
    if depth_level == TWENTY_DEPTH_LEVELS:
        return TWENTY_DEPTH_LEVELS
    return min(max(sequence_or_rows, 0), MAXIMUM_DEPTH_ROWS)


def decode_depth_section(frame, offset, depth_level, arrival_time):
    """
    Decode one bid or ask section of a depth frame, starting at its twelve byte header.

    Args:
        frame (bytes): One complete binary websocket frame as received.
        offset (int): Byte offset of the section header within the frame.
        depth_level (int): The depth level the connection subscribed to, 20 or 200.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        tuple: A (tick, next_offset) pair, where tick is the decoded depth tick, or None when the frame does not hold the whole section, and next_offset is where the next section starts.
    """
    _, code, exchange_segment, security_id, sequence_or_rows = DEPTH_HEADER_STRUCT.unpack_from(frame, offset)

    rows = depth_rows(sequence_or_rows, depth_level)
    packet_length = HEADER_LENGTH + rows * DEPTH_ENTRY_LENGTH
    if offset + packet_length > len(frame):
        return (None, offset)

    prices = []
    quantities = []
    orders = []
    entry_offset = offset + HEADER_LENGTH
    for row in range(rows):
        price, quantity, order_count = DEPTH_ENTRY_STRUCT.unpack_from(frame, entry_offset)
        prices.append(price_in_paise(price))
        quantities.append(quantity)
        orders.append(order_count)
        entry_offset = entry_offset + DEPTH_ENTRY_LENGTH

    if code == BID_RESPONSE_CODE:
        side = "bid"
    else:
        side = "ask"

    if depth_level == TWENTY_DEPTH_LEVELS:
        tick_mode = "depth_twenty"
    else:
        tick_mode = "depth_two_hundred"

    tick = {
        "arrival_time": arrival_time,
        "security_id": security_id,
        "exchange_segment": exchange_segment,
        "dhan_segment": segment_name(exchange_segment),
        "price_divisor": price_divisor(exchange_segment),
        "tick_mode": tick_mode,
        "side": side,
    }
    if side == "bid":
        tick["bid_prices"] = prices
        tick["bid_quantities"] = quantities
        tick["bid_orders"] = orders
    else:
        tick["ask_prices"] = prices
        tick["ask_quantities"] = quantities
        tick["ask_orders"] = orders
    return (tick, offset + packet_length)


def frame_packet_count(frame, depth_level):
    """
    Count the bid and ask sections one depth frame carries, for the archive manifest.

    The archive is broker agnostic and must not interpret broker frames itself, so the counting decision lives in each broker's parser. A depth connection supplies this function partially applied to its own depth level, since the row count of a twenty level section cannot be read from the frame alone.

    Args:
        frame (bytes): One binary websocket frame as received.
        depth_level (int): The depth level the connection subscribed to, 20 or 200.

    Returns:
        int: The number of sections the frame carries, which is zero for a frame too short to hold a header.
    """
    frame_length = len(frame)
    if frame_length < HEADER_LENGTH:
        return 0

    sections = 0
    offset = 0
    while offset + HEADER_LENGTH <= frame_length:
        message_length, code, _, _, sequence_or_rows = DEPTH_HEADER_STRUCT.unpack_from(frame, offset)
        if code == DISCONNECT_RESPONSE_CODE:
            sections = sections + 1
            break
        if code not in (BID_RESPONSE_CODE, ASK_RESPONSE_CODE):
            if message_length < HEADER_LENGTH or offset + message_length > frame_length:
                break
            offset = offset + message_length
            sections = sections + 1
            continue
        packet_length = HEADER_LENGTH + depth_rows(sequence_or_rows, depth_level) * DEPTH_ENTRY_LENGTH
        if offset + packet_length > frame_length:
            break
        sections = sections + 1
        offset = offset + packet_length
    return sections


def decode_frame(frame, depth_level, arrival_time):
    """
    Decode every section in one binary depth frame.

    A frame whose first section header carries the disconnect code yields no ticks; the connection layer reads the reason from decode_disconnect. A frame that ends in the middle of a section stops the loop and the sections read so far are returned, because this runs inside the socket read loop and one malformed frame must not take down a connection.

    Args:
        frame (bytes): One complete binary websocket frame as received.
        depth_level (int): The depth level the connection subscribed to, 20 or 200.
        arrival_time (datetime.datetime): The moment the frame was read off the socket, recorded by the caller so that every tick in the frame shares one timestamp.

    Returns:
        list[dict]: One decoded tick per bid or ask section, in the order the sections appeared.
    """
    if len(frame) < HEADER_LENGTH:
        return []

    if frame[2] == DISCONNECT_RESPONSE_CODE:
        return []

    ticks = []
    offset = 0
    while offset + HEADER_LENGTH <= len(frame):
        message_length, code, exchange_segment, security_id, sequence_or_rows = DEPTH_HEADER_STRUCT.unpack_from(frame, offset)
        if code == DISCONNECT_RESPONSE_CODE:
            break
        if code == BID_RESPONSE_CODE or code == ASK_RESPONSE_CODE:
            tick, next_offset = decode_depth_section(frame, offset, depth_level, arrival_time)
            if tick is None:
                break
            ticks.append(tick)
            offset = next_offset
            continue
        if message_length < HEADER_LENGTH or offset + message_length > len(frame):
            break
        offset = offset + message_length
    return ticks