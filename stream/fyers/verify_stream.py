"""
Checks that Fyers' frames are being decoded correctly.

The synthetic checks in this module build frames byte by byte from known values and assert that every field comes back exactly, which needs no network and no market hours. They exist because the two Fyers feeds fail in two completely different ways and neither failure is loud.

The quote feed is positional, so a wrong field order is the whole risk: it produces plausible numbers in the wrong places, and swapping the day's open with its high looks like nothing at all. It is also stateful in a way no other broker's feed is, because an update packet identifies its instrument by a number that only an earlier snapshot gave meaning to, so the checks pin that a topic table is built, is used, is not crossed between instruments, and is not carried across a session.

The depth feed is Protocol Buffers, so the risk is the opposite: the structure is self-describing and cannot be misaligned, but a hand-written reader can disagree with the schema. The golden frames here were encoded by Fyers' own generated code from their published schema and are stored as bytes, so every run pins this project's reader against the official encoder without the client library needing to be installed.

Run with: python3 -m stream.fyers.verify_stream --synthetic

The --against-rest mode is the oracle check: it captures live websocket ticks for a spread of instruments, asks Fyers' own REST quote endpoint what the same instruments are worth, and compares every value the two share. It also measures the implied price scale exchange by exchange, which is what settles whether the snapshot's `multiplier` or its `precision` is the real divisor. The decoder currently reads the precision, and that reading is a considered guess until this check has run against a live market.

Run with: python3 -m stream.fyers.verify_stream --against-rest --per-exchange 3 --seconds 12

The REST endpoint takes fifty symbols per call against a limit of ten calls a second and two hundred a minute, and the account is blocked for the rest of the day after three breaches of the per-minute limit, so the oracle paces itself deliberately rather than going as fast as it can.
"""

import argparse
import asyncio
import statistics
import struct
import time
from datetime import datetime

import requests
from sqlalchemy import create_engine, text as sql_text

from stream.fyers import connection, depth_packets, packets
from stream.fyers.connection import FyersConnection
from stream.fyers.credentials import websocket_credentials, authorization_header_value
from utilities.configuration import postgres_configuration

ARRIVAL_TIME = datetime(2026, 9, 6, 10, 30, 0)

QUOTE_ENDPOINT = "https://api-t1.fyers.in/data/quotes"
SYMBOLS_PER_QUOTE_REQUEST = 50
QUOTE_REQUEST_PAUSE_SECONDS = 1.0
VERIFICATION_TOLERANCE = 0.011

SNAPSHOT_FRAME = bytes.fromhex(
    "080612c5010a114e53453a4e4946545932354d415246555412af012a730a040888e32d12"
    "0408dfd3421a120a0508d2cb9801120308c8011a02080922001a140a0508ebcb98011203"
    "08c9011a02080a2202080122110a0508a0cb9801120208641a020805220022130a050887"
    "cb9801120208651a0208062202080122130a0508eeca9801120208661a02080722020802"
    "320608c0bdefd4063a0608c1bdefd406420f31303131323530333132333435363748cd83"
    "0650015a114e53453a4e4946545932354d41524655541801"
)

DIFFERENCE_FRAME = bytes.fromhex(
    "080612400a114e53453a4e4946545932354d4152465554122b2a1622140a0508bcca9801"
    "12030889061a020803220208015a114e53453a4e4946545932354d4152465554"
)

ERROR_FRAME = bytes.fromhex(
    "0808220e696e76616c69642073796d626f6c2801"
)

NEGATIVE_PRICE_FRAME = bytes.fromhex(
    "12250a054e53453a59121c2a1322110a0b08c79fffffffffffffff01120022005a054e53"
    "453a59"
)

SCRIP_SNAPSHOT_VALUES = [
    60640,
    3045212,
    1690953622,
    1690953623,
    2081,
    903,
    60640,
    60645,
    5,
    749960,
    1092063,
    60820,
    12345,
    60585,
    61050,
    70000,
    50000,
    55000,
    66000,
    60985,
    62020,
]

INDEX_SNAPSHOT_VALUES = [
    1975025,
    1968040,
    1690953622,
    1977500,
    1970100,
    1972000,
]

DEPTH_SNAPSHOT_VALUES = (
    [60625, 60620, 60615, 60610, 60605]
    + [60630, 60635, 60640, 60645, 60650]
    + [20, 902, 111, 110, 0]
    + [282, 568, 2910, 1676, 2981]
    + [1, 3, 2, 2, 0]
    + [4, 2, 12, 9, 17]
)


def build_snapshot_packet(topic_identifier, topic_name, values, multiplier=100, price_precision=2, strings=("NSE", "2885", "SBIN")):
    """
    Build one snapshot packet, the kind that names its topic and carries every field.

    Args:
        topic_identifier (int): The identifier the packet introduces the topic under.
        topic_name (str): The topic name, for example "sf|nse_cm|2885".
        values (list): One value per positional field, None for a field the wire reports as absent.
        multiplier (int): The multiplier the snapshot carries.
        price_precision (int): The price precision the snapshot carries.
        strings (tuple): The three trailing strings, which are the exchange, the exchange token and the symbol.

    Returns:
        bytes: The packet, including its leading kind byte.
    """
    packet = bytearray()
    packet.append(packets.PACKET_KIND_SNAPSHOT)
    packet.extend(struct.pack("<H", topic_identifier))
    packet.append(len(topic_name))
    packet.extend(topic_name.encode("ascii"))
    packet.append(len(values))
    for value in values:
        if value is None:
            packet.extend(struct.pack(">i", packets.ABSENT_VALUE))
        else:
            packet.extend(struct.pack(">i", value))
    packet.extend(b"\x00\x00")
    packet.extend(struct.pack(">H", multiplier))
    packet.append(price_precision)
    for text in strings:
        packet.append(len(text))
        packet.extend(text.encode("ascii"))
    return bytes(packet)


def build_update_packet(topic_identifier, values):
    """
    Build one update packet, the kind that carries a topic identifier and no name.

    Args:
        topic_identifier (int): The identifier of the topic being updated.
        values (list): One value per positional field, None for a field the wire reports as absent.

    Returns:
        bytes: The packet, including its leading kind byte.
    """
    packet = bytearray()
    packet.append(packets.PACKET_KIND_UPDATE)
    packet.extend(struct.pack("<H", topic_identifier))
    packet.append(len(values))
    for value in values:
        if value is None:
            packet.extend(struct.pack(">i", packets.ABSENT_VALUE))
        else:
            packet.extend(struct.pack(">i", value))
    return bytes(packet)


