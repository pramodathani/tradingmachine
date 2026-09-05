"""
Decoding of Flattrade's JSON touchline and depth frames.

Every Flattrade market data message is one JSON object carried in one websocket text frame. A subscription is answered with one acknowledgement per scrip, `tk` on the touchline feed and `dk` on the depth feed, which carries the day's full snapshot, and every later message, `tf` and `df`, carries only the fields that changed. So decoding happens in two pieces: `decode_frame` turns one frame into a partial tick holding just the fields the wire sent, and `TickAssembler` keeps the last seen value of every field per scrip and emits the complete tick.

Prices arrive as decimal strings and the snapshot tells the scrip's own price precision in `pp`, so each price is converted to a wire integer by multiplying by ten to the power of that precision. This follows the Zerodha decoder's rule, an integer price with a per tick divisor, rather than the Dhan decoder's fixed hundred, because currency scrips tick in fractions of a paisa and a fixed divisor would misstate them. The implied scale cross check against REST is what finally settles the precision segment by segment, the same way it settled Zerodha's and Dhan's scales.

This module knows nothing about sockets, shards, Redis or the database, exactly like its Zerodha and Dhan counterparts. It imports `orjson` and `datetime` and nothing else, so it can be tested completely on bytes alone.
"""

from datetime import datetime

import orjson

MESSAGE_TYPE_KEY = "t"
MESSAGE_TYPE_AUTHENTICATION_ACK = "ak"
MESSAGE_TYPE_TOUCHLINE_ACK = "tk"
MESSAGE_TYPE_TOUCHLINE_UPDATE = "tf"
MESSAGE_TYPE_DEPTH_ACK = "dk"
MESSAGE_TYPE_DEPTH_UPDATE = "df"
MESSAGE_TYPE_UNSUBSCRIBE_TOUCHLINE_ACK = "uk"
MESSAGE_TYPE_UNSUBSCRIBE_DEPTH_ACK = "udk"
MESSAGE_TYPE_HEARTBEAT = "h"
MESSAGE_TYPE_HEARTBEAT_ACK = "hk"
MESSAGE_TYPE_ORDER_UPDATE = "o"
MESSAGE_TYPE_POSITION_UPDATE = "p"
MESSAGE_TYPE_AUTHENTICATION_NOT_OK = "Not_Ok"

MARKET_DATA_MESSAGE_TYPES = {
    MESSAGE_TYPE_TOUCHLINE_ACK,
    MESSAGE_TYPE_TOUCHLINE_UPDATE,
    MESSAGE_TYPE_DEPTH_ACK,
    MESSAGE_TYPE_DEPTH_UPDATE,
}

EXCHANGE_KEY = "e"
TOKEN_KEY = "tk"
PRICE_PRECISION_KEY = "pp"
LAST_PRICE_KEY = "lp"
VOLUME_TRADED_KEY = "v"
AVERAGE_TRADED_PRICE_KEY = "ap"
OPEN_PRICE_KEY = "o"
HIGH_PRICE_KEY = "h"
LOW_PRICE_KEY = "l"
CLOSE_PRICE_KEY = "c"
DEPTH_CLOSE_PRICE_KEY = "cp"
OPEN_INTEREST_KEY = "oi"
FEED_TIME_KEY = "ft"
LAST_TRADE_TIME_KEY = "ltt"
LAST_TRADED_QUANTITY_KEY = "ltq"
TOTAL_BUY_QUANTITY_KEY = "tbq"
TOTAL_SELL_QUANTITY_KEY = "tsq"

DEPTH_LEVELS_PER_SIDE = 5
BID_PRICE_KEYS = ["bp1", "bp2", "bp3", "bp4", "bp5"]
BID_QUANTITY_KEYS = ["bq1", "bq2", "bq3", "bq4", "bq5"]
BID_ORDER_KEYS = ["bo1", "bo2", "bo3", "bo4", "bo5"]
ASK_PRICE_KEYS = ["sp1", "sp2", "sp3", "sp4", "sp5"]
ASK_QUANTITY_KEYS = ["sq1", "sq2", "sq3", "sq4", "sq5"]
ASK_ORDER_KEYS = ["so1", "so2", "so3", "so4", "so5"]

