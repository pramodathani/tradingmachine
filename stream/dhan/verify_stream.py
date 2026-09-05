"""
Checks that Dhan's binary frames are being decoded correctly.

The synthetic checks in this module build frames byte by byte from known values and assert that every field comes back exactly, which needs no network and no market hours. They exist because a binary parser fails silently: a wrong offset, a wrong width, or a wrong field order produces numbers that are still plausible prices and quantities, and a model trading on them would give no sign that anything was wrong.

Each check targets a specific way this parser could be wrong rather than simply exercising the happy path. The quote check would fail if the day's prices were read as open, high, low, close instead of open, close, high, low, the full packet check would fail if its depth were read as five bids followed by five asks instead of five interleaved levels, and the precision check pins the float to paise conversion on a price the float32 format cannot represent exactly.

Run with: python3 -m stream.dhan.verify_stream --synthetic

The --depth mode opens a real depth socket during market hours, holds it for a few seconds, and reports what arrived: frame counts, the distinct security identifiers seen, and whether bid and ask sections arrive together. It exists because the depth frames' row layout is only pinned by synthetic bytes until a live run confirms it.

Run with: python3 -m stream.dhan.verify_stream --depth --instrument NSE_EQ:1333 --seconds 30

The --against-rest mode is the oracle check: it captures live websocket ticks for a spread of instruments, asks Dhan's REST quote endpoint what the same instruments are worth, and compares every field the two share. It also measures the implied price scale of the wire segment by segment, because Dhan documents no divisor and this is what settles whether the wire carries rupees, paise or something else entirely.

Run with: python3 -m stream.dhan.verify_stream --against-rest --per-segment 3 --seconds 12
"""

import argparse
import asyncio
import logging
import statistics
import struct
import time
from datetime import datetime

import requests
from sqlalchemy import create_engine, text as sql_text

from stream.dhan import connection, depth_packets, packets
from stream.dhan.connection import DhanConnection, EXCHANGE_SEGMENT_NAMES
from stream.dhan.credentials import websocket_credentials
from stream.dhan.depth_connection import DhanDepthConnection
from utilities.configuration import postgres_configuration
from stream.dhan.packets import (
    HEADER_LENGTH,
    PAISE_PER_RUPEE,
    RESPONSE_CODE_DISCONNECT,
    RESPONSE_CODE_FIVE_LEVEL_DEPTH,
    RESPONSE_CODE_FULL,
    RESPONSE_CODE_MARKET_STATUS,
    RESPONSE_CODE_OPEN_INTEREST,
    RESPONSE_CODE_PREV_CLOSE,
    RESPONSE_CODE_QUOTE,
    RESPONSE_CODE_TICKER,
    decode_disconnect,
    decode_frame,
    frame_packet_count,
)
from stream.dhan.depth_packets import (
    ASK_RESPONSE_CODE,
    BID_RESPONSE_CODE,
    DEPTH_ENTRY_LENGTH,
    HEADER_LENGTH as DEPTH_HEADER_LENGTH,
    decode_frame as decode_depth_frame,
    decode_disconnect as decode_depth_disconnect,
    frame_packet_count as depth_frame_packet_count,
)

ARRIVAL_TIME = datetime(2026, 9, 6, 10, 30, 0)

IDX_I_SEGMENT = 0
NSE_EQ_SEGMENT = 1
NSE_FNO_SEGMENT = 2
UNKNOWN_SEGMENT = 9

SECURITY_ID = 1333
ENDIANNESS_SECURITY_ID = 0x01000000


def expected_paise(price):
    """
    Give the paise value the decoder must produce for a wire price.

    The wire holds a float32, which rounds a price before the decoder ever sees it, so the expected value is computed through the same round trip the wire performs. Asserting against this formula pins the conversion contract exactly rather than approximately.

    Args:
        price (float): The price in rupees that the synthetic builder put on the wire.

    Returns:
        int: The paise value the decoder must store for this price.
    """
    return round(struct.unpack("<f", struct.pack("<f", price))[0] * PAISE_PER_RUPEE)


def build_frame(packets):
    """
    Assemble a binary websocket frame out of already-built packets.

    The live feed stacks packets one after another with no frame level prefix, so a frame is simply its packets in order.

    Args:
        packets (list[bytes]): The packets to place in the frame, in order.

    Returns:
        bytes: A frame carrying exactly those packets.
    """
    frame = b""
    for packet in packets:
        frame = frame + packet
    return frame


def build_header(code, exchange_segment, security_id, packet_length):
    """
    Build an eight byte live feed packet header.

    Args:
        code (int): The feed response code.
        exchange_segment (int): The exchange segment byte.
        security_id (int): The Dhan security identifier.
        packet_length (int): The message length to claim in the header, which this module's builder states as the whole packet including the header.

    Returns:
        bytes: The eight byte header.
    """
    return struct.pack("<BHBI", code, packet_length, exchange_segment, security_id)


def build_packet(code, exchange_segment, security_id, payload):
    """
    Build one live feed packet out of a header and a payload.

    Args:
        code (int): The feed response code.
        exchange_segment (int): The exchange segment byte.
        security_id (int): The Dhan security identifier.
        payload (bytes): The packet's bytes after the header.

    Returns:
        bytes: The complete packet.
    """
    return build_header(code, exchange_segment, security_id, HEADER_LENGTH + len(payload)) + payload


def build_ticker_packet(exchange_segment, security_id, last_price, last_trade_seconds):
    """
    Build a sixteen byte ticker packet.

    Args:
        exchange_segment (int): The exchange segment byte.
        security_id (int): The Dhan security identifier.
        last_price (float): The last traded price in rupees as it sits on the wire.
        last_trade_seconds (int): Seconds since the Unix epoch of the last trade.

    Returns:
        bytes: The packet.
    """
    payload = struct.pack("<fI", last_price, last_trade_seconds)
    return build_packet(RESPONSE_CODE_TICKER, exchange_segment, security_id, payload)


def build_quote_packet(exchange_segment, security_id, values):
    """
    Build a fifty byte quote packet.

    The day's prices are written in the wire's order open, close, high, low, which is what the decoder must reproduce.

    Args:
        exchange_segment (int): The exchange segment byte.
        security_id (int): The Dhan security identifier.
        values (dict): Wire values keyed by name, covering last_price, last_traded_quantity, last_trade_seconds, average_traded_price, volume_traded, total_sell_quantity, total_buy_quantity, open_price, close_price, high_price and low_price.

    Returns:
        bytes: The packet.
    """
    payload = struct.pack(
        "<fHIfIIIffff",
        values["last_price"],
        values["last_traded_quantity"],
        values["last_trade_seconds"],
        values["average_traded_price"],
        values["volume_traded"],
        values["total_sell_quantity"],
        values["total_buy_quantity"],
        values["open_price"],
        values["close_price"],
        values["high_price"],
        values["low_price"],
    )
    return build_packet(RESPONSE_CODE_QUOTE, exchange_segment, security_id, payload)