def build_data_frame(packet_list, message_number=7):
    """
    Wrap packets in the market data frame that carries them.

    Args:
        packet_list (list[bytes]): The packets to carry, each including its kind byte.
        message_number (int): The message number the frame declares.

    Returns:
        bytes: The complete frame.
    """
    body = bytearray()
    body.extend(struct.pack(">I", message_number))
    body.extend(struct.pack(">H", len(packet_list)))
    for packet in packet_list:
        body.extend(packet)

    frame = bytearray()
    frame.extend(struct.pack(">H", len(body) + 1))
    frame.append(packets.RESPONSE_TYPE_DATA_FEED)
    frame.extend(body)
    return bytes(frame)


def check_field_lists_are_pinned_literally():
    """
    The positional field lists are exactly these names in exactly this order.

    Every other check reads the field lists out of the decoder and compares against them, so all of them move together if a list is reordered and none of them can notice. This check writes the expected order out in full, so it is the only thing standing between a reordered list and a silent, plausible mislabelling of every field that moved.

    The names here were transcribed from Fyers' own client library and must not be changed to match a modified decoder. If this check fails, the decoder is wrong until the wire is shown to have changed.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []

    expected_scrip = [
        "last_price",
        "volume_traded",
        "last_trade_time",
        "exchange_timestamp",
        "touchline_bid_quantity",
        "touchline_ask_quantity",
        "touchline_bid_price",
        "touchline_ask_price",
        "last_traded_quantity",
        "total_buy_quantity",
        "total_sell_quantity",
        "average_traded_price",
        "open_interest",
        "low_price",
        "high_price",
        "yearly_high_price",
        "yearly_low_price",
        "lower_circuit_price",
        "upper_circuit_price",
        "open_price",
        "close_price",
    ]
    expected_index = [
        "last_price",
        "close_price",
        "exchange_timestamp",
        "high_price",
        "low_price",
        "open_price",
    ]
    expected_depth = [
        "bid_prices",
        "ask_prices",
        "bid_quantities",
        "ask_quantities",
        "bid_orders",
        "ask_orders",
    ]

    named_lists = [
        ("SCRIP_FIELD_NAMES", packets.SCRIP_FIELD_NAMES, expected_scrip),
        ("INDEX_FIELD_NAMES", packets.INDEX_FIELD_NAMES, expected_index),
        ("DEPTH_FIELD_NAMES", packets.DEPTH_FIELD_NAMES, expected_depth),
    ]
    for list_name, actual, expected in named_lists:
        if list(actual) != expected:
            failures.append(f"{list_name} is {list(actual)!r}")
            failures.append(f"{' ' * len(list_name)}  expected {expected!r}")

    expected_segments = {
        "1010": "nse_cm",
        "1011": "nse_fo",
        "1012": "cde_fo",
        "1020": "nse_com",
        "1120": "mcx_fo",
        "1210": "bse_cm",
        "1211": "bse_fo",
        "1212": "bcs_fo",
    }
    if packets.SEGMENT_NAMES_BY_TOKEN_PREFIX != expected_segments:
        failures.append(f"the segment table is {packets.SEGMENT_NAMES_BY_TOKEN_PREFIX!r}")

    pinned_constants = [
        ("PACKET_KIND_SNAPSHOT", packets.PACKET_KIND_SNAPSHOT, 83),
        ("PACKET_KIND_UPDATE", packets.PACKET_KIND_UPDATE, 85),
        ("PACKET_KIND_LITE_UPDATE", packets.PACKET_KIND_LITE_UPDATE, 76),
        ("ABSENT_VALUE", packets.ABSENT_VALUE, -2147483648),
        ("RESPONSE_TYPE_DATA_FEED", packets.RESPONSE_TYPE_DATA_FEED, 6),
        ("RESPONSE_TYPE_AUTHENTICATION", packets.RESPONSE_TYPE_AUTHENTICATION, 1),
        ("DEPTH_LEVELS_PER_SIDE", packets.DEPTH_LEVELS_PER_SIDE, 5),
        ("PACKET_COUNT_OFFSET", packets.PACKET_COUNT_OFFSET, 7),
        ("FIRST_PACKET_OFFSET", packets.FIRST_PACKET_OFFSET, 9),
    ]
    for constant_name, actual, expected in pinned_constants:
        if actual != expected:
            failures.append(f"{constant_name} is {actual!r}, expected {expected!r}")

    for prefix, expected_names in (("sf", expected_scrip), ("if", expected_index), ("dp", expected_depth)):
        if list(packets.field_names_for_prefix(prefix)) != expected_names:
            failures.append(f"topic prefix {prefix!r} is read against the wrong field list")
    return failures


def check_short_frames_decode_to_nothing():
    """
    A frame too short to carry a header, or carrying a type that is not market data, decodes to nothing.

    The connection driver reads the authentication, subscription and mode replies for itself, so the decoder must ignore them rather than try to read packets out of them.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    for frame in (b"", b"\x00", b"\x00\x09"):
        if packets.decode_frame(frame, ARRIVAL_TIME) != []:
            failures.append(f"a {len(frame)} byte frame decoded to something")
        if packets.frame_packet_count(frame) != 0:
            failures.append(f"a {len(frame)} byte frame counted a packet")

    authentication_reply = connection.build_request(packets.RESPONSE_TYPE_AUTHENTICATION, [(1, b"K")])
    if packets.decode_frame(authentication_reply, ARRIVAL_TIME) != []:
        failures.append("an authentication reply decoded to a tick")
    if packets.frame_packet_count(authentication_reply) != 0:
        failures.append("an authentication reply counted a packet")
    return failures