DEFAULT_PRICE_PRECISION = 2
MAXIMUM_PLAUSIBLE_EPOCH_SECONDS = 4102444800

CONTRACT_FIELDS = (
    "exchange_timestamp",
    "last_trade_time",
    "last_price",
    "last_traded_quantity",
    "average_traded_price",
    "volume_traded",
    "total_buy_quantity",
    "total_sell_quantity",
    "open_interest",
    "open_interest_day_high",
    "open_interest_day_low",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "bid_quantities",
    "bid_prices",
    "bid_orders",
    "ask_quantities",
    "ask_prices",
    "ask_orders",
)


def parse_message(frame):
    """
    Parse one websocket frame into the JSON message it carries.

    Args:
        frame (bytes): One complete websocket frame as received, which on Flattrade is one JSON object.

    Returns:
        dict | None: The parsed message, or None when the frame is empty or not JSON. Parsing never raises, because this runs inside the socket read loop, where one malformed frame must not take down a connection carrying thousands of instruments.
    """
    try:
        message = orjson.loads(frame)
    except orjson.JSONDecodeError:
        return None
    if not isinstance(message, dict):
        return None
    return message


def message_type(frame):
    """
    Give the message type a frame declares in its `t` field.

    Args:
        frame (bytes): One complete websocket frame as received.

    Returns:
        str | None: The message type, for example "tk", or None when the frame carries none.
    """
    message = parse_message(frame)
    if message is None:
        return None
    message_type_value = message.get(MESSAGE_TYPE_KEY)
    if not isinstance(message_type_value, str):
        return None
    return message_type_value


def price_precision_value(message):
    """
    Give the price precision a message carries in its `pp` field.

    Args:
        message (dict): One parsed wire message.

    Returns:
        int | None: The price precision, or None when the message carries no `pp` field.
    """
    value = message.get(PRICE_PRECISION_KEY)
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def price_divisor(price_precision):
    """
    Give the number that turns this instrument's stored prices into rupees.

    Args:
        price_precision (int): The number of decimal places the instrument's prices are quoted to, from its snapshot's `pp` field.

    Returns:
        int: The divisor to apply to this tick's stored prices, which is ten to the power of the precision.
    """
    return 10 ** price_precision


def price_in_wire(price_value, price_precision):
    """
    Convert a wire price to a whole number of the instrument's smallest quoted unit.

    A currency scrip quoted to four decimals is stored as a number of 0.0001 rupee units, not paise, which is why the divisor is carried per tick rather than fixed at a hundred like Dhan's.

    Args:
        price_value (str | int | float | None): The price as it arrived on the wire, usually a decimal string.
        price_precision (int): The number of decimal places the instrument's prices are quoted to.

    Returns:
        int | None: The scaled price, or None when the wire sent no price at all. An empty string means the field was absent, not that the price was zero.
    """
    if price_value is None or price_value == "":
        return None
    try:
        return round(float(price_value) * 10 ** price_precision)
    except (TypeError, ValueError):
        return None


def integer_value(value):
    """
    Turn a wire quantity into an integer.

    Noren sends quantities and volumes as strings, and orjson turns numeric ones into numbers, so both forms are accepted. An empty string means the field was absent, not that the quantity was zero.

    Args:
        value (str | int | float | None): The quantity as it arrived on the wire.

    Returns:
        int | None: The quantity, or None when the wire sent nothing.
    """
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def epoch_seconds_to_datetime(epoch_seconds_value):
    """
    Turn an exchange timestamp into a datetime, rejecting the implausible ones.

    Noren sends these as strings, so string and number forms are both accepted. The exchange sends zero or a blank when it has no timestamp to give, and the ticks table is partitioned by time, so anything outside a sane range becomes no timestamp rather than a wrong one.

    Args:
        epoch_seconds_value (str | int | None): Seconds since the Unix epoch as they arrived on the wire.

    Returns:
        datetime.datetime | None: The corresponding local time, or None when the value is absent, zero, or outside the plausible range.
    """
    seconds = integer_value(epoch_seconds_value)
    if seconds is None or seconds <= 0:
        return None
    if seconds >= MAXIMUM_PLAUSIBLE_EPOCH_SECONDS:
        return None
    return datetime.fromtimestamp(seconds)