def build_depth_entries(levels):
    """
    Build the five interleaved twenty byte depth entries of a full or five level depth packet.

    Args:
        levels (list[tuple]): One tuple per level of bid quantity, ask quantity, bid order count, ask order count, bid price and ask price.

    Returns:
        bytes: One hundred bytes of depth.
    """
    payload = b""
    for bid_quantity, ask_quantity, bid_orders, ask_orders, bid_price, ask_price in levels:
        payload = payload + struct.pack("<IIHHff", bid_quantity, ask_quantity, bid_orders, ask_orders, bid_price, ask_price)
    return payload


def build_full_packet(exchange_segment, security_id, values, levels):
    """
    Build a one hundred and sixty two byte full packet.

    Args:
        exchange_segment (int): The exchange segment byte.
        security_id (int): The Dhan security identifier.
        values (dict): Wire values keyed by name, covering everything a quote packet carries plus open_interest, open_interest_day_high and open_interest_day_low.
        levels (list[tuple]): Five interleaved depth levels as build_depth_entries expects.

    Returns:
        bytes: The packet.
    """
    payload = struct.pack(
        "<fHIfIIIIIIffff",
        values["last_price"],
        values["last_traded_quantity"],
        values["last_trade_seconds"],
        values["average_traded_price"],
        values["volume_traded"],
        values["total_sell_quantity"],
        values["total_buy_quantity"],
        values["open_interest"],
        values["open_interest_day_high"],
        values["open_interest_day_low"],
        values["open_price"],
        values["close_price"],
        values["high_price"],
        values["low_price"],
    )
    return build_packet(RESPONSE_CODE_FULL, exchange_segment, security_id, payload + build_depth_entries(levels))


def build_five_level_depth_packet(exchange_segment, security_id, last_price, levels):
    """
    Build a one hundred and twelve byte five level depth packet, response code 3.

    Args:
        exchange_segment (int): The exchange segment byte.
        security_id (int): The Dhan security identifier.
        last_price (float): The last traded price in rupees as it sits on the wire.
        levels (list[tuple]): Five interleaved depth levels as build_depth_entries expects.

    Returns:
        bytes: The packet.
    """
    payload = struct.pack("<f", last_price) + build_depth_entries(levels)
    return build_packet(RESPONSE_CODE_FIVE_LEVEL_DEPTH, exchange_segment, security_id, payload)


def build_open_interest_packet(exchange_segment, security_id, open_interest):
    """
    Build a twelve byte open interest packet.

    Args:
        exchange_segment (int): The exchange segment byte.
        security_id (int): The Dhan security identifier.
        open_interest (int): The open interest figure.

    Returns:
        bytes: The packet.
    """
    return build_packet(RESPONSE_CODE_OPEN_INTEREST, exchange_segment, security_id, struct.pack("<I", open_interest))


def build_prev_close_packet(exchange_segment, security_id, previous_close, previous_open_interest):
    """
    Build a sixteen byte previous close packet.

    Args:
        exchange_segment (int): The exchange segment byte.
        security_id (int): The Dhan security identifier.
        previous_close (float): The previous day's close price in rupees as it sits on the wire.
        previous_open_interest (int): The previous day's open interest.

    Returns:
        bytes: The packet.
    """
    payload = struct.pack("<fI", previous_close, previous_open_interest)
    return build_packet(RESPONSE_CODE_PREV_CLOSE, exchange_segment, security_id, payload)


def build_market_status_packet(exchange_segment, security_id):
    """
    Build an eight byte market status packet, which carries no payload.

    Args:
        exchange_segment (int): The exchange segment byte.
        security_id (int): The Dhan security identifier.

    Returns:
        bytes: The packet.
    """
    return build_packet(RESPONSE_CODE_MARKET_STATUS, exchange_segment, security_id, b"")


def build_disconnect_packet(reason_code):
    """
    Build a ten byte disconnect packet.

    Args:
        reason_code (int): The disconnection reason code.

    Returns:
        bytes: The packet.
    """
    return build_header(RESPONSE_CODE_DISCONNECT, 0, 0, 10) + struct.pack("<H", reason_code)


def build_depth_frame(depth_level, exchange_segment, security_id, bid_rows, ask_rows):
    """
    Build one depth frame carrying one instrument's bid section followed by its ask section.

    Args:
        depth_level (int): The depth level to build for, 20 or 200.
        exchange_segment (int): The exchange segment byte.
        security_id (int): The Dhan security identifier.
        bid_rows (int): How many bid rows to write.
        ask_rows (int): How many ask rows to write.

    Returns:
        bytes: The frame, twelve byte headers included, with the sequence or row count field set to the row count in both sections.
    """
    frame = struct.pack("<hBBiI", DEPTH_HEADER_LENGTH + bid_rows * DEPTH_ENTRY_LENGTH, BID_RESPONSE_CODE, exchange_segment, security_id, bid_rows)
    for row in range(bid_rows):
        frame = frame + struct.pack("<dII", 2841.50 - row * 0.05, 50 + row * 10, row + 1)
    frame = frame + struct.pack("<hBBiI", DEPTH_HEADER_LENGTH + ask_rows * DEPTH_ENTRY_LENGTH, ASK_RESPONSE_CODE, exchange_segment, security_id, ask_rows)
    for row in range(ask_rows):
        frame = frame + struct.pack("<dII", 2841.60 + row * 0.05, 60 + row * 10, row + 2)
    return frame


def check_short_frames_decode_to_nothing():
    """
    A frame too short to carry a header must decode to no ticks rather than raising.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    ticks = decode_frame(b"", ARRIVAL_TIME)
    one_byte = decode_frame(b"\x01", ARRIVAL_TIME)
    seven_bytes = decode_frame(b"\x00" * 7, ARRIVAL_TIME)
    depth_ticks = decode_depth_frame(b"", 20, ARRIVAL_TIME)
    depth_one_byte = decode_depth_frame(b"\x01", 20, ARRIVAL_TIME)
    depth_eleven_bytes = decode_depth_frame(b"\x00" * 11, 20, ARRIVAL_TIME)
    passed = ticks == [] and one_byte == [] and seven_bytes == [] and depth_ticks == [] and depth_one_byte == [] and depth_eleven_bytes == []
    return ("frames shorter than a header decode to nothing", passed, f"live {ticks!r}, depth {depth_ticks!r}")


def check_endianness():
    """
    A security identifier must be read little endian, which is the opposite of Zerodha's frames.

    The bytes of the value chosen here are zero, zero, zero, one, which a big endian reader would report as one and a little endian reader reports as one crore sixty seven lakh.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    frame = build_frame([build_ticker_packet(NSE_EQ_SEGMENT, ENDIANNESS_SECURITY_ID, 2841.55, 1788609598)])
    tick = decode_frame(frame, ARRIVAL_TIME)[0]
    passed = tick["security_id"] == 16777216
    return ("security id read little endian", passed, f"security id {tick['security_id']}")