def check_snapshot_round_trips_every_field():
    """
    Every one of the twenty one positional scrip fields comes back under the right name.

    This is the check that a reordered field list has to fail. The values are deliberately all different, so a swap of any two shows up rather than being masked by two fields that happen to be equal.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    frame = build_data_frame([build_snapshot_packet(41, "sf|nse_cm|2885", SCRIP_SNAPSHOT_VALUES)])
    decoded = packets.decode_frame(frame, ARRIVAL_TIME)
    if len(decoded) != 1:
        return [f"expected one partial tick, got {len(decoded)}"]

    tick = packets.TickAssembler().merge(decoded[0])
    for position, field_name in enumerate(packets.SCRIP_FIELD_NAMES):
        expected = SCRIP_SNAPSHOT_VALUES[position]
        if field_name in packets.TIMESTAMP_FIELDS:
            expected = packets.epoch_seconds_to_datetime(expected)
        if tick.get(field_name) != expected:
            failures.append(f"field {position} {field_name} came back as {tick.get(field_name)!r}, expected {expected!r}")

    if tick["topic_name"] != "sf|nse_cm|2885":
        failures.append(f"topic name came back as {tick['topic_name']!r}")
    if tick["segment"] != "nse_cm":
        failures.append(f"segment came back as {tick['segment']!r}")
    if tick["exchange_token"] != "2885":
        failures.append(f"exchange token came back as {tick['exchange_token']!r}")
    if tick["tick_mode"] != "quote":
        failures.append(f"tick mode came back as {tick['tick_mode']!r}")
    if not tick["tradable"]:
        failures.append("a tradeable scrip came back as not tradeable")
    return failures


def check_index_fields_are_not_scrip_fields():
    """
    An index snapshot is read against the index field list, not the scrip one.

    An index carries last price, previous close, feed time, high, low and open. A scrip carries last price and volume first. Reading an index with the scrip list puts the previous close where the volume belongs and every later field is wrong too, which produces numbers that all still look like prices.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    frame = build_data_frame([build_snapshot_packet(9, "if|nse_cm|Nifty Bank", INDEX_SNAPSHOT_VALUES, strings=("NSE", "26009", "NIFTYBANK"))])
    tick = packets.TickAssembler().merge(packets.decode_frame(frame, ARRIVAL_TIME)[0])

    for position, field_name in enumerate(packets.INDEX_FIELD_NAMES):
        expected = INDEX_SNAPSHOT_VALUES[position]
        if field_name in packets.TIMESTAMP_FIELDS:
            expected = packets.epoch_seconds_to_datetime(expected)
        if tick.get(field_name) != expected:
            failures.append(f"index field {position} {field_name} came back as {tick.get(field_name)!r}, expected {expected!r}")

    if tick["volume_traded"] is not None:
        failures.append("an index reported a traded volume, which means it was read with the scrip field list")
    if tick["tradable"]:
        failures.append("an index came back as tradeable")
    if tick["tick_mode"] != "index_quote":
        failures.append(f"an index came back in tick mode {tick['tick_mode']!r}")
    return failures


def check_absent_value_reads_as_missing():
    """
    The sentinel -2147483648 means the wire sent nothing, not that the price is that number.

    Reading it as a value would put a large negative number into a price field, and the assembler would then keep it for the rest of the day because a later packet that omits the field cannot overwrite it.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    values = list(SCRIP_SNAPSHOT_VALUES)
    values[12] = None
    values[15] = None
    frame = build_data_frame([build_snapshot_packet(41, "sf|nse_cm|2885", values)])
    tick = packets.TickAssembler().merge(packets.decode_frame(frame, ARRIVAL_TIME)[0])

    if tick["open_interest"] is not None:
        failures.append(f"an absent open interest came back as {tick['open_interest']!r}")
    if tick["yearly_high_price"] is not None:
        failures.append(f"an absent yearly high came back as {tick['yearly_high_price']!r}")
    if tick["last_price"] != SCRIP_SNAPSHOT_VALUES[0]:
        failures.append("a field beside an absent one was disturbed")
    return failures


def check_update_resolves_through_topic_table():
    """
    An update packet, which carries no topic name, is named by the snapshot that introduced its identifier.

    This is the property the whole quote feed rests on. An update carries a number and nothing else, and only the topic table can say what that number means.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    assembler = packets.TickAssembler()
    snapshot = build_data_frame([build_snapshot_packet(41, "sf|nse_cm|2885", SCRIP_SNAPSHOT_VALUES)])
    assembler.merge(packets.decode_frame(snapshot, ARRIVAL_TIME)[0])

    update = build_data_frame([build_update_packet(41, [61000])])
    tick = assembler.merge(packets.decode_frame(update, ARRIVAL_TIME)[0])
    if tick is None:
        return ["an update for a known topic decoded to nothing"]

    if tick["topic_name"] != "sf|nse_cm|2885":
        failures.append(f"an update resolved to topic {tick['topic_name']!r}")
    if tick["last_price"] != 61000:
        failures.append(f"the updated last price came back as {tick['last_price']!r}")
    return failures


def check_update_for_unknown_topic_decodes_to_nothing():
    """
    An update whose topic no snapshot has introduced is dropped rather than guessed at.

    A subscription's first update can overtake its snapshot. Dropping it loses one revision of a field the next update carries again; attributing it to some other instrument would be unrecoverable and would look like nothing was wrong.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    assembler = packets.TickAssembler()
    update = build_data_frame([build_update_packet(999, [61000])])
    decoded = packets.decode_frame(update, ARRIVAL_TIME)
    if len(decoded) != 1:
        failures.append("an update for an unknown topic did not decode to a partial tick")
    elif assembler.merge(decoded[0]) is not None:
        failures.append("an update for an unknown topic was merged into something")
    return failures


def check_assembler_keeps_unrepeated_fields():
    """
    A field an update does not carry keeps its last seen value rather than being reset.

    Fyers sends only what changed, so an assembler that replaced instead of updating would drop the day's open, high, low and volume on the first update after the snapshot.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    assembler = packets.TickAssembler()
    snapshot = build_data_frame([build_snapshot_packet(41, "sf|nse_cm|2885", SCRIP_SNAPSHOT_VALUES)])
    assembler.merge(packets.decode_frame(snapshot, ARRIVAL_TIME)[0])

    update = build_data_frame([build_update_packet(41, [61000])])
    tick = assembler.merge(packets.decode_frame(update, ARRIVAL_TIME)[0])

    for position, field_name in enumerate(packets.SCRIP_FIELD_NAMES):
        if position == 0:
            continue
        expected = SCRIP_SNAPSHOT_VALUES[position]
        if field_name in packets.TIMESTAMP_FIELDS:
            expected = packets.epoch_seconds_to_datetime(expected)
        if tick.get(field_name) != expected:
            failures.append(f"{field_name} was lost by an update that did not carry it: {tick.get(field_name)!r}")
    return failures


def check_assembler_keys_do_not_cross():
    """
    Two instruments on one connection keep separate state.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    assembler = packets.TickAssembler()
    first = build_data_frame([build_snapshot_packet(1, "sf|nse_cm|2885", SCRIP_SNAPSHOT_VALUES)])
    second_values = [value + 1 for value in SCRIP_SNAPSHOT_VALUES]
    second = build_data_frame([build_snapshot_packet(2, "sf|nse_cm|1594", second_values, strings=("NSE", "1594", "INFY"))])
    assembler.merge(packets.decode_frame(first, ARRIVAL_TIME)[0])
    assembler.merge(packets.decode_frame(second, ARRIVAL_TIME)[0])

    update = build_data_frame([build_update_packet(1, [99999])])
    first_tick = assembler.merge(packets.decode_frame(update, ARRIVAL_TIME)[0])
    if first_tick["last_price"] != 99999:
        failures.append("updating the first instrument did not take effect")

    second_snapshot = build_data_frame([build_update_packet(2, [None])])
    second_tick = assembler.merge(packets.decode_frame(second_snapshot, ARRIVAL_TIME)[0])
    if second_tick["last_price"] != second_values[0]:
        failures.append(f"the second instrument's last price became {second_tick['last_price']!r} after the first was updated")
    if len(assembler.known_instruments()) != 2:
        failures.append(f"the assembler tracked {len(assembler.known_instruments())} instruments, expected 2")
    return failures


def check_topic_table_does_not_survive_a_session():
    """
    A fresh assembler knows nothing, so a reconnected connection cannot inherit stale topic numbers.

    Fyers renumbers topics per connection. An assembler carried across a reconnection would attribute one instrument's prices to another, and nothing about the output would look wrong, which is why the connection driver reports a new session and the shard builds a new assembler.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    first_session = packets.TickAssembler()
    snapshot = build_data_frame([build_snapshot_packet(41, "sf|nse_cm|2885", SCRIP_SNAPSHOT_VALUES)])
    first_session.merge(packets.decode_frame(snapshot, ARRIVAL_TIME)[0])
    if first_session.known_topic(41) is None:
        failures.append("the first session did not learn its topic")

    second_session = packets.TickAssembler()
    if second_session.known_topic(41) is not None:
        failures.append("a new assembler already knew a topic from a previous session")
    update = build_data_frame([build_update_packet(41, [61000])])
    if second_session.merge(packets.decode_frame(update, ARRIVAL_TIME)[0]) is not None:
        failures.append("a new assembler resolved a topic number from a previous session")
    return failures