def time_of_day_to_datetime(value):
    """
    Turn a last trade time into a datetime, whatever form the wire used.

    The depth feed's `ltt` is documented only as the last trade time, with no format given. A number is read as seconds since the Unix epoch, and a value containing colons is read as a time of day on the day of arrival, which is the only date it could mean.

    Args:
        value (str | int | None): The last trade time as it arrived on the wire.

    Returns:
        datetime.datetime | None: The corresponding local time, or None when the value is absent or in no form this decoder understands.
    """
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return epoch_seconds_to_datetime(value)
    if ":" in str(value):
        try:
            hour, minute, second = (int(part) for part in str(value).split(":"))
        except ValueError:
            return None
        if hour < 0 or hour > 23 or minute < 0 or minute > 59 or second < 0 or second > 59:
            return None
        today = datetime.now()
        return today.replace(hour=hour, minute=minute, second=second, microsecond=0)
    return epoch_seconds_to_datetime(value)


def base_tick(message, arrival_time, tick_mode):
    """
    Build the identity part of a partial tick, the fields every message carries.

    Args:
        message (dict): One parsed wire message.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.
        tick_mode (str): Which feed the message belongs to, "quote" for touchline and "full" for depth.

    Returns:
        dict: The partial tick's identity fields, with the price precision included only when the message carries one.
    """
    tick = {
        "arrival_time": arrival_time,
        "exchange": message.get(EXCHANGE_KEY),
        "token": message.get(TOKEN_KEY),
        "price_divisor": price_divisor(price_precision_value(message) or DEFAULT_PRICE_PRECISION),
        "tick_mode": tick_mode,
        "tradable": True,
    }
    precision = price_precision_value(message)
    if precision is not None:
        tick["price_precision"] = precision
    return tick


def decode_touchline_message(message, arrival_time):
    """
    Decode one touchline message, `tk` or `tf`, into a partial tick.

    A `tk` acknowledgement carries the day's full snapshot and a `tf` update carries only the fields that changed, so this function maps whichever fields the message actually carries and leaves the rest to TickAssembler. The wire keys are Flattrade's own compact names: `lp` for the last price, `v` for volume, `o`, `h`, `l` and `c` for the day's prices, `ap` for the average traded price, `oi` for open interest and `ft` for the feed time. The touchline's top of book fields `bq1`, `bp1`, `sq1` and `sp1` are not mapped, because the depth feed reports the same book with five levels and one scrip must not carry two different shapes.

    Args:
        message (dict): One parsed touchline message.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        dict: The partial tick, holding the identity fields plus only the contract fields this message carried.
    """
    precision = price_precision_value(message) or DEFAULT_PRICE_PRECISION
    tick = base_tick(message, arrival_time, "quote")
    if FEED_TIME_KEY in message:
        tick["exchange_timestamp"] = epoch_seconds_to_datetime(message.get(FEED_TIME_KEY))
    if LAST_PRICE_KEY in message:
        tick["last_price"] = price_in_wire(message.get(LAST_PRICE_KEY), precision)
    if VOLUME_TRADED_KEY in message:
        tick["volume_traded"] = integer_value(message.get(VOLUME_TRADED_KEY))
    if AVERAGE_TRADED_PRICE_KEY in message:
        tick["average_traded_price"] = price_in_wire(message.get(AVERAGE_TRADED_PRICE_KEY), precision)
    if OPEN_PRICE_KEY in message:
        tick["open_price"] = price_in_wire(message.get(OPEN_PRICE_KEY), precision)
    if HIGH_PRICE_KEY in message:
        tick["high_price"] = price_in_wire(message.get(HIGH_PRICE_KEY), precision)
    if LOW_PRICE_KEY in message:
        tick["low_price"] = price_in_wire(message.get(LOW_PRICE_KEY), precision)
    if CLOSE_PRICE_KEY in message:
        tick["close_price"] = price_in_wire(message.get(CLOSE_PRICE_KEY), precision)
    if OPEN_INTEREST_KEY in message:
        tick["open_interest"] = integer_value(message.get(OPEN_INTEREST_KEY))
    return tick