def check_ticker_packet():
    """
    A ticker packet must yield the security id, segment, price in paise and last trade time.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    frame = build_frame([build_ticker_packet(NSE_EQ_SEGMENT, SECURITY_ID, 2841.55, 1788609598)])
    ticks = decode_frame(frame, ARRIVAL_TIME)
    tick = ticks[0]
    passed = (
        len(ticks) == 1
        and tick["security_id"] == SECURITY_ID
        and tick["exchange_segment"] == NSE_EQ_SEGMENT
        and tick["dhan_segment"] == "nse_eq"
        and tick["tick_mode"] == "ticker"
        and tick["tradable"] is True
        and tick["price_divisor"] == 100
        and tick["last_price"] == expected_paise(2841.55)
        and tick["last_trade_time"] == datetime.fromtimestamp(1788609598)
    )
    return ("ticker packet", passed, f"security id {tick['security_id']} price {tick['last_price']} mode {tick['tick_mode']}")


def check_quote_packet_field_order():
    """
    A quote packet must be read as open, close, high, low, not as open, high, low, close.

    The four prices are deliberately all different, so reading them in the wrong order fails this check. The wire also puts the total sell quantity before the total buy quantity, the reverse of Zerodha's order, so those two are checked as well.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    values = {
        "last_price": 2841.55,
        "last_traded_quantity": 12,
        "last_trade_seconds": 1788609598,
        "average_traded_price": 2838.12,
        "volume_traded": 4182933,
        "total_sell_quantity": 96311,
        "total_buy_quantity": 118422,
        "open_price": 2820.00,
        "close_price": 2819.35,
        "high_price": 2851.90,
        "low_price": 2815.05,
    }
    frame = build_frame([build_quote_packet(NSE_EQ_SEGMENT, SECURITY_ID, values)])
    tick = decode_frame(frame, ARRIVAL_TIME)[0]

    problems = []
    if tick["open_price"] != expected_paise(values["open_price"]):
        problems.append(f"open {tick['open_price']}")
    if tick["close_price"] != expected_paise(values["close_price"]):
        problems.append(f"close {tick['close_price']}")
    if tick["high_price"] != expected_paise(values["high_price"]):
        problems.append(f"high {tick['high_price']}")
    if tick["low_price"] != expected_paise(values["low_price"]):
        problems.append(f"low {tick['low_price']}")
    if tick["last_price"] != expected_paise(values["last_price"]):
        problems.append(f"last price {tick['last_price']}")
    if tick["average_traded_price"] != expected_paise(values["average_traded_price"]):
        problems.append(f"average traded price {tick['average_traded_price']}")
    if tick["total_sell_quantity"] != values["total_sell_quantity"]:
        problems.append(f"sell quantity {tick['total_sell_quantity']}")
    if tick["total_buy_quantity"] != values["total_buy_quantity"]:
        problems.append(f"buy quantity {tick['total_buy_quantity']}")
    if tick["volume_traded"] != values["volume_traded"]:
        problems.append(f"volume {tick['volume_traded']}")
    if tick["last_traded_quantity"] != values["last_traded_quantity"]:
        problems.append(f"last traded quantity {tick['last_traded_quantity']}")
    if "bid_prices" in tick:
        problems.append("carries depth")

    passed = not problems
    return ("quote packet, open close high low order", passed, "; ".join(problems) or "all eleven fields exact, sell before buy, no depth")


def check_full_packet():
    """
    A full packet must yield open interest before the day's prices, and five interleaved depth levels a side.

    The open interest figures are chosen so reading a full packet with the quote reader puts an open interest where the open belongs and fails. The bid and ask prices per level are chosen so reading the depth as five bids followed by five asks puts level two's bid where level one's ask belongs and fails. The order counts include 65535, so a wrong width shows up as wrong prices rather than only wrong counts.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    values = {
        "last_price": 2841.55,
        "last_traded_quantity": 12,
        "last_trade_seconds": 1788609598,
        "average_traded_price": 2838.12,
        "volume_traded": 4182933,
        "total_sell_quantity": 96311,
        "total_buy_quantity": 118422,
        "open_interest": 21845,
        "open_interest_day_high": 30000,
        "open_interest_day_low": 11000,
        "open_price": 2820.00,
        "close_price": 2819.35,
        "high_price": 2851.90,
        "low_price": 2815.05,
    }
    levels = [
        (53, 43, 1, 2, 2841.50, 2841.60),
        (120, 90, 3, 4, 2841.45, 2841.65),
        (8, 250, 1, 9, 2841.40, 2841.70),
        (400, 11, 7, 1, 2841.35, 2841.75),
        (17, 600, 2, 65535, 2841.30, 2841.80),
    ]
    frame = build_frame([build_full_packet(NSE_FNO_SEGMENT, SECURITY_ID, values, levels)])
    tick = decode_frame(frame, ARRIVAL_TIME)[0]

    problems = []
    if tick["tick_mode"] != "full":
        problems.append(f"mode {tick['tick_mode']}")
    if tick["open_interest"] != values["open_interest"]:
        problems.append(f"open interest {tick['open_interest']}")
    if tick["open_interest_day_high"] != values["open_interest_day_high"]:
        problems.append(f"open interest day high {tick['open_interest_day_high']}")
    if tick["open_interest_day_low"] != values["open_interest_day_low"]:
        problems.append(f"open interest day low {tick['open_interest_day_low']}")
    if tick["open_price"] != expected_paise(values["open_price"]):
        problems.append(f"open {tick['open_price']}")
    if tick["close_price"] != expected_paise(values["close_price"]):
        problems.append(f"close {tick['close_price']}")
    if tick["high_price"] != expected_paise(values["high_price"]):
        problems.append(f"high {tick['high_price']}")
    if tick["low_price"] != expected_paise(values["low_price"]):
        problems.append(f"low {tick['low_price']}")
    if tick["last_trade_time"] != datetime.fromtimestamp(1788609598):
        problems.append(f"last trade time {tick['last_trade_time']}")

    expected_bid_prices = [expected_paise(2841.50), expected_paise(2841.45), expected_paise(2841.40), expected_paise(2841.35), expected_paise(2841.30)]
    expected_ask_prices = [expected_paise(2841.60), expected_paise(2841.65), expected_paise(2841.70), expected_paise(2841.75), expected_paise(2841.80)]
    expected_bid_orders = [1, 3, 1, 7, 2]
    expected_ask_orders = [2, 4, 9, 1, 65535]
    expected_bid_quantities = [53, 120, 8, 400, 17]
    expected_ask_quantities = [43, 90, 250, 11, 600]
    if tick["bid_prices"] != expected_bid_prices:
        problems.append(f"bid prices {tick['bid_prices']}")
    if tick["ask_prices"] != expected_ask_prices:
        problems.append(f"ask prices {tick['ask_prices']}")
    if tick["bid_orders"] != expected_bid_orders:
        problems.append(f"bid orders {tick['bid_orders']}")
    if tick["ask_orders"] != expected_ask_orders:
        problems.append(f"ask orders {tick['ask_orders']}")
    if tick["bid_quantities"] != expected_bid_quantities:
        problems.append(f"bid quantities {tick['bid_quantities']}")
    if tick["ask_quantities"] != expected_ask_quantities:
        problems.append(f"ask quantities {tick['ask_quantities']}")

    passed = not problems
    return ("full packet, open interest placement and interleaved depth", passed, "; ".join(problems) or "all fields exact, five interleaved levels a side, 65535 orders survived")


def check_float32_precision():
    """
    A price with no exact float32 representation must convert to the paise of the float32 that was actually sent.

    The wire rounds the price to float32 before this project sees it, so the decoder's contract is the paise of the unpacked float, not the paise of the decimal that was packed. The value chosen here is one the float32 format cannot represent exactly.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    price = 2841.61
    frame = build_frame([build_ticker_packet(NSE_EQ_SEGMENT, SECURITY_ID, price, 0)])
    tick = decode_frame(frame, ARRIVAL_TIME)[0]
    passed = tick["last_price"] == expected_paise(price)
    return ("float32 to paise conversion", passed, f"wire {price} stored {tick['last_price']} paise")