def check_depth_arrays_are_five():
    """
    The five level book keeps five places a side, zeros included.

    Trimming a level that reported zero would be an easy and wrong convenience: one instrument's book would then be a different length from another's, and a consumer indexing the third level would silently read the fourth.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    frame = build_data_frame([build_snapshot_packet(7, "dp|nse_cm|2885", DEPTH_SNAPSHOT_VALUES)])
    tick = packets.TickAssembler().merge(packets.decode_frame(frame, ARRIVAL_TIME)[0])

    expected_arrays = {
        "bid_prices": DEPTH_SNAPSHOT_VALUES[0:5],
        "ask_prices": DEPTH_SNAPSHOT_VALUES[5:10],
        "bid_quantities": DEPTH_SNAPSHOT_VALUES[10:15],
        "ask_quantities": DEPTH_SNAPSHOT_VALUES[15:20],
        "bid_orders": DEPTH_SNAPSHOT_VALUES[20:25],
        "ask_orders": DEPTH_SNAPSHOT_VALUES[25:30],
    }
    for field_name, expected in expected_arrays.items():
        actual = tick.get(field_name)
        if actual is None:
            failures.append(f"{field_name} was not decoded at all")
        elif len(actual) != packets.DEPTH_LEVELS_PER_SIDE:
            failures.append(f"{field_name} came back {len(actual)} long, expected {packets.DEPTH_LEVELS_PER_SIDE}")
        elif actual != expected:
            failures.append(f"{field_name} came back as {actual!r}, expected {expected!r}")

    if tick["tick_mode"] != "full":
        failures.append(f"a depth tick came back in tick mode {tick['tick_mode']!r}")
    return failures


def check_frame_packet_count():
    """
    The archive's packet counter agrees with the decoder about what a frame carries.

    A manifest that disagrees with the decoder is worse than no manifest, because the reconciliation looks like a real signal while being wrong.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    packet_list = [
        build_snapshot_packet(1, "sf|nse_cm|2885", SCRIP_SNAPSHOT_VALUES),
        build_update_packet(1, [61000]),
        build_snapshot_packet(7, "dp|nse_cm|2885", DEPTH_SNAPSHOT_VALUES),
    ]
    frame = build_data_frame(packet_list)
    counted = packets.frame_packet_count(frame)
    decoded = len(packets.decode_frame(frame, ARRIVAL_TIME))
    if counted != len(packet_list):
        failures.append(f"the counter said {counted} packets, the frame carries {len(packet_list)}")
    if decoded != len(packet_list):
        failures.append(f"the decoder produced {decoded} ticks, the frame carries {len(packet_list)}")
    return failures


def check_truncated_frame_stops_cleanly():
    """
    A frame cut off mid-packet yields what was readable and never raises.

    This runs inside the socket read loop, so one malformed frame must not take down a connection carrying thousands of instruments.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    frame = build_data_frame([
        build_snapshot_packet(1, "sf|nse_cm|2885", SCRIP_SNAPSHOT_VALUES),
        build_snapshot_packet(2, "sf|nse_cm|1594", SCRIP_SNAPSHOT_VALUES, strings=("NSE", "1594", "INFY")),
    ])
    for cut in range(1, len(frame)):
        try:
            packets.decode_frame(frame[:cut], ARRIVAL_TIME)
        except Exception as error:
            failures.append(f"a frame cut to {cut} bytes raised {type(error).__name__}: {error}")
            break
    return failures


def check_hsm_symbol_construction():
    """
    A subscription key is built from an instrument master row exactly as the wire expects it.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    cases = [
        ("101000000003045", "3045", "NSE:SBIN-EQ", packets.FEED_QUOTE, "sf|nse_cm|3045"),
        ("101000000003045", "3045", "NSE:SBIN-EQ", packets.FEED_DEPTH, "dp|nse_cm|3045"),
        ("101000000026009", "26009", "NSE:NIFTYBANK-INDEX", packets.FEED_QUOTE, "if|nse_cm|Nifty Bank"),
        ("101000000026009", "26009", "NSE:NIFTYBANK-INDEX", packets.FEED_DEPTH, None),
        ("112026100483079", "483079", "MCX:GOLD26OCTFUT", packets.FEED_QUOTE, "sf|mcx_fo|483079"),
        ("999900000000001", "1", "XXX:NOTHING", packets.FEED_QUOTE, None),
    ]
    for fytoken, scrip_code, symbol_ticker, feed, expected in cases:
        actual = packets.hsm_symbol_for_instrument(fytoken, scrip_code, symbol_ticker, feed)
        if actual != expected:
            failures.append(f"{symbol_ticker} on the {feed} feed built {actual!r}, expected {expected!r}")

    prefix, segment, exchange_token = packets.parse_topic_name("sf|nse_cm|3045")
    if (prefix, segment, exchange_token) != ("sf", "nse_cm", "3045"):
        failures.append(f"a topic name parsed back to {(prefix, segment, exchange_token)!r}")
    if packets.parse_topic_name("nonsense") != (None, None, None):
        failures.append("a malformed topic name did not parse to nothing")
    return failures