def depth_side(message, price_keys, quantity_keys, order_keys, precision):
    """
    Read one side of a depth message's five levels into the three arrays the shared contract uses.

    Args:
        message (dict): One parsed depth message.
        price_keys (list[str]): The five wire keys of the side's prices, cheapest to deepest.
        quantity_keys (list[str]): The five wire keys of the side's quantities.
        order_keys (list[str]): The five wire keys of the side's order counts.
        precision (int): The price precision the message carries.

    Returns:
        tuple: The (quantities, prices, orders) triple of five element lists, zeros where the wire reports zero and None where the wire sent nothing at all.
    """
    quantities = []
    prices = []
    orders = []
    for level in range(DEPTH_LEVELS_PER_SIDE):
        quantities.append(integer_value(message.get(quantity_keys[level])))
        prices.append(price_in_wire(message.get(price_keys[level]), precision))
        orders.append(integer_value(message.get(order_keys[level])))
    return quantities, prices, orders


def decode_depth_message(message, arrival_time):
    """
    Decode one depth message, `dk` or `df`, into a partial tick.

    The depth acknowledgement carries the day's prices, the totals and five levels a side. The wire's `c` holds the previous day's close, the same quantity the Zerodha and Dhan decoders store as close_price, while `cp` repeats the wire's own close price idea and is left undecoded for the first live run to settle. The last trade time in `ltt` has no documented format, so time_of_day_to_datetime reads it either way.

    Args:
        message (dict): One parsed depth message.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        dict: The partial tick, with five element bid and ask arrays for every level the message carries.
    """
    precision = price_precision_value(message) or DEFAULT_PRICE_PRECISION
    tick = base_tick(message, arrival_time, "full")
    if FEED_TIME_KEY in message:
        tick["exchange_timestamp"] = epoch_seconds_to_datetime(message.get(FEED_TIME_KEY))
    if LAST_PRICE_KEY in message:
        tick["last_price"] = price_in_wire(message.get(LAST_PRICE_KEY), precision)
    if LAST_TRADED_QUANTITY_KEY in message:
        tick["last_traded_quantity"] = integer_value(message.get(LAST_TRADED_QUANTITY_KEY))
    if LAST_TRADE_TIME_KEY in message:
        tick["last_trade_time"] = time_of_day_to_datetime(message.get(LAST_TRADE_TIME_KEY))
    if AVERAGE_TRADED_PRICE_KEY in message:
        tick["average_traded_price"] = price_in_wire(message.get(AVERAGE_TRADED_PRICE_KEY), precision)
    if VOLUME_TRADED_KEY in message:
        tick["volume_traded"] = integer_value(message.get(VOLUME_TRADED_KEY))
    if TOTAL_BUY_QUANTITY_KEY in message:
        tick["total_buy_quantity"] = integer_value(message.get(TOTAL_BUY_QUANTITY_KEY))
    if TOTAL_SELL_QUANTITY_KEY in message:
        tick["total_sell_quantity"] = integer_value(message.get(TOTAL_SELL_QUANTITY_KEY))
    if OPEN_PRICE_KEY in message:
        tick["open_price"] = price_in_wire(message.get(OPEN_PRICE_KEY), precision)
    if HIGH_PRICE_KEY in message:
        tick["high_price"] = price_in_wire(message.get(HIGH_PRICE_KEY), precision)
    if LOW_PRICE_KEY in message:
        tick["low_price"] = price_in_wire(message.get(LOW_PRICE_KEY), precision)
    if CLOSE_PRICE_KEY in message:
        tick["close_price"] = price_in_wire(message.get(CLOSE_PRICE_KEY), precision)
    if OPEN_INTEREST_KEY in message:
        tick["open_interest"] = integer_value(message.get(OPEN_INTEREST_KEY))

    has_bid_levels = any(key in message for key in BID_QUANTITY_KEYS)
    has_ask_levels = any(key in message for key in ASK_QUANTITY_KEYS)
    if has_bid_levels:
        tick["bid_quantities"], tick["bid_prices"], tick["bid_orders"] = depth_side(message, BID_PRICE_KEYS, BID_QUANTITY_KEYS, BID_ORDER_KEYS, precision)
    if has_ask_levels:
        tick["ask_quantities"], tick["ask_prices"], tick["ask_orders"] = depth_side(message, ASK_PRICE_KEYS, ASK_QUANTITY_KEYS, ASK_ORDER_KEYS, precision)
    return tick