def check_side_packets():
    """
    The previous close, open interest, market status and disconnect packets must each behave as documented.

    A previous close packet carries yesterday's close and yesterday's open interest, an open interest packet carries today's open interest alone, a market status packet carries no tick at all, and a disconnect packet yields no tick while decode_disconnect reports the reason.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    prev_close_frame = build_frame([build_prev_close_packet(NSE_EQ_SEGMENT, SECURITY_ID, 2819.35, 15000)])
    prev_close_tick = decode_frame(prev_close_frame, ARRIVAL_TIME)[0]

    oi_frame = build_frame([build_open_interest_packet(NSE_FNO_SEGMENT, SECURITY_ID, 21845)])
    oi_tick = decode_frame(oi_frame, ARRIVAL_TIME)[0]

    status_frame = build_frame([build_market_status_packet(NSE_EQ_SEGMENT, SECURITY_ID)])
    status_ticks = decode_frame(status_frame, ARRIVAL_TIME)

    disconnect_frame = build_frame([build_disconnect_packet(807)])
    disconnect_ticks = decode_frame(disconnect_frame, ARRIVAL_TIME)

    depth_disconnect_frame = struct.pack("<hBBiI", 14, 50, NSE_EQ_SEGMENT, SECURITY_ID, 0) + struct.pack("<H", 805)
    depth_disconnect_ticks = decode_depth_frame(depth_disconnect_frame, 20, ARRIVAL_TIME)

    problems = []
    if prev_close_tick["tick_mode"] != "prev_close":
        problems.append(f"prev close mode {prev_close_tick['tick_mode']}")
    if prev_close_tick["close_price"] != expected_paise(2819.35):
        problems.append(f"prev close {prev_close_tick['close_price']}")
    if prev_close_tick["open_interest"] != 15000:
        problems.append(f"prev open interest {prev_close_tick['open_interest']}")
    if oi_tick["tick_mode"] != "oi":
        problems.append(f"open interest mode {oi_tick['tick_mode']}")
    if oi_tick["open_interest"] != 21845:
        problems.append(f"open interest {oi_tick['open_interest']}")
    if status_ticks != []:
        problems.append(f"market status gave {status_ticks!r}")
    if disconnect_ticks != []:
        problems.append(f"disconnect gave {disconnect_ticks!r}")
    if decode_disconnect(disconnect_frame) != "access_token_expired":
        problems.append(f"disconnect reason {decode_disconnect(disconnect_frame)!r}")
    if depth_disconnect_ticks != []:
        problems.append(f"depth disconnect gave {depth_disconnect_ticks!r}")
    if decode_depth_disconnect(depth_disconnect_frame) != "connection_limit_exceeded":
        problems.append(f"depth disconnect reason {decode_depth_disconnect(depth_disconnect_frame)!r}")

    passed = not problems
    return ("prev close, open interest, market status and disconnect packets", passed, "; ".join(problems) or "prev close and open interest exact, market status and disconnect silent, reasons named on both feeds")


def check_five_level_depth_packet():
    """
    A one hundred and twelve byte packet, response code 3, must yield the last traded price and five interleaved depth levels.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    levels = [
        (53, 43, 1, 2, 2841.50, 2841.60),
        (120, 90, 3, 4, 2841.45, 2841.65),
        (8, 250, 1, 9, 2841.40, 2841.70),
        (400, 11, 7, 1, 2841.35, 2841.75),
        (17, 600, 2, 65535, 2841.30, 2841.80),
    ]
    frame = build_frame([build_five_level_depth_packet(NSE_EQ_SEGMENT, SECURITY_ID, 2841.55, levels)])
    tick = decode_frame(frame, ARRIVAL_TIME)[0]

    problems = []
    if tick["tick_mode"] != "depth":
        problems.append(f"mode {tick['tick_mode']}")
    if tick["last_price"] != expected_paise(2841.55):
        problems.append(f"last price {tick['last_price']}")
    if tick["bid_prices"] != [expected_paise(2841.50), expected_paise(2841.45), expected_paise(2841.40), expected_paise(2841.35), expected_paise(2841.30)]:
        problems.append(f"bid prices {tick['bid_prices']}")
    if tick["ask_prices"] != [expected_paise(2841.60), expected_paise(2841.65), expected_paise(2841.70), expected_paise(2841.75), expected_paise(2841.80)]:
        problems.append(f"ask prices {tick['ask_prices']}")
    if tick["bid_orders"] != [1, 3, 1, 7, 2]:
        problems.append(f"bid orders {tick['bid_orders']}")
    if tick["ask_orders"] != [2, 4, 9, 1, 65535]:
        problems.append(f"ask orders {tick['ask_orders']}")
    if tick["bid_quantities"] != [53, 120, 8, 400, 17]:
        problems.append(f"bid quantities {tick['bid_quantities']}")
    if tick["ask_quantities"] != [43, 90, 250, 11, 600]:
        problems.append(f"ask quantities {tick['ask_quantities']}")

    passed = not problems
    return ("five level depth packet", passed, "; ".join(problems) or "price and five interleaved levels exact")