def check_wire_request_types():
    """
    The request messages carry the literal type bytes and layout the server expects.

    The builders and the decoder share this module's constants and would otherwise agree with themselves about a renamed one, so this pins the numbers rather than the names.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []

    authentication = connection.authentication_message("A" * 56)
    if authentication[2] != 1:
        failures.append(f"the authentication message declared type {authentication[2]}, expected 1")
    if authentication[3] != 4:
        failures.append(f"the authentication message declared {authentication[3]} fields, expected 4")
    declared_length = struct.unpack_from(">H", authentication, 0)[0]
    if declared_length != len(authentication) - 2:
        failures.append(f"the authentication message declared length {declared_length}, its body is {len(authentication) - 2}")

    mode = connection.mode_message("full", 11)
    if mode[2] != 12:
        failures.append(f"the mode message declared type {mode[2]}, expected 12")
    if struct.unpack_from(">Q", mode, 7)[0] != 1 << 11:
        failures.append("the mode message did not set the channel as a bit mask")
    if mode[-1] != 70:
        failures.append(f"full mode sent byte {mode[-1]}, expected 70")
    if connection.mode_message("lite", 11)[-1] != 76:
        failures.append("lite mode did not send byte 76")

    subscribe = connection.subscribe_message(["sf|nse_cm|3045", "if|nse_cm|Nifty Bank"], 11)
    if subscribe[2] != 4:
        failures.append(f"the subscribe message declared type {subscribe[2]}, expected 4")
    payload_length = struct.unpack_from(">H", subscribe, 5)[0]
    payload = subscribe[7:7 + payload_length]
    if struct.unpack_from(">H", payload, 0)[0] != 2:
        failures.append("the subscribe message did not declare two scrips")
    if subscribe[-1] != 11:
        failures.append(f"the subscribe message put channel {subscribe[-1]} last, expected 11")

    if connection.unsubscribe_message(["sf|nse_cm|3045"], 11)[2] != 5:
        failures.append("the unsubscribe message did not declare type 5")

    acknowledgement = connection.acknowledgement_message(123456)
    if len(acknowledgement) != 11:
        failures.append(f"the acknowledgement message is {len(acknowledgement)} bytes, expected 11")
    if acknowledgement[2] != 3:
        failures.append(f"the acknowledgement message declared type {acknowledgement[2]}, expected 3")
    if struct.unpack_from(">I", acknowledgement, 7)[0] != 123456:
        failures.append("the acknowledgement message did not carry the message number at offset 7")

    if connection.KEEP_ALIVE_FRAME != bytes([0, 1, 11]):
        failures.append(f"the keep-alive frame is {connection.KEEP_ALIVE_FRAME!r}, expected b'\\x00\\x01\\x0b'")
    return failures


def check_authentication_reply_parsing():
    """
    The authentication reply's status and acknowledgement interval are read from the right offsets.

    The interval matters as much as the status: a connection that never acknowledges is eventually stopped being fed, and the silence looks exactly like a dropped subscription.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    accepted = connection.build_request(packets.RESPONSE_TYPE_AUTHENTICATION, [(1, b"K"), (2, struct.pack(">I", 500))])
    status, interval = connection.read_authentication_reply(accepted)
    if status != "K":
        failures.append(f"an accepted reply read as status {status!r}")
    if interval != 500:
        failures.append(f"an accepted reply read an acknowledgement interval of {interval!r}, expected 500")

    refused = connection.build_request(packets.RESPONSE_TYPE_AUTHENTICATION, [(1, b"E"), (2, struct.pack(">I", 500))])
    status, _ = connection.read_authentication_reply(refused)
    if status == "K":
        failures.append("a refused reply read as accepted")

    status, interval = connection.read_authentication_reply(build_data_frame([]))
    if status is not None or interval is not None:
        failures.append("a market data frame was read as an authentication reply")
    return failures


def check_message_number_is_read_for_acknowledgement():
    """
    The message number an acknowledgement has to quote is read from the frame that carried it.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    frame = build_data_frame([build_snapshot_packet(1, "sf|nse_cm|2885", SCRIP_SNAPSHOT_VALUES)], message_number=4242)
    if packets.frame_message_number(frame) != 4242:
        failures.append(f"the message number read as {packets.frame_message_number(frame)!r}, expected 4242")
    if packets.frame_message_number(connection.build_request(packets.RESPONSE_TYPE_AUTHENTICATION, [(1, b"K")])) is not None:
        failures.append("a non-data frame reported a message number")
    return failures


def check_segment_table_covers_the_instrument_master():
    """
    Every segment prefix the decoder knows maps to a name, and the two index tables are self-consistent.

    The instrument master is not read here, because the synthetic checks must run with no database. The capacity probe reports any token whose key could not be built, which is where a genuinely new segment would surface.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    for prefix, segment in packets.SEGMENT_NAMES_BY_TOKEN_PREFIX.items():
        if len(prefix) != 4 or not prefix.isdigit():
            failures.append(f"segment prefix {prefix!r} is not four digits")
        if not segment:
            failures.append(f"segment prefix {prefix!r} maps to an empty name")
        if packets.segment_for_token(prefix + "000000123") != segment:
            failures.append(f"segment_for_token disagreed with the table for prefix {prefix!r}")

    if packets.segment_for_token("9999000000001") is not None:
        failures.append("an unknown token prefix returned a segment")
    if packets.index_name_for_ticker("NSE:NIFTYBANK-INDEX") != "Nifty Bank":
        failures.append("a known index did not resolve through the table")
    if packets.index_name_for_ticker("NSE:NOTATABLE-INDEX") != "NOTATABLE":
        failures.append("an unknown index did not fall back to its ticker symbol")
    if not packets.is_index_ticker("NSE:NIFTYBANK-INDEX") or packets.is_index_ticker("NSE:SBIN-EQ"):
        failures.append("index tickers were not recognised")
    return failures