def decode_frame(frame, arrival_time):
    """
    Decode one websocket frame into the partial ticks it carries.

    Dispatch is by the message type in the `t` field. Touchline and depth messages decode to one partial tick each, and every other message type, the acknowledgements, the heartbeat exchange and the order and position updates, decodes to nothing at all, because none of them is market data. Raising instead of returning an empty list would be worse than useless here: this runs inside the socket read loop, so one malformed frame would take down a connection carrying thousands of instruments.

    Args:
        frame (bytes): One complete websocket frame as received.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        list[dict]: Zero or one partial tick, holding only the fields the wire actually sent.
    """
    message = parse_message(frame)
    if message is None:
        return []
    message_type_value = message.get(MESSAGE_TYPE_KEY)
    if message_type_value in (MESSAGE_TYPE_TOUCHLINE_ACK, MESSAGE_TYPE_TOUCHLINE_UPDATE):
        return [decode_touchline_message(message, arrival_time)]
    if message_type_value in (MESSAGE_TYPE_DEPTH_ACK, MESSAGE_TYPE_DEPTH_UPDATE):
        return [decode_depth_message(message, arrival_time)]
    return []


def frame_packet_count(frame):
    """
    Count the market data messages one websocket frame carries, for the archive manifest.

    One Flattrade frame carries one JSON message, so the count is one for a touchline or depth message and zero for everything else. Counting acknowledgements or heartbeat acknowledgements as packets would corrupt the manifest's reconciliation, and a frame that is not JSON at all carries nothing countable.

    Args:
        frame (bytes): One complete websocket frame as received.

    Returns:
        int: The number of market data messages the frame carries, which is zero or one.
    """
    return 1 if message_type(frame) in MARKET_DATA_MESSAGE_TYPES else 0


class TickAssembler:
    """
    Merges partial ticks into complete ticks, one instrument at a time.

    Flattrade's touchline and depth updates carry only the fields that changed since the last message, so no single message describes a scrip. The assembler keeps the last seen value of every contract field per (exchange, token), remembers each scrip's price precision from its acknowledgement, and returns the complete tick with None for every field the scrip has not reported yet.

    Attributes:
        ticks_by_key (dict): The last seen value of every field, keyed on (exchange, token).
        price_precisions (dict): Each scrip's price precision, keyed on (exchange, token).
    """

    def __init__(self):
        """
        Start with no instrument state at all.

        Returns:
            None.
        """
        self.ticks_by_key = {}
        self.price_precisions = {}

    def merge(self, tick):
        """
        Merge one partial tick into the scrip's state and return the complete tick.

        A field the message did not carry is left at its last seen value, and a field the scrip has never reported stays None rather than being invented as a zero. The partial tick's arrival time always wins, because it is the freshest fact about when this tick was read off the socket.

        Args:
            tick (dict): One partial tick from decode_frame.

        Returns:
            dict: The complete tick for this scrip, every contract field present.

        Raises:
            KeyError: If the tick carries no exchange or token to key it on.
        """
        key = (tick["exchange"], tick["token"])
        precision = tick.get("price_precision")
        if precision is not None:
            self.price_precisions[key] = precision

        stored = self.ticks_by_key.get(key)
        if stored is None:
            stored = {
                "exchange": tick["exchange"],
                "token": tick["token"],
                "tick_mode": None,
                "tradable": True,
                "price_divisor": price_divisor(self.price_precisions.get(key, DEFAULT_PRICE_PRECISION)),
            }
            for field in CONTRACT_FIELDS:
                stored[field] = None
            self.ticks_by_key[key] = stored

        for field, value in tick.items():
            if field == "price_precision":
                continue
            if value is not None:
                stored[field] = value
        stored["price_divisor"] = price_divisor(self.price_precisions.get(key, DEFAULT_PRICE_PRECISION))
        return dict(stored)

    def known_instruments(self):
        """
        List the scrips this assembler has state for.

        Returns:
            list[tuple]: One (exchange, token) pair per scrip seen so far.
        """
        return list(self.ticks_by_key)