def check_depth_frame():
    """
    A depth frame must yield a bid tick and an ask tick, each with the rows the subscription asked for.

    The twenty level frame's header sequence number is set to the row count even though the decoder must ignore it and use the subscription's depth level, which is what distinguishes the two sockets.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    frame = build_depth_frame(20, NSE_EQ_SEGMENT, SECURITY_ID, 20, 20)
    ticks = decode_depth_frame(frame, 20, ARRIVAL_TIME)

    problems = []
    if len(ticks) != 2:
        problems.append(f"decoded {len(ticks)} sections")
    else:
        if ticks[0]["side"] != "bid" or ticks[1]["side"] != "ask":
            problems.append(f"sides {ticks[0]['side']} then {ticks[1]['side']}")
        if ticks[0]["tick_mode"] != "depth_twenty" or ticks[1]["tick_mode"] != "depth_twenty":
            problems.append(f"modes {ticks[0]['tick_mode']} {ticks[1]['tick_mode']}")
        if ticks[0]["bid_prices"][0] != expected_paise(2841.50) or ticks[0]["bid_prices"][19] != expected_paise(2841.50 - 19 * 0.05):
            problems.append(f"bid prices {ticks[0]['bid_prices'][0]} {ticks[0]['bid_prices'][19]}")
        if ticks[1]["ask_prices"][0] != expected_paise(2841.60) or ticks[1]["ask_prices"][19] != expected_paise(2841.60 + 19 * 0.05):
            problems.append(f"ask prices {ticks[1]['ask_prices'][0]} {ticks[1]['ask_prices'][19]}")
        if len(ticks[0]["bid_quantities"]) != 20 or len(ticks[1]["ask_orders"]) != 20:
            problems.append(f"row counts {len(ticks[0]['bid_quantities'])} {len(ticks[1]['ask_orders'])}")

    passed = not problems
    return ("depth frame, bid and ask sections", passed, "; ".join(problems) or "bid then ask, twenty rows a side, prices and order counts exact")


def check_unknown_code_and_truncation():
    """
    An unknown response code must be skipped, and neither it nor truncation may ever raise.

    An exception in the decode loop would run inside the socket read loop and take down a connection carrying thousands of instruments over one malformed frame.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    unknown_packet = build_header(9, NSE_EQ_SEGMENT, SECURITY_ID, 24) + b"\x00" * 16
    ticker_packet = build_ticker_packet(NSE_EQ_SEGMENT, SECURITY_ID, 2841.55, 1788609598)
    frame = build_frame([unknown_packet, ticker_packet])
    ticks = decode_frame(frame, ARRIVAL_TIME)

    problems = []
    if len(ticks) != 1 or ticks[0]["tick_mode"] != "ticker":
        problems.append(f"unknown code skipped to {ticks!r}")

    stacked = build_frame([
        build_ticker_packet(NSE_EQ_SEGMENT, SECURITY_ID, 2841.55, 1788609598),
        build_ticker_packet(IDX_I_SEGMENT, SECURITY_ID, 22350.25, 0),
    ])
    for cut in range(1, len(stacked)):
        try:
            decode_frame(stacked[:cut], ARRIVAL_TIME)
            decode_depth_frame(stacked[:cut], 20, ARRIVAL_TIME)
        except Exception as error:
            problems.append(f"cut at {cut} raised {type(error).__name__}: {error}")

    lying_length = build_header(RESPONSE_CODE_TICKER, NSE_EQ_SEGMENT, SECURITY_ID, 4000) + b"\x00" * 16
    try:
        lying_ticks = decode_frame(build_frame([lying_length, ticker_packet]), ARRIVAL_TIME)
    except Exception as error:
        problems.append(f"overstated length raised {type(error).__name__}: {error}")
        lying_ticks = []
    if len(lying_ticks) != 1:
        problems.append(f"overstated length gave {lying_ticks!r}")

    passed = not problems
    return ("unknown codes and truncated frames never raise", passed, "; ".join(problems) or f"unknown code skipped, all {len(stacked) - 1} truncations handled, overstated length gave {len(lying_ticks)} packets")


def check_frame_packet_count():
    """
    The archive's frame packet counter must count every packet in a stacked frame.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    frame = build_frame([
        build_ticker_packet(NSE_EQ_SEGMENT, SECURITY_ID, 2841.55, 1788609598),
        build_prev_close_packet(NSE_EQ_SEGMENT, SECURITY_ID, 2819.35, 15000),
        build_market_status_packet(NSE_EQ_SEGMENT, SECURITY_ID),
    ])
    depth_frame = build_depth_frame(20, NSE_EQ_SEGMENT, SECURITY_ID, 20, 20)
    passed = (
        frame_packet_count(frame) == 3
        and frame_packet_count(b"") == 0
        and frame_packet_count(b"\x01" * 7) == 0
        and depth_frame_packet_count(depth_frame, 20) == 2
        and depth_frame_packet_count(b"", 20) == 0
    )
    return ("frame packet counts", passed, f"live {frame_packet_count(frame)}, depth {depth_frame_packet_count(depth_frame, 20)}")


def check_wire_code_bytes():
    """
    The builder constants must sit at the wire positions the real feed uses.

    The depth frame builder and the depth decoder share one module's constants, so an edit to a response code would leave the checks self-consistent and silently agree with themselves. This check pins the bytes those constants produce to their literal documented values, so the constants cannot drift from the wire without a live run noticing.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    ticker_frame = build_frame([build_ticker_packet(NSE_EQ_SEGMENT, SECURITY_ID, 2841.55, 0)])
    depth_frame = build_depth_frame(20, NSE_EQ_SEGMENT, SECURITY_ID, 2, 2)
    ask_section_offset = DEPTH_HEADER_LENGTH + 2 * DEPTH_ENTRY_LENGTH
    disconnect_frame = struct.pack("<hBBiI", 14, 50, NSE_EQ_SEGMENT, SECURITY_ID, 0) + struct.pack("<H", 805)

    problems = []
    if ticker_frame[0] != 2:
        problems.append(f"live feed code byte {ticker_frame[0]}")
    if depth_frame[2] != 41:
        problems.append(f"depth bid code byte {depth_frame[2]}")
    if depth_frame[ask_section_offset + 2] != 51:
        problems.append(f"depth ask code byte {depth_frame[ask_section_offset + 2]}")
    if disconnect_frame[2] != 50:
        problems.append(f"depth disconnect code byte {disconnect_frame[2]}")

    passed = not problems
    return ("wire code bytes pinned", passed, "; ".join(problems) or "live code 2 at byte 0, depth bid 41, ask 51 and disconnect 50 at byte 2")


def check_segment_tables_agree():
    """
    The decoders' and the connection's segment tables must cover exactly the segments Dhan documents.

    The segment name tables are duplicated between the two decoders and the connection owns the wire's spelled-out names, so this check is what keeps the three from drifting apart.

    Returns:
        tuple: A (name, passed, detail) triple.
    """
    documented_segments = {0, 1, 2, 3, 4, 5, 7, 8}
    problems = []
    if set(packets.SEGMENT_NAMES) != documented_segments:
        problems.append(f"live feed table {sorted(packets.SEGMENT_NAMES)}")
    if set(depth_packets.SEGMENT_NAMES) != documented_segments:
        problems.append(f"depth table {sorted(depth_packets.SEGMENT_NAMES)}")
    if set(connection.EXCHANGE_SEGMENT_NAMES) != documented_segments:
        problems.append(f"connection table {sorted(connection.EXCHANGE_SEGMENT_NAMES)}")
    if packets.SEGMENT_NAMES != depth_packets.SEGMENT_NAMES:
        problems.append("the two decoder tables disagree on names")

    passed = not problems
    return ("segment name tables agree", passed, "; ".join(problems) or f"all three tables cover {sorted(documented_segments)}")