def check_depth_golden_snapshot():
    """
    A frame encoded by Fyers' own generated code decodes here to exactly the values it was built from.

    This is what pins the hand-written protobuf reader against the published schema. The bytes were produced once by the official encoder and stored, so the check needs neither the client library nor a network.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    ticks = depth_packets.decode_frame(SNAPSHOT_FRAME, ARRIVAL_TIME)
    if len(ticks) != 1:
        return [f"the golden snapshot decoded to {len(ticks)} ticks, expected 1"]

    tick = ticks[0]
    expectations = {
        "ticker": "NSE:NIFTY25MARFUT",
        "token": "101125031234567",
        "sequence_number": 98765,
        "is_snapshot": True,
        "exchange_timestamp": depth_packets.epoch_seconds_to_datetime(1788600000),
        "send_timestamp": depth_packets.epoch_seconds_to_datetime(1788600001),
    }
    for field_name, expected in expectations.items():
        if tick.get(field_name) != expected:
            failures.append(f"{field_name} came back as {tick.get(field_name)!r}, expected {expected!r}")

    depth = tick["depth"]
    if depth["total_buy_quantity"] != 749960:
        failures.append(f"total buy quantity came back as {depth['total_buy_quantity']!r}")
    if depth["total_sell_quantity"] != 1092063:
        failures.append(f"total sell quantity came back as {depth['total_sell_quantity']!r}")

    expected_bids = [
        {"price": 2500000, "quantity": 100, "orders": 5, "number": 0},
        {"price": 2499975, "quantity": 101, "orders": 6, "number": 1},
        {"price": 2499950, "quantity": 102, "orders": 7, "number": 2},
    ]
    if depth["bids"] != expected_bids:
        failures.append(f"bids came back as {depth['bids']!r}")
    expected_asks = [
        {"price": 2500050, "quantity": 200, "orders": 9, "number": 0},
        {"price": 2500075, "quantity": 201, "orders": 10, "number": 1},
    ]
    if depth["asks"] != expected_asks:
        failures.append(f"asks came back as {depth['asks']!r}")

    if depth_packets.frame_packet_count(SNAPSHOT_FRAME) != 1:
        failures.append("the golden snapshot counted the wrong number of packets")
    return failures


def check_depth_difference_updates_one_level():
    """
    A difference changes only the level it names and a later snapshot clears what came before.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    assembler = depth_packets.DepthAssembler()
    book = assembler.merge(depth_packets.decode_frame(SNAPSHOT_FRAME, ARRIVAL_TIME)[0])
    if book["bid_prices"][:3] != [2500000, 2499975, 2499950]:
        failures.append(f"the snapshot assembled bids {book['bid_prices'][:3]!r}")

    book = assembler.merge(depth_packets.decode_frame(DIFFERENCE_FRAME, ARRIVAL_TIME)[0])
    if book["bid_prices"][1] != 2499900:
        failures.append(f"the difference did not change level 1, which reads {book['bid_prices'][1]!r}")
    if book["bid_quantities"][1] != 777:
        failures.append(f"the difference did not change level 1's quantity, which reads {book['bid_quantities'][1]!r}")
    if book["bid_prices"][0] != 2500000 or book["bid_prices"][2] != 2499950:
        failures.append("the difference disturbed a level it did not name")
    if book["ask_prices"][0] != 2500050:
        failures.append("the difference disturbed the other side of the book")

    for side in ("bid", "ask"):
        for kind in ("prices", "quantities", "orders"):
            array = book[f"{side}_{kind}"]
            if len(array) != depth_packets.DEPTH_LEVELS:
                failures.append(f"{side}_{kind} is {len(array)} long, expected {depth_packets.DEPTH_LEVELS}")

    reset = depth_packets.DepthAssembler()
    reset.merge(depth_packets.decode_frame(SNAPSHOT_FRAME, ARRIVAL_TIME)[0])
    fresh = reset.merge(depth_packets.decode_frame(SNAPSHOT_FRAME, ARRIVAL_TIME)[0])
    if fresh["bid_prices"][3] is not None:
        failures.append("a second snapshot did not clear levels the first had filled")
    return failures


def check_depth_error_frame():
    """
    An error frame carries no instruments, counts no packets, and yields its text.

    A rejected symbol is reported this way and nothing else surfaces it: the connection stays healthy and the other symbols keep flowing.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    if depth_packets.decode_frame(ERROR_FRAME, ARRIVAL_TIME) != []:
        failures.append("an error frame decoded to a tick")
    if depth_packets.frame_packet_count(ERROR_FRAME) != 0:
        failures.append("an error frame counted a packet")
    if depth_packets.frame_error_text(ERROR_FRAME) != "invalid symbol":
        failures.append(f"the error text read as {depth_packets.frame_error_text(ERROR_FRAME)!r}")
    if depth_packets.frame_error_text(SNAPSHOT_FRAME) is not None:
        failures.append("a data frame reported an error")
    return failures


def check_depth_negative_price_and_empty_wrapper():
    """
    A negative price survives and a wrapper that is present but empty reads as zero.

    Protocol Buffers writes a negative int64 as ten bytes of two's complement rather than zigzag, so a price read without that conversion comes back as roughly eighteen quintillion. An empty wrapper means the value really is zero, which is different from the field being absent.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    ticks = depth_packets.decode_frame(NEGATIVE_PRICE_FRAME, ARRIVAL_TIME)
    if len(ticks) != 1:
        return [f"the golden negative price frame decoded to {len(ticks)} ticks"]

    level = ticks[0]["depth"]["bids"][0]
    if level["price"] != -12345:
        failures.append(f"a negative price came back as {level['price']!r}, expected -12345")
    if level["quantity"] != 0:
        failures.append(f"an empty quantity wrapper came back as {level['quantity']!r}, expected 0")
    if level["orders"] is not None:
        failures.append(f"an absent orders wrapper came back as {level['orders']!r}, expected None")
    return failures


def check_depth_truncated_frame_stops_cleanly():
    """
    A protobuf frame cut off anywhere yields what was readable and never raises.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    for cut in range(1, len(SNAPSHOT_FRAME)):
        try:
            depth_packets.decode_frame(SNAPSHOT_FRAME[:cut], ARRIVAL_TIME)
        except Exception as error:
            failures.append(f"a depth frame cut to {cut} bytes raised {type(error).__name__}: {error}")
            break
    return failures


def check_depth_subscription_messages():
    """
    The tick-by-tick requests are exactly the JSON Fyers documents.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    import json

    from stream.fyers import depth_connection

    failures = []
    documented_subscribe = {
        "type": 1,
        "data": {
            "subs": 1,
            "symbols": ["NSE:IOC25FEBFUT"],
            "mode": "depth",
            "channel": "1",
        },
    }
    actual = json.loads(depth_connection.subscription_message(["NSE:IOC25FEBFUT"], True, "1"))
    if actual != documented_subscribe:
        failures.append(f"the subscribe message is {actual!r}")

    documented_unsubscribe = dict(documented_subscribe)
    documented_unsubscribe["data"] = dict(documented_subscribe["data"])
    documented_unsubscribe["data"]["subs"] = -1
    actual = json.loads(depth_connection.subscription_message(["NSE:IOC25FEBFUT"], False, "1"))
    if actual != documented_unsubscribe:
        failures.append(f"the unsubscribe message is {actual!r}")

    documented_switch = {
        "type": 2,
        "data": {
            "resumeChannels": ["1"],
            "pauseChannels": [],
        },
    }
    actual = json.loads(depth_connection.switch_channel_message(["1"], []))
    if actual != documented_switch:
        failures.append(f"the switch channel message is {actual!r}")
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
        "last_price": 42690,
        "open_price": 42500,
        "high_price": 42800,
        "low_price": 42400,
        "close_price": 42520,
        "volume_traded": 3045212,
        "average_traded_price": 42600,
        "price_divisor": 100,
    }
    quote = {
        "lp": 426.90,
        "open_price": 425.00,
        "high_price": 428.00,
        "low_price": 424.00,
        "prev_close_price": 425.20,
        "volume": 3045212,
        "atp": 426.00,
    }
    agreements, disagreements = compare_tick_to_quote(tick, quote)
    if disagreements:
        failures.append(f"an exact match reported disagreements: {disagreements!r}")
    if len(agreements) != 7:
        failures.append(f"an exact match compared {len(agreements)} fields, expected 7")

    wrong = dict(tick)
    wrong["last_price"] = 4269000
    _, disagreements = compare_tick_to_quote(wrong, quote)
    if not disagreements:
        failures.append("a price out by a factor of a hundred was not reported")
    return failures


def check_implied_scale_ratio():
    """
    The implied scale measurement recovers a divisor it was not told.

    This is the check that settles the open question about Fyers' prices. If the wire's precision is not the real divisor, this measurement is what says so, so it has to be right before the live run rather than after it.

    Returns:
        list[str]: The failures found, empty when the check passed.
    """
    failures = []
    ticks_by_key = {
        "NSE:SBIN-EQ": {"last_price": 4269000, "price_divisor": 100},
        "NSE:INFY-EQ": {"last_price": 15005000, "price_divisor": 100},
    }
    quotes = {
        "NSE:SBIN-EQ": {"lp": 426.90},
        "NSE:INFY-EQ": {"lp": 1500.50},
    }
    ratios = implied_scale_ratios(ticks_by_key, quotes)
    if not ratios:
        return ["the implied scale measurement produced nothing"]
    median = statistics.median(ratios)
    if abs(median - 10000) > 1:
        failures.append(f"the implied divisor measured {median}, expected 10000")
    return failures


SYNTHETIC_CHECKS = [
    check_field_lists_are_pinned_literally,
    check_short_frames_decode_to_nothing,
    check_snapshot_round_trips_every_field,
    check_index_fields_are_not_scrip_fields,
    check_absent_value_reads_as_missing,
    check_update_resolves_through_topic_table,
    check_update_for_unknown_topic_decodes_to_nothing,
    check_assembler_keeps_unrepeated_fields,
    check_assembler_keys_do_not_cross,
    check_topic_table_does_not_survive_a_session,
    check_depth_arrays_are_five,
    check_frame_packet_count,
    check_truncated_frame_stops_cleanly,
    check_hsm_symbol_construction,
    check_wire_request_types,
    check_authentication_reply_parsing,
    check_message_number_is_read_for_acknowledgement,
    check_segment_table_covers_the_instrument_master,
    check_depth_golden_snapshot,
    check_depth_difference_updates_one_level,
    check_depth_error_frame,
    check_depth_negative_price_and_empty_wrapper,
    check_depth_truncated_frame_stops_cleanly,
    check_depth_subscription_messages,
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

    A spread matters more than a large sample. The price divisor is the thing under test and it is a per instrument property on this feed, so a hundred NSE equities would settle one segment and say nothing about the others, while three from each segment settles all of them.

    Args:
        engine: A SQLAlchemy engine for the tradingmachine database.
        per_exchange (int): How many instruments to take from each segment.

    Returns:
        list[dict]: One dict per instrument with keys "fytoken", "scrip_code", "symbol_ticker" and "segment".

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the instrument tables cannot be read.
    """
    with engine.connect() as database_connection:
        rows = database_connection.execute(sql_text(
            "SELECT f.fytoken, f.scrip_code, f.symbol_ticker "
            "FROM instruments.fyers f "
            "JOIN instruments.broker_mappings b ON b.broker_token = f.fytoken AND b.broker = 'fyers' "
            "JOIN instruments.master m ON m.instrument_id = b.instrument_id "
            "WHERE f.download_date = (SELECT max(download_date) FROM instruments.fyers) "
            "  AND b.mapping_date = (SELECT max(mapping_date) FROM instruments.broker_mappings WHERE broker = 'fyers') "
            "  AND (m.expiry_date IS NULL OR m.expiry_date > CURRENT_DATE)"
        )).all()

    by_segment = {}
    for row in rows:
        segment = packets.segment_for_token(row.fytoken)
        if segment is None:
            continue
        if segment not in by_segment:
            by_segment[segment] = []
        if len(by_segment[segment]) >= per_exchange:
            continue
        by_segment[segment].append({
            "fytoken": row.fytoken,
            "scrip_code": row.scrip_code,
            "symbol_ticker": row.symbol_ticker,
            "segment": segment,
        })

    chosen = []
    for segment in sorted(by_segment):
        chosen.extend(by_segment[segment])
    return chosen


async def capture_ticks_async(hsm_key, instruments, seconds, feed):
    """
    Open one connection, subscribe the chosen instruments and collect what arrives.

    Args:
        hsm_key (str): The hsm_key claim decoded out of today's access token.
        instruments (list[dict]): The instruments to subscribe.
        seconds (float): How long to keep the connection open.
        feed (str): Which feed to subscribe, "quote" or "depth".

    Returns:
        dict: The most recent complete tick per topic name.

    Raises:
        stream.fyers.connection.FyersAuthenticationError: If Fyers rejected the credentials.
    """
    assembler = packets.TickAssembler()
    ticks_by_topic = {}

    def on_session_start():
        assembler.__init__()
        ticks_by_topic.clear()

    def on_frame(arrival_time_nanoseconds, frame):
        arrival_time = datetime.fromtimestamp(arrival_time_nanoseconds / 1_000_000_000)
        for partial in packets.decode_frame(frame, arrival_time):
            tick = assembler.merge(partial)
            if tick is not None:
                ticks_by_topic[tick["topic_name"]] = tick

    subscription_keys = []
    for instrument in instruments:
        key = packets.hsm_symbol_for_instrument(instrument["fytoken"], instrument["scrip_code"], instrument["symbol_ticker"], feed)
        if key is not None:
            subscription_keys.append(key)

    live_connection = FyersConnection(
        hsm_key=hsm_key,
        instruments=subscription_keys,
        on_frame=on_frame,
        mode=connection.MODE_FULL,
        on_session_start=on_session_start,
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

    return ticks_by_topic


def fetch_quotes(authorization, symbol_tickers):
    """
    Ask Fyers' REST endpoint what a batch of instruments is worth.

    The endpoint takes fifty symbols per call against ten calls a second and two hundred a minute, and the account is blocked for the rest of the day after three breaches of the per-minute limit, so this pauses between calls rather than going as fast as it can.

    Args:
        authorization (str): The Authorization header value, which is the application identifier and the access token joined by a colon.
        symbol_tickers (list[str]): Fyers symbol tickers to ask about.

    Returns:
        dict: The value block per symbol ticker, for the symbols the endpoint answered for.

    Raises:
        requests.RequestException: If the endpoint cannot be reached.
    """
    quotes = {}
    for start in range(0, len(symbol_tickers), SYMBOLS_PER_QUOTE_REQUEST):
        batch = symbol_tickers[start:start + SYMBOLS_PER_QUOTE_REQUEST]
        response = requests.get(
            QUOTE_ENDPOINT,
            params={"symbols": ",".join(batch)},
            headers={"Authorization": authorization},
            timeout=30,
        )
        payload = response.json()
        if payload.get("s") != "ok":
            print(f"  the quote endpoint answered {payload.get('s')!r}: {payload.get('message')!r}")
            continue
        for entry in payload.get("d", []):
            if entry.get("s") != "ok":
                continue
            values = entry.get("v")
            if isinstance(values, dict):
                quotes[entry.get("n")] = values
        time.sleep(QUOTE_REQUEST_PAUSE_SECONDS)
    return quotes


COMPARABLE_FIELDS = [
    ("last_price", "lp"),
    ("open_price", "open_price"),
    ("high_price", "high_price"),
    ("low_price", "low_price"),
    ("close_price", "prev_close_price"),
    ("average_traded_price", "atp"),
]


def compare_tick_to_quote(tick, quote):
    """
    Compare one decoded tick against the REST endpoint's view of the same instrument.

    Prices are divided by the tick's own divisor before comparing, which is the whole point: a divisor that is wrong shows up here as every price being out by the same factor, rather than as one field looking odd.

    Args:
        tick (dict): One complete tick from the assembler.
        quote (dict): The value block the REST endpoint returned for the same instrument.

    Returns:
        tuple: An (agreements, disagreements) pair of lists, each holding one description per field compared.
    """
    agreements = []
    disagreements = []
    divisor = tick.get("price_divisor") or 1

    for tick_field, quote_field in COMPARABLE_FIELDS:
        tick_value = tick.get(tick_field)
        quote_value = quote.get(quote_field)
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


def implied_scale_ratios(ticks_by_key, quotes):
    """
    Measure what divisor the wire's prices actually imply, ignoring what the decoder assumed.

    This is what settles whether the snapshot's price precision or its multiplier is the real divisor. Dividing the raw wire price by the REST price gives the divisor directly, so a decoder reading the wrong one shows up as a clean factor rather than as noise.

    Args:
        ticks_by_key (dict): One complete tick per key, carrying raw wire prices.
        quotes (dict): The REST value block per the same keys.

    Returns:
        list[float]: One implied divisor per instrument that could be measured.
    """
    ratios = []
    for key, tick in ticks_by_key.items():
        quote = quotes.get(key)
        if quote is None:
            continue
        wire_price = tick.get("last_price")
        rest_price = quote.get("lp")
        if not wire_price or not rest_price:
            continue
        ratios.append(wire_price / rest_price)
    return ratios


def run_against_rest(per_exchange, seconds, feed):
    """
    Capture live ticks, ask the REST endpoint about the same instruments, and compare.

    Args:
        per_exchange (int): How many instruments to take from each segment.
        seconds (float): How long to hold the websocket open.
        feed (str): Which feed to subscribe, "quote" or "depth".

    Returns:
        int: 0 when every instrument that could be compared agreed, 1 otherwise.

    Raises:
        stream.fyers.credentials.FyersCredentialsError: If the credentials are missing or expired.
    """
    application_identifier, access_token, hsm_key = websocket_credentials()
    authorization = authorization_header_value(application_identifier, access_token)

    engine = create_engine(postgres_configuration["connection_string"])
    instruments = select_verification_instruments(engine, per_exchange)
    print(f"comparing {len(instruments)} instruments across {len({instrument['segment'] for instrument in instruments})} segments")

    ticks_by_topic = asyncio.run(capture_ticks_async(hsm_key, instruments, seconds, feed))
    print(f"captured ticks for {len(ticks_by_topic)} of {len(instruments)} instruments in {seconds:.0f} seconds")

    ticks_by_ticker = {}
    for instrument in instruments:
        key = packets.hsm_symbol_for_instrument(instrument["fytoken"], instrument["scrip_code"], instrument["symbol_ticker"], feed)
        if key is not None and key in ticks_by_topic:
            ticks_by_ticker[instrument["symbol_ticker"]] = ticks_by_topic[key]

    missing = [instrument["symbol_ticker"] for instrument in instruments if instrument["symbol_ticker"] not in ticks_by_ticker]
    if missing:
        print(f"no tick arrived for {len(missing)}: {', '.join(missing[:10])}{' ...' if len(missing) > 10 else ''}")

    quotes = fetch_quotes(authorization, sorted(ticks_by_ticker))
    print(f"the REST endpoint answered for {len(quotes)} of them")
    print()

    total_disagreements = 0
    for ticker in sorted(ticks_by_ticker):
        quote = quotes.get(ticker)
        if quote is None:
            continue
        agreements, disagreements = compare_tick_to_quote(ticks_by_ticker[ticker], quote)
        if disagreements:
            total_disagreements = total_disagreements + len(disagreements)
            print(f"MISMATCH {ticker}")
            for disagreement in disagreements:
                print(f"           {disagreement}")
        else:
            print(f"ok       {ticker}  ({len(agreements)} fields agree)")

    print()
    print("implied price divisor by segment")
    by_segment = {}
    for instrument in instruments:
        ticker = instrument["symbol_ticker"]
        if ticker not in ticks_by_ticker or ticker not in quotes:
            continue
        by_segment.setdefault(instrument["segment"], {})[ticker] = ticks_by_ticker[ticker]

    for segment in sorted(by_segment):
        ratios = implied_scale_ratios(by_segment[segment], quotes)
        if not ratios:
            continue
        sample = next(iter(by_segment[segment].values()))
        print(
            f"  {segment:10} measured {statistics.median(ratios):12,.2f}   "
            f"decoder used {sample.get('price_divisor')}   "
            f"multiplier {sample.get('multiplier')}   precision {sample.get('price_precision')}   "
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
    parser = argparse.ArgumentParser(description="Verify the Fyers stream decoders.")
    parser.add_argument("--synthetic", action="store_true", help="Run the offline checks, which need no network.")
    parser.add_argument("--against-rest", action="store_true", help="Compare live websocket ticks against Fyers' own REST quotes.")
    parser.add_argument("--per-exchange", type=int, default=3, help="How many instruments to take from each segment.")
    parser.add_argument("--seconds", type=float, default=12.0, help="How long to hold the websocket open.")
    parser.add_argument("--feed", choices=[packets.FEED_QUOTE, packets.FEED_DEPTH], default=packets.FEED_QUOTE, help="Which feed to subscribe.")
    arguments = parser.parse_args()

    if not arguments.synthetic and not arguments.against_rest:
        parser.error("choose --synthetic, --against-rest, or both.")

    status = 0
    if arguments.synthetic:
        status = run_synthetic()
    if arguments.against_rest:
        print()
        status = max(status, run_against_rest(arguments.per_exchange, arguments.seconds, arguments.feed))
    raise SystemExit(status)


if __name__ == "__main__":
    main()