SYNTHETIC_CHECKS = [
    check_short_frames_decode_to_nothing,
    check_endianness,
    check_ticker_packet,
    check_quote_packet_field_order,
    check_full_packet,
    check_float32_precision,
    check_side_packets,
    check_five_level_depth_packet,
    check_depth_frame,
    check_unknown_code_and_truncation,
    check_frame_packet_count,
    check_wire_code_bytes,
    check_segment_tables_agree,
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


def parse_instruments(instrument_arguments):
    """
    Turn command line instrument arguments into (exchange_segment, security_id) pairs.

    Args:
        instrument_arguments (list[str]): One argument per instrument, each spelled as the wire's segment name, a colon, and the security identifier, for example "NSE_EQ:1333".

    Returns:
        list[tuple]: One (exchange_segment, security_id) pair per argument.

    Raises:
        ValueError: If an argument is not in SEGMENT:SECURITY_ID form, names an unknown segment, or has a security identifier that is not a number.
    """
    segment_by_wire_name = {wire_name: segment for segment, wire_name in EXCHANGE_SEGMENT_NAMES.items()}
    instruments = []
    for instrument_argument in instrument_arguments:
        try:
            wire_name, security_id_text = instrument_argument.split(":", 1)
        except ValueError:
            raise ValueError(f"Instrument {instrument_argument!r} must be spelled SEGMENT:SECURITY_ID, for example NSE_EQ:1333.")
        if wire_name not in segment_by_wire_name:
            raise ValueError(f"Segment {wire_name!r} is unknown; the known names are {sorted(segment_by_wire_name)}.")
        if not security_id_text.isdigit():
            raise ValueError(f"Security id {security_id_text!r} is not a number.")
        instruments.append((segment_by_wire_name[wire_name], int(security_id_text)))
    return instruments


def run_depth(arguments):
    """
    Hold a real depth socket open for a few seconds and report what arrived.

    This is a live check: it needs a valid access token and, for any real data, market hours. It prints its report and returns a failure count, treating a connection that arrived but saw nothing as a pass with a note, since outside market hours silence is the expected answer.

    Args:
        arguments (argparse.Namespace): The parsed command line, carrying depth_level, instrument and seconds.

    Returns:
        int: The number of checks that failed, always zero or one.

    Raises:
        SystemExit: If the credentials are missing or the connection was refused outright, since no report would be meaningful.
    """
    client_id, access_token = websocket_credentials()
    instruments = parse_instruments(arguments.instrument)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    counters = {
        "data_frames": 0,
        "heartbeats": 0,
        "disconnects": 0,
        "bid_sections": 0,
        "ask_sections": 0,
        "security_ids": set(),
        "rows_read": 0,
    }

    def on_frame(arrival_time_nanoseconds, frame):
        arrival_time = datetime.fromtimestamp(arrival_time_nanoseconds / 1_000_000_000)
        if len(frame) < DEPTH_HEADER_LENGTH:
            counters["heartbeats"] = counters["heartbeats"] + 1
            return
        if frame[2] == BID_RESPONSE_CODE or frame[2] == ASK_RESPONSE_CODE:
            counters["data_frames"] = counters["data_frames"] + 1
            ticks = decode_depth_frame(frame, arguments.depth_level, arrival_time)
            for tick in ticks:
                counters["security_ids"].add(tick["security_id"])
                counters["rows_read"] = counters["rows_read"] + len(tick["bid_prices"] + tick["ask_prices"])
                if tick["side"] == "bid":
                    counters["bid_sections"] = counters["bid_sections"] + 1
                else:
                    counters["ask_sections"] = counters["ask_sections"] + 1
        else:
            counters["disconnects"] = counters["disconnects"] + 1

    async def drive():
        stop_event = asyncio.Event()
        depth_connection = DhanDepthConnection(
            arguments.depth_level,
            client_id,
            access_token,
            instruments,
            on_frame=on_frame,
            logger=logging.getLogger("verify_stream.depth"),
        )
        async def close_when_done():
            await asyncio.sleep(arguments.seconds)
            stop_event.set()
        await asyncio.gather(depth_connection.run(stop_event), close_when_done())
        return depth_connection

    print(f"Depth check: {arguments.depth_level} level socket, {len(instruments)} instrument(s), {arguments.seconds:.0f} seconds")
    print()
    try:
        depth_connection = asyncio.run(drive())
    except Exception as error:
        print(f"  FAIL  the connection did not survive its run: {type(error).__name__}: {error}")
        return 1

    paired = counters["bid_sections"] > 0 and abs(counters["bid_sections"] - counters["ask_sections"]) <= 2
    passed = True
    problems = []

    print(f"  frames received         {depth_connection.frames_received}")
    print(f"  data frames             {counters['data_frames']}")
    print(f"  heartbeats              {counters['heartbeats']}")
    print(f"  disconnect packets      {counters['disconnects']}")
    print(f"  distinct security ids   {len(counters['security_ids'])}")
    print(f"  bid sections            {counters['bid_sections']}")
    print(f"  ask sections            {counters['ask_sections']}")
    print(f"  depth rows read         {counters['rows_read']}")
    print(f"  reconnects              {depth_connection.reconnect_count}")
    print()

    if counters["data_frames"] == 0:
        print("  NOTE  no data frames arrived; outside market hours that is the expected answer, run again during a session")
    else:
        if not paired:
            passed = False
            problems.append(f"bid sections {counters['bid_sections']} and ask sections {counters['ask_sections']} did not arrive together")
        if len(counters["security_ids"]) != len(instruments):
            passed = False
            problems.append(f"subscribed {len(instruments)} instrument(s) but saw {len(counters['security_ids'])}")
        if depth_connection.reconnect_count > 0:
            passed = False
            problems.append(f"reconnected {depth_connection.reconnect_count} times during a short hold, which should not happen")

    if problems:
        for problem in problems:
            print(f"  FAIL  {problem}")
    else:
        print("  PASS  frames decoded, bid and ask sections arrived together, every subscribed instrument was seen")
    print()
    return 0 if passed else 1


QUOTE_ENDPOINT = "https://api.dhan.co/v2/marketfeed/quote"

VERIFICATION_TOLERANCE = 0.011

QUOTE_BATCH_SIZE = 1000
QUOTE_REQUEST_PAUSE_SECONDS = 1.0


def dhan_exchange_segment(master_exchange, master_segment):
    """
    Translate an instruments.master exchange and segment into Dhan's exchange segment number.

    Dhan's instrument list covers eight of the canonical segments; indexes on BSE and everything on NCDEX have no Dhan feed, so they translate to None and the cross-check skips them.

    Args:
        master_exchange (str): The canonical lowercase exchange stored in instruments.master, for example "nse".
        master_segment (str): The exchange-prefixed segment stored in instruments.master, for example "nse_equities".

    Returns:
        int | None: Dhan's exchange segment number, or None when Dhan does not feed this segment.
    """
    bare_segment = master_segment.partition("_")[2]
    if master_exchange == "nse":
        if bare_segment == "equities":
            return 1
        if bare_segment in ("equity_futures", "equity_options", "equity_index_futures", "equity_index_options"):
            return 2
        if bare_segment == "equity_indices":
            return 0
        if bare_segment == "currencies" or bare_segment.startswith("currency_"):
            return 3
    if master_exchange == "bse":
        if bare_segment == "equities":
            return 4
        if bare_segment in ("equity_futures", "equity_options", "equity_index_futures", "equity_index_options"):
            return 8
        if bare_segment == "currencies" or bare_segment.startswith("currency_"):
            return 7
    if master_exchange == "mcx" and (bare_segment == "commodities" or bare_segment.startswith("commodity_")):
        return 5
    return None


def select_verification_instruments(engine, per_segment):
    """
    Choose Dhan instruments to check against Dhan's own quote endpoint, spanning as many segments as possible.

    Expired contracts are excluded because the quote endpoint will not price them and they would produce gaps rather than comparisons. Futures are preferred over options within a derivative segment, since they are more likely to have traded and therefore to carry a full set of values worth comparing.

    Args:
        engine: A SQLAlchemy engine for the black_box database.
        per_segment (int): How many instruments to take from each Dhan exchange segment.

    Returns:
        list[dict]: One entry per instrument with keys "exchange_segment", "security_id", "identifier" and "master_segment", where the identifier is the wire's segment name and security id joined by a colon as the subscription and the quote endpoint both expect.

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
        "  WHERE b.broker = 'dhan'"
        "    AND b.mapping_date = (SELECT max(mapping_date) FROM instruments.broker_mappings WHERE broker = 'dhan')"
        "    AND (m.expiry_date IS NULL OR m.expiry_date > CURRENT_DATE)"
        ") ranked WHERE rank <= :per_segment"
    )
    with engine.connect() as connection:
        rows = connection.execute(statement, {"per_segment": per_segment}).all()

    chosen = {}
    for broker_token, master_exchange, master_segment, master_shape in rows:
        exchange_segment = dhan_exchange_segment(master_exchange, master_segment)
        if exchange_segment is None:
            continue
        security_id = int(broker_token)
        if (exchange_segment, security_id) in chosen:
            continue
        chosen[(exchange_segment, security_id)] = {
            "exchange_segment": exchange_segment,
            "security_id": security_id,
            "identifier": f"{EXCHANGE_SEGMENT_NAMES[exchange_segment]}:{security_id}",
            "master_segment": f"{master_segment}/{master_shape}",
        }

    by_segment = {}
    for entry in chosen.values():
        by_segment.setdefault(entry["exchange_segment"], []).append(entry)
    instruments = []
    for exchange_segment in sorted(by_segment):
        segment_entries = by_segment[exchange_segment][:per_segment]
        for entry in segment_entries:
            instruments.append(entry)
    return instruments


def capture_ticks(instruments, seconds):
    """
    Open one live feed connection, collect whatever it sends, and decode it.

    Dhan may or may not send a snapshot of every subscribed instrument immediately after a subscription is accepted; whether it does is one of the open questions this run settles. Outside market hours the capture can come back empty, and the caller must treat that as an inconclusive run rather than a passed one.

    Args:
        instruments (list[dict]): The instruments to subscribe to, as select_verification_instruments returns them.
        seconds (float): How long to stay connected before closing.

    Returns:
        tuple: A (client_id, access_token, ticks_by_key) triple, where ticks_by_key maps each (exchange_segment, security_id) pair to the most recently decoded tick for it.

    Raises:
        stream.dhan.credentials.DhanCredentialsError: If there is no usable client identifier or access token.
        stream.dhan.connection.DhanConnectionError: If the connection could not be established.
    """
    frames = []

    async def capture():
        """
        Hold one connection open for the requested time and let the callback collect frames.

        Returns:
            tuple: A (client_id, access_token) pair, returned so the caller can reuse the same credentials for the REST comparison.
        """
        client_id, access_token = websocket_credentials()
        feed_connection = DhanConnection(
            client_id=client_id,
            access_token=access_token,
            instruments=[(instrument["exchange_segment"], instrument["security_id"]) for instrument in instruments],
            on_frame=lambda arrival, frame: frames.append((arrival, frame)),
            mode=connection.MODE_FULL,
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
        return (client_id, access_token)

    client_id, access_token = asyncio.run(capture())

    ticks_by_key = {}
    for arrival, frame in frames:
        if len(frame) < packets.HEADER_LENGTH:
            continue
        for tick in decode_frame(frame, datetime.fromtimestamp(arrival / 1e9)):
            ticks_by_key[(tick["exchange_segment"], tick["security_id"])] = tick
    return (client_id, access_token, ticks_by_key)


def fetch_quotes(client_id, access_token, instruments):
    """
    Ask Dhan's REST quote endpoint what it thinks these instruments are worth.

    Args:
        client_id (str): The Dhan client identifier, sent as the client-id header.
        access_token (str): An access token issued today, sent as the access-token header.
        instruments (list[dict]): The instruments to price, as select_verification_instruments returns them.

    Returns:
        dict: The endpoint's data block, keyed by (wire segment name, security id). Instruments it declines to price are simply absent.

    Raises:
        requests.HTTPError: If the endpoint returned an error status.
    """
    wire_name_by_segment = {segment: wire_name for segment, wire_name in EXCHANGE_SEGMENT_NAMES.items()}

    quotes = {}
    for start in range(0, len(instruments), QUOTE_BATCH_SIZE):
        batch = instruments[start:start + QUOTE_BATCH_SIZE]
        body = {}
        for instrument in batch:
            wire_name = wire_name_by_segment[instrument["exchange_segment"]]
            body.setdefault(wire_name, [])
            body[wire_name].append(instrument["security_id"])

        if start > 0:
            time.sleep(QUOTE_REQUEST_PAUSE_SECONDS)
        response = requests.post(
            QUOTE_ENDPOINT,
            json=body,
            headers={
                "access-token": access_token,
                "client-id": client_id,
                "Accept": "application/json",
            },
            timeout=30,
        )
        response.raise_for_status()
        for wire_name, segment_data in response.json().get("data", {}).items():
            for security_id, quote in segment_data.items():
                quotes[(wire_name, int(security_id))] = quote
    return quotes


def compare_tick_to_quote(tick, quote):
    """
    Compare one decoded tick against Dhan's own quote for the same instrument.

    Prices are divided by the tick's own divisor before comparing, which is what makes this a real test of the divisor rather than only of the field offsets. Quantities, volume and open interest are compared as they are, since no divisor applies to them.

    Args:
        tick (dict): A decoded tick from stream.dhan.packets.
        quote (dict): One instrument's entry from the quote endpoint's data block.

    Returns:
        tuple: A (compared_count, disagreements) pair, where disagreements is a list of readable strings describing each value that did not match.
    """
    divisor = tick["price_divisor"]
    compared = 0
    disagreements = []

    ohlc = quote.get("ohlc") or {}
    values = [
        ("last_price", tick.get("last_price"), quote.get("last_price"), True),
        ("open_price", tick.get("open_price"), ohlc.get("open"), True),
        ("high_price", tick.get("high_price"), ohlc.get("high"), True),
        ("low_price", tick.get("low_price"), ohlc.get("low"), True),
        ("close_price", tick.get("close_price"), ohlc.get("close"), True),
        ("volume_traded", tick.get("volume_traded"), quote.get("volume"), False),
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


def implied_scale_ratios(instruments, ticks_by_key, quotes):
    """
    Measure what price scale the wire really carries, segment by segment.

    Dhan documents no price divisor, so this is the check that settles it, the same way Zerodha's NSE Commodity divisor was settled. Each instrument's stored close price, or its last price when the close has not arrived, is turned back into rupees and divided by the REST quote's price. A median ratio of one means the wire carries rupees, which the decoder's conversion to paise assumes; a median of one hundred or one hundredth would mean the wire carries a different scale and the divisor table must change.

    Args:
        instruments (list[dict]): The instruments that were compared, as select_verification_instruments returns them.
        ticks_by_key (dict): Decoded ticks keyed by (exchange_segment, security_id), as capture_ticks returns them.
        quotes (dict): REST quotes keyed by (wire segment name, security id), as fetch_quotes returns them.

    Returns:
        dict: One entry per exchange segment with a nonzero ratio sample, mapping the segment number to the median ratio for it.
    """
    wire_name_by_segment = {segment: wire_name for segment, wire_name in EXCHANGE_SEGMENT_NAMES.items()}
    ratios_by_segment = {}
    for instrument in instruments:
        key = (instrument["exchange_segment"], instrument["security_id"])
        tick = ticks_by_key.get(key)
        quote = quotes.get((wire_name_by_segment[instrument["exchange_segment"]], instrument["security_id"]))
        if tick is None or quote is None:
            continue
        their_price = quote.get("ohlc", {}).get("close") or quote.get("last_price")
        our_price = tick.get("close_price") or tick.get("last_price")
        if not our_price or not their_price or float(their_price) == 0:
            continue
        ratio = (our_price / tick["price_divisor"]) / float(their_price)
        ratios_by_segment.setdefault(instrument["exchange_segment"], []).append(ratio)

    medians = {}
    for exchange_segment, ratios in ratios_by_segment.items():
        medians[exchange_segment] = statistics.median(ratios)
    return medians


def run_against_rest(per_segment, seconds):
    """
    Check decoded websocket ticks against Dhan's own REST quotes for the same instruments.

    This is the check the synthetic ones cannot replace. Those prove the parser agrees with this file's own idea of the format, since every byte they read was written here; this one uses the broker as the oracle, so it catches a field that both the parser and the synthetic checks are wrong about in the same direction.

    Args:
        per_segment (int): How many instruments to take from each Dhan exchange segment.
        seconds (float): How long to hold the websocket connection open.

    Returns:
        int: The number of instruments that disagreed with the quote endpoint.

    Raises:
        stream.dhan.credentials.DhanCredentialsError: If there is no usable client identifier or access token.
        requests.HTTPError: If the quote endpoint returned an error status.
    """
    engine = create_engine(postgres_configuration["connection_string"])
    instruments = select_verification_instruments(engine, per_segment)
    print(f"Checking {len(instruments)} instruments across {len({i['exchange_segment'] for i in instruments})} Dhan segments against Dhan's quote endpoint.")
    print()

    client_id, access_token, ticks_by_key = capture_ticks(instruments, seconds)
    if not ticks_by_key:
        print("  NOTE  the websocket delivered no ticks at all; outside market hours that is the expected answer, and during a session it would mean Dhan sent no snapshot on subscribe")
        print("        run this again during market hours")
        return 0

    quotes = fetch_quotes(client_id, access_token, instruments)

    total_compared = 0
    disagreeing_instruments = 0
    unquotable = 0
    undelivered = 0

    for instrument in instruments:
        key = (instrument["exchange_segment"], instrument["security_id"])
        tick = ticks_by_key.get(key)
        quote = quotes.get((EXCHANGE_SEGMENT_NAMES[instrument["exchange_segment"]], instrument["security_id"]))
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
            print(f"  ok        {instrument['identifier']:24s} segment {tick['exchange_segment']:>2d} {compared:>3d} values")

    print()
    scale_medians = implied_scale_ratios(instruments, ticks_by_key, quotes)
    for exchange_segment in sorted(scale_medians):
        median = scale_medians[exchange_segment]
        marker = "ok " if abs(median - 1.0) < 0.1 else "BAD"
        print(f"  {marker} implied scale for segment {exchange_segment:>2d} ({EXCHANGE_SEGMENT_NAMES[exchange_segment]}): median ratio {median:.4f}")
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
    Parse the command line and run the requested checks.

    Returns:
        None.

    Raises:
        SystemExit: Always, with status 1 when any check failed and 0 otherwise.
    """
    parser = argparse.ArgumentParser(description="Check that Dhan binary frames are decoded correctly.")
    parser.add_argument("--synthetic", action="store_true", help="Run the byte-level checks, which need no network.")
    parser.add_argument("--depth", action="store_true", help="Open a real depth socket and report what arrives; needs market hours and credentials.")
    parser.add_argument("--against-rest", action="store_true", help="Compare decoded websocket ticks against Dhan's own REST quotes; needs market hours and credentials.")
    parser.add_argument("--per-segment", type=int, default=3, help="How many instruments to take from each Dhan segment for --against-rest.")
    parser.add_argument("--depth-level", type=int, default=20, choices=(20, 200), help="Which depth socket to open in --depth mode, twenty levels or two hundred levels.")
    parser.add_argument("--instrument", action="append", help="An instrument to subscribe as SEGMENT:SECURITY_ID, for example NSE_EQ:1333; repeat for more; the two hundred level socket takes exactly one.")
    parser.add_argument("--seconds", type=float, default=30.0, help="How long to hold a live socket open.")
    arguments = parser.parse_args()

    if arguments.depth and not arguments.instrument:
        parser.error("--depth needs at least one --instrument SEGMENT:SECURITY_ID")

    if arguments.depth:
        failures = run_depth(arguments)
        raise SystemExit(1 if failures else 0)

    if not arguments.synthetic and not arguments.against_rest:
        parser.error("nothing to do: pass --synthetic, --against-rest, or both")

    failures = 0
    if arguments.synthetic:
        failures = failures + run_synthetic()
    if arguments.against_rest:
        if arguments.synthetic:
            print()
        failures = failures + run_against_rest(arguments.per_segment, arguments.seconds)

    raise SystemExit(1 if failures else 0)

    failures = run_synthetic()
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()