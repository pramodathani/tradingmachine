"""
Decoding of Fyers' HSM binary market data frames.

Fyers publishes no wire format at all. Its documentation describes the `fyers_apiv3` client library and the shape of the data after that library has decoded it, and the only websocket URLs it names are the order socket and the tick-by-tick socket. Everything in this module was established by reading that library's source, which is a public package; nothing from it is imported, exactly as no other broker's client library is imported here.

A frame opens with a two byte big endian length and a one byte response type. Type 6 is market data and is the only type this module decodes; the rest are the authentication, subscription and mode acknowledgements, which the connection driver reads. A market data frame carries a four byte message number at offset 3, a two byte packet count at offset 7, and then that many packets from offset 9.

Each packet opens with a one byte kind, and the three kinds are not three shapes of the same thing. A snapshot, kind 83, names its topic and carries every field the instrument has. An update, kind 85, carries only a topic identifier and the changed values, and crucially does not repeat the topic name. A lite update, kind 76, carries a topic identifier and a single price.

That omission is the one thing about this feed that shapes everything else. An update packet is meaningless on its own: the number 41 in it identifies an instrument only to a reader that saw the snapshot which introduced topic 41 on the same connection. So `decode_frame` stays a pure function of bytes, the way every other broker's does, and returns partial ticks that carry the raw topic identifier; `TickAssembler` holds the topic table learned from snapshots and is what turns an identifier back into an instrument. A new connection starts a new table, because the broker renumbers topics per connection.

Fields are positional rather than named. A packet says how many values follow and they are read against a fixed list, so the lists here are the whole of the field naming and a reordered list silently mislabels every field it moves. `-2147483648` means the wire sent nothing for that field, not that the value is that number.

Prices are not converted here. Each instrument's snapshot carries a `multiplier` and a `precision` and both are reported alongside the raw integers, because the ticks table stores wire integers and applies the divisor in a view. Which of the two actually scales the price is settled by the cross-check against Fyers' own REST quotes, not guessed at here.

This module knows nothing about sockets, shards, Redis or the database, exactly like its Zerodha, Dhan, Flattrade and Shoonya counterparts. It imports `struct` and `datetime` and nothing else, so it can be tested completely on bytes alone.
"""

import struct
from datetime import datetime

FRAME_HEADER_STRUCT = struct.Struct(">HB")
MESSAGE_NUMBER_STRUCT = struct.Struct(">I")
PACKET_COUNT_STRUCT = struct.Struct(">H")
TOPIC_IDENTIFIER_STRUCT = struct.Struct("<H")
FIELD_VALUE_STRUCT = struct.Struct(">i")
MULTIPLIER_STRUCT = struct.Struct(">H")

RESPONSE_TYPE_AUTHENTICATION = 1
RESPONSE_TYPE_SUBSCRIBE = 4
RESPONSE_TYPE_UNSUBSCRIBE = 5
RESPONSE_TYPE_DATA_FEED = 6
RESPONSE_TYPE_CHANNEL_RESUME = 7
RESPONSE_TYPE_CHANNEL_PAUSE = 8
RESPONSE_TYPE_MODE = 12

PACKET_KIND_SNAPSHOT = 83
PACKET_KIND_UPDATE = 85
PACKET_KIND_LITE_UPDATE = 76

ABSENT_VALUE = -2147483648

FRAME_HEADER_LENGTH = 3
PACKET_COUNT_OFFSET = 7
FIRST_PACKET_OFFSET = 9
SNAPSHOT_TRAILING_SKIP_BYTES = 2
SNAPSHOT_STRING_FIELDS = [
    "wire_exchange",
    "wire_exchange_token",
    "wire_symbol",
]

TOPIC_PREFIX_SCRIP = "sf"
TOPIC_PREFIX_INDEX = "if"
TOPIC_PREFIX_DEPTH = "dp"

FEED_QUOTE = "quote"
FEED_DEPTH = "depth"

MAXIMUM_PLAUSIBLE_EPOCH_SECONDS = 4102444800

DEPTH_LEVELS_PER_SIDE = 5
DEFAULT_PRICE_PRECISION = 2

SCRIP_FIELD_NAMES = [
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

INDEX_FIELD_NAMES = [
    "last_price",
    "close_price",
    "exchange_timestamp",
    "high_price",
    "low_price",
    "open_price",
]

DEPTH_FIELD_NAMES = [
    "bid_prices",
    "ask_prices",
    "bid_quantities",
    "ask_quantities",
    "bid_orders",
    "ask_orders",
]

TIMESTAMP_FIELDS = {
    "last_trade_time",
    "exchange_timestamp",
}

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
    "touchline_bid_quantity",
    "touchline_bid_price",
    "touchline_ask_quantity",
    "touchline_ask_price",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "yearly_high_price",
    "yearly_low_price",
    "lower_circuit_price",
    "upper_circuit_price",
    "bid_quantities",
    "bid_prices",
    "bid_orders",
    "ask_quantities",
    "ask_prices",
    "ask_orders",
)

SEGMENT_NAMES_BY_TOKEN_PREFIX = {
    "1010": "nse_cm",
    "1011": "nse_fo",
    "1012": "cde_fo",
    "1020": "nse_com",
    "1120": "mcx_fo",
    "1210": "bse_cm",
    "1211": "bse_fo",
    "1212": "bcs_fo",
}

INDEX_NAMES_BY_TICKER = {
    "BSE:100-INDEX": "BSE100",
    "BSE:100LARGECAPTMC-INDEX": "LCTMCI",
    "BSE:150MIDCAP-INDEX": "MID150",
    "BSE:200-INDEX": "BSE200",
    "BSE:250LARGEMIDCAP-INDEX": "LMI250",
    "BSE:250SMALLCAP-INDEX": "SML250",
    "BSE:400MIDSMALLCAP-INDEX": "MSL400",
    "BSE:500-INDEX": "BSE500",
    "BSE:ALLCAP-INDEX": "ALLCAP",
    "BSE:AUTO-INDEX": "AUTO",
    "BSE:BANKEX-INDEX": "BANKEX",
    "BSE:BASMTR-INDEX": "BASMTR",
    "BSE:BHRT22-INDEX": "BHRT22",
    "BSE:CARBONEX-INDEX": "CARBON",
    "BSE:CD-INDEX": "BSE CD",
    "BSE:CDGS-INDEX": "CDGS",
    "BSE:CG-INDEX": "BSE CG",
    "BSE:CPSE-INDEX": "CPSE",
    "BSE:DFRG-INDEX": "DFRGRI",
    "BSE:DIVIDENDSTABILITY-INDEX": "BSEDSI",
    "BSE:ENERGY-INDEX": "ENERGY",
    "BSE:ENHANCEDVALUE-INDEX": "BSEEVI",
    "BSE:ESG100-INDEX": "ESG100",
    "BSE:FIN-INDEX": "FIN",
    "BSE:FMC-INDEX": "BSEFMC",
    "BSE:GREENEX-INDEX": "GREENX",
    "BSE:HC-INDEX": "BSE HC",
    "BSE:INDIAMANUFACTURING-INDEX": "MFG",
    "BSE:INDSTR-INDEX": "INDSTR",
    "BSE:INFRA-INDEX": "INFRA",
    "BSE:IPO-INDEX": "BSEIPO",
    "BSE:IT-INDEX": "BSE IT",
    "BSE:LOWVOLATILITY-INDEX": "BSELVI",
    "BSE:LRGCAP-INDEX": "LRGCAP",
    "BSE:METAL-INDEX": "METAL",
    "BSE:MIDCAP-INDEX": "MIDCAP",
    "BSE:MIDSEL-INDEX": "MIDSEL",
    "BSE:MOMENTUM-INDEX": "BSEMOI",
    "BSE:OILGAS-INDEX": "OILGAS",
    "BSE:POWER-INDEX": "POWER",
    "BSE:PRIVATEBANKS-INDEX": "BSEPBI",
    "BSE:PSU-INDEX": "BSEPSU",
    "BSE:QUALITY-INDEX": "BSEQUI",
    "BSE:REALTY-INDEX": "REALTY",
    "BSE:SENSEX-INDEX": "SENSEX",
    "BSE:SME IPO-INDEX": "SMEIPO",
    "BSE:SMLCAP-INDEX": "SMLCAP",
    "BSE:SMLSEL-INDEX": "SMLSEL",
    "BSE:SNSX50-INDEX": "SNSX50",
    "BSE:SNXT50-INDEX": "SNXT50",
    "BSE:TECK-INDEX": "TECK",
    "BSE:TELCOM-INDEX": "TELCOM",
    "BSE:UTILS-INDEX": "UTILS",
    "NSE:BHARATBOND-APR30-INDEX": "BHARATBOND-APR30",
    "NSE:BHARATBOND-APR31-INDEX": "BHARATBOND-APR31",
    "NSE:BHARATBOND-APR32-INDEX": "BHARATBOND-APR32",
    "NSE:BHARATBOND-APR33-INDEX": "BHARATBOND-APR33",
    "NSE:FINNIFTY-INDEX": "Nifty Fin Service",
    "NSE:HANGSENG BEES-NAV-INDEX": "HangSeng BeES-NAV",
    "NSE:INDIAVIX-INDEX": "India VIX",
    "NSE:MIDCPNIFTY-INDEX": "NIFTY MID SELECT",
    "NSE:NIFTY100 EQL WGT-INDEX": "NIFTY100 EQL Wgt",
    "NSE:NIFTY100 LOWVOL30-INDEX": "NIFTY100 LowVol30",
    "NSE:NIFTY100-INDEX": "Nifty 100",
    "NSE:NIFTY100ALPHA30-INDEX": "Nifty100 Alpha 30",
    "NSE:NIFTY100ENHESG-INDEX": "Nifty100 Enh ESG",
    "NSE:NIFTY100ESG-INDEX": "NIFTY100 ESG",
    "NSE:NIFTY100ESGSECLDR-INDEX": "Nifty100ESGSecLdr",
    "NSE:NIFTY100LIQ15-INDEX": "Nifty100 Liq 15",
    "NSE:NIFTY200-INDEX": "Nifty 200",
    "NSE:NIFTY200MOMENTM30-INDEX": "Nifty200Momentm30",
    "NSE:NIFTY200QUALTY30-INDEX": "NIFTY200 QUALTY30",
    "NSE:NIFTY200VALUE30-INDEX": "Nifty200 Value 30",
    "NSE:NIFTY50 EQL WGT-INDEX": "NIFTY50 EQL Wgt",
    "NSE:NIFTY50-INDEX": "Nifty 50",
    "NSE:NIFTY500-INDEX": "Nifty 500",
    "NSE:NIFTY500EW-INDEX": "Nifty500 EW",
    "NSE:NIFTY500LMSEQL-INDEX": "Nifty500 LMS Eql",
    "NSE:NIFTY500LOWVOL50-INDEX": "Nifty500 LowVol50",
    "NSE:NIFTY500MOMENTM50-INDEX": "Nifty500Momentm50",
    "NSE:NIFTY500MULTICAP-INDEX": "NIFTY500 MULTICAP",
    "NSE:NIFTY500QLTY50-INDEX": "Nifty500 Qlty50",
    "NSE:NIFTY500SHARIAH-INDEX": "Nifty500 Shariah",
    "NSE:NIFTY500VALUE50-INDEX": "Nifty500 Value 50",
    "NSE:NIFTY50DIVPOINT-INDEX": "Nifty50 Div Point",
    "NSE:NIFTY50PR1XINV-INDEX": "Nifty50 PR 1x Inv",
    "NSE:NIFTY50PR2XLEV-INDEX": "Nifty50 PR 2x Lev",
    "NSE:NIFTY50SHARIAH-INDEX": "Nifty50 Shariah",
    "NSE:NIFTY50TR1XINV-INDEX": "Nifty50 TR 1x Inv",
    "NSE:NIFTY50TR2XLEV-INDEX": "Nifty50 TR 2x Lev",
    "NSE:NIFTY50VALUE20-INDEX": "Nifty50 Value 20",
    "NSE:NIFTYALPHA50-INDEX": "NIFTY Alpha 50",
    "NSE:NIFTYALPHALOWVOL-INDEX": "NIFTY AlphaLowVol",
    "NSE:NIFTYAQL30-INDEX": "Nifty AQL 30",
    "NSE:NIFTYAQLV30-INDEX": "Nifty AQLV 30",
    "NSE:NIFTYAUTO-INDEX": "Nifty Auto",
    "NSE:NIFTYBANK-INDEX": "Nifty Bank",
    "NSE:NIFTYCAPITALMKT-INDEX": "Nifty Capital Mkt",
    "NSE:NIFTYCOMMODITIES-INDEX": "Nifty Commodities",
    "NSE:NIFTYCONSRDURBL-INDEX": "NIFTY CONSR DURBL",
    "NSE:NIFTYCONSUMPTION-INDEX": "Nifty Consumption",
    "NSE:NIFTYCOREHOUSING-INDEX": "Nifty CoreHousing",
    "NSE:NIFTYCORPMAATR-INDEX": "Nifty Corp MAATR",
    "NSE:NIFTYCPSE-INDEX": "Nifty CPSE",
    "NSE:NIFTYDIVOPPS50-INDEX": "Nifty Div Opps 50",
    "NSE:NIFTYENERGY-INDEX": "Nifty Energy",
    "NSE:NIFTYEV-INDEX": "Nifty EV",
    "NSE:NIFTYFINSEREXBNK-INDEX": "Nifty FinSerExBnk",
    "NSE:NIFTYFINSRV2550-INDEX": "Nifty FinSrv25 50",
    "NSE:NIFTYFMCG-INDEX": "Nifty FMCG",
    "NSE:NIFTYGROWSECT15-INDEX": "Nifty GrowSect 15",
    "NSE:NIFTYGS10YR-INDEX": "Nifty GS 10Yr",
    "NSE:NIFTYGS10YRCLN-INDEX": "Nifty GS 10Yr Cln",
    "NSE:NIFTYGS1115YR-INDEX": "Nifty GS 11 15Yr",
    "NSE:NIFTYGS15YRPLUS-INDEX": "Nifty GS 15YrPlus",
    "NSE:NIFTYGS48YR-INDEX": "Nifty GS 4 8Yr",
    "NSE:NIFTYGS813YR-INDEX": "Nifty GS 8 13Yr",
    "NSE:NIFTYGSCOMPSITE-INDEX": "Nifty GS Compsite",
    "NSE:NIFTYHEALTHCARE-INDEX": "NIFTY HEALTHCARE",
    "NSE:NIFTYHIGHBETA50-INDEX": "Nifty HighBeta 50",
    "NSE:NIFTYHOUSING-INDEX": "Nifty Housing",
    "NSE:NIFTYINDDEFENCE-INDEX": "Nifty Ind Defence",
    "NSE:NIFTYINDDIGITAL-INDEX": "NIFTY IND DIGITAL",
    "NSE:NIFTYINDIAMFG-INDEX": "NIFTY INDIA MFG",
    "NSE:NIFTYINDTOURISM-INDEX": "Nifty Ind Tourism",
    "NSE:NIFTYINFRA-INDEX": "Nifty Infra",
    "NSE:NIFTYIPO-INDEX": "Nifty IPO",
    "NSE:NIFTYIT-INDEX": "Nifty IT",
    "NSE:NIFTYLARGEMID250-INDEX": "NIFTY LARGEMID250",
    "NSE:NIFTYLOWVOL50-INDEX": "Nifty Low Vol 50",
    "NSE:NIFTYM150QLTY50-INDEX": "NIFTY M150 QLTY50",
    "NSE:NIFTYMEDIA-INDEX": "Nifty Media",
    "NSE:NIFTYMETAL-INDEX": "Nifty Metal",
    "NSE:NIFTYMICROCAP250-INDEX": "NIFTY MICROCAP250",
    "NSE:NIFTYMIDCAP100-INDEX": "NIFTY MIDCAP 100",
    "NSE:NIFTYMIDCAP150-INDEX": "NIFTY MIDCAP 150",
    "NSE:NIFTYMIDCAP50-INDEX": "Nifty Midcap 50",
    "NSE:NIFTYMIDLIQ15-INDEX": "Nifty Mid Liq 15",
    "NSE:NIFTYMIDSML400-INDEX": "NIFTY MIDSML 400",
    "NSE:NIFTYMIDSMLHLTH-INDEX": "Nifty MidSml Hlth",
    "NSE:NIFTYMNC-INDEX": "Nifty MNC",
    "NSE:NIFTYMOBILITY-INDEX": "Nifty Mobility",
    "NSE:NIFTYMS400MQ100-INDEX": "NiftyMS400 MQ 100",
    "NSE:NIFTYMSFINSERV-INDEX": "Nifty MS Fin Serv",
    "NSE:NIFTYMSINDCONS-INDEX": "Nifty MS Ind Cons",
    "NSE:NIFTYMSITTELCM-INDEX": "Nifty MS IT Telcm",
    "NSE:NIFTYMULTIINFRA-INDEX": "Nifty Multi Infra",
    "NSE:NIFTYMULTIMFG-INDEX": "Nifty Multi Mfg",
    "NSE:NIFTYMULTIMQ50-INDEX": "Nifty Multi MQ 50",
    "NSE:NIFTYNEWCONSUMP-INDEX": "Nifty New Consump",
    "NSE:NIFTYNEXT50-INDEX": "Nifty Next 50",
    "NSE:NIFTYNONCYCCONS-INDEX": "Nifty NonCyc Cons",
    "NSE:NIFTYNXT50-INDEX": "Nifty Next 50",
    "NSE:NIFTYOILANDGAS-INDEX": "NIFTY OIL AND GAS",
    "NSE:NIFTYPHARMA-INDEX": "Nifty Pharma",
    "NSE:NIFTYPSE-INDEX": "Nifty PSE",
    "NSE:NIFTYPSUBANK-INDEX": "Nifty PSU Bank",
    "NSE:NIFTYPVTBANK-INDEX": "Nifty Pvt Bank",
    "NSE:NIFTYQLTYLV30-INDEX": "Nifty Qlty LV 30",
    "NSE:NIFTYQUALITY30-INDEX": "NIFTY100 Qualty30",
    "NSE:NIFTYREALTY-INDEX": "Nifty Realty",
    "NSE:NIFTYRURAL-INDEX": "Nifty Rural",
    "NSE:NIFTYSERVSECTOR-INDEX": "Nifty Serv Sector",
    "NSE:NIFTYSHARIAH25-INDEX": "Nifty Shariah 25",
    "NSE:NIFTYSML250MQ100-INDEX": "NiftySml250MQ 100",
    "NSE:NIFTYSML250Q50-INDEX": "Nifty Sml250 Q50",
    "NSE:NIFTYSMLCAP100-INDEX": "NIFTY SMLCAP 100",
    "NSE:NIFTYSMLCAP250-INDEX": "NIFTY SMLCAP 250",
    "NSE:NIFTYSMLCAP50-INDEX": "NIFTY SMLCAP 50",
    "NSE:NIFTYTATA25CAP-INDEX": "Nifty Tata 25 Cap",
    "NSE:NIFTYTOP10EW-INDEX": "Nifty Top 10 EW",
    "NSE:NIFTYTOP15EW-INDEX": "Nifty Top 15 EW",
    "NSE:NIFTYTOP20EW-INDEX": "Nifty Top 20 EW",
    "NSE:NIFTYTOTALMKT-INDEX": "NIFTY TOTAL MKT",
    "NSE:NIFTYTRANSLOGIS-INDEX": "Nifty Trans Logis",
}


def segment_for_token(fytoken):
    """
    Give the segment name that a Fyers instrument token belongs to.

    Fyers encodes the exchange and segment in the first four digits of every token, so this needs no lookup against the instrument master.

    Args:
        fytoken (str): The Fyers instrument token, for example "101000000026009".

    Returns:
        str | None: The segment name, for example "nse_cm", or None when the token's prefix is not one this module knows.
    """
    return SEGMENT_NAMES_BY_TOKEN_PREFIX.get(str(fytoken)[:4])


def index_name_for_ticker(symbol_ticker):
    """
    Give the exchange's own name for an index, which is what its topic is keyed on.

    An index is not subscribed by its numeric token but by the name the exchange publishes it under, and that name is not derivable from anything Fyers puts in its instrument master. The table here is transcribed from the one Fyers ships with its client library and covers 173 of the 182 index rows in the master.

    The fallback for the rest takes the ticker's own symbol, so "NSE:NIFTYCHEMICALS-INDEX" becomes "NIFTYCHEMICALS". That is a guess and is known to be one; it is what the client library does, and the live run is what confirms or refutes it for those nine.

    Args:
        symbol_ticker (str): The Fyers symbol ticker, for example "NSE:NIFTYBANK-INDEX".

    Returns:
        str: The index name to subscribe with, for example "NIFTY BANK".
    """
    if symbol_ticker in INDEX_NAMES_BY_TICKER:
        return INDEX_NAMES_BY_TICKER[symbol_ticker]
    without_exchange = str(symbol_ticker).split(":")[-1]
    return without_exchange.split("-")[0]


def is_index_ticker(symbol_ticker):
    """
    Say whether a Fyers symbol ticker names an index rather than a tradeable instrument.

    Args:
        symbol_ticker (str): The Fyers symbol ticker, for example "NSE:SBIN-EQ".

    Returns:
        bool: True when the ticker is an index.
    """
    return str(symbol_ticker).endswith("-INDEX")


def hsm_symbol(topic_prefix, segment, exchange_token):
    """
    Join the three parts of a subscription key into the string the wire uses.

    Args:
        topic_prefix (str): The feed prefix, "sf" for a tradeable quote, "if" for an index, or "dp" for depth.
        segment (str): The segment name, for example "nse_cm".
        exchange_token (str): The exchange's own token for the instrument, or an index's name.

    Returns:
        str: The subscription key, for example "sf|nse_cm|2885".
    """
    return f"{topic_prefix}|{segment}|{exchange_token}"


def hsm_symbol_for_instrument(fytoken, scrip_code, symbol_ticker, feed=FEED_QUOTE):
    """
    Build the subscription key for one instrument out of its own instrument master row.

    Fyers' client library obtains this key by posting every symbol to a REST endpoint, but the endpoint only returns the token that the instrument master already holds. Since the segment comes from the token's first four digits and the exchange token is the token's remainder, the key can be built entirely offline. That matters at this project's scale: the REST route allows ten requests a second and blocks the account for the rest of the day after three breaches of the per minute limit, against a universe of about a hundred and sixty thousand instruments.

    The instrument master's own `scrip_code` column holds the same digits as the token's remainder, which was checked across every row of a day's file, so it is used directly rather than sliced back out of the token.

    Args:
        fytoken (str): The Fyers instrument token from the instrument master.
        scrip_code (str): The exchange token from the instrument master, which is the token's remainder after its first ten digits.
        symbol_ticker (str): The Fyers symbol ticker, needed only to recognise an index and to name it.
        feed (str): Which feed to subscribe, "quote" or "depth".

    Returns:
        str | None: The subscription key, or None when the token's prefix names no segment this module knows, or when depth was asked for on an index, which Fyers does not serve.
    """
    segment = segment_for_token(fytoken)
    if segment is None:
        return None

    if is_index_ticker(symbol_ticker):
        if feed == FEED_DEPTH:
            return None
        return hsm_symbol(TOPIC_PREFIX_INDEX, segment, index_name_for_ticker(symbol_ticker))

    if feed == FEED_DEPTH:
        return hsm_symbol(TOPIC_PREFIX_DEPTH, segment, scrip_code)
    return hsm_symbol(TOPIC_PREFIX_SCRIP, segment, scrip_code)


def parse_topic_name(topic_name):
    """
    Split a topic name back into the three parts it was built from.

    Args:
        topic_name (str): The topic name as it arrived in a snapshot packet, for example "sf|nse_cm|2885".

    Returns:
        tuple: A (topic_prefix, segment, exchange_token) triple. Parts the name does not carry come back as None, because a malformed topic name must not raise inside the socket read loop.
    """
    parts = str(topic_name).split("|")
    if len(parts) != 3:
        return (None, None, None)
    return (parts[0], parts[1], parts[2])


def field_names_for_prefix(topic_prefix):
    """
    Give the positional field list that a topic's packets are read against.

    Args:
        topic_prefix (str): The feed prefix from a topic name, "sf", "if" or "dp".

    Returns:
        list[str] | None: The field names in wire order, or None when the prefix is not one this module knows.
    """
    if topic_prefix == TOPIC_PREFIX_SCRIP:
        return SCRIP_FIELD_NAMES
    if topic_prefix == TOPIC_PREFIX_INDEX:
        return INDEX_FIELD_NAMES
    if topic_prefix == TOPIC_PREFIX_DEPTH:
        return DEPTH_FIELD_NAMES
    return None


def tick_mode_for_prefix(topic_prefix):
    """
    Give the tick mode name that a topic's ticks are reported under.

    Args:
        topic_prefix (str): The feed prefix from a topic name, "sf", "if" or "dp".

    Returns:
        str | None: The tick mode, or None when the prefix is not one this module knows.
    """
    if topic_prefix == TOPIC_PREFIX_SCRIP:
        return "quote"
    if topic_prefix == TOPIC_PREFIX_INDEX:
        return "index_quote"
    if topic_prefix == TOPIC_PREFIX_DEPTH:
        return "full"
    return None


def price_divisor(multiplier, price_precision):
    """
    Give the number that turns this instrument's wire prices into rupees.

    A snapshot carries two numbers that could each be the answer, a multiplier and a price precision, and Fyers documents neither. This follows the Flattrade decoder's rule, ten to the power of the precision, because that is the form the other Noren-adjacent feeds use and because it handles a currency scrip quoted in fractions of a paisa, which a fixed hundred would misstate.

    The multiplier is carried on every tick beside the divisor rather than being discarded, so the cross-check against Fyers' own REST quotes can measure the implied scale and settle which of the two is really the divisor. Until that check has run against a live market this is the decoder's best reading rather than an established fact.

    Args:
        multiplier (int | None): The multiplier the snapshot carried, kept for the cross-check.
        price_precision (int | None): The number of decimal places the instrument's prices are quoted to.

    Returns:
        int: The divisor to apply to this instrument's stored prices.
    """
    if price_precision is None:
        return 10 ** DEFAULT_PRICE_PRECISION
    return 10 ** price_precision


def epoch_seconds_to_datetime(epoch_seconds):
    """
    Turn an exchange timestamp into a datetime, rejecting the implausible ones.

    The exchange sends zero when it has no timestamp to give. The ticks table is partitioned by time, so anything outside a sane range becomes no timestamp rather than a wrong one, which would put a row in the wrong partition.

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


def frame_response_type(frame):
    """
    Give the response type a frame declares in its header.

    Args:
        frame (bytes): One complete websocket frame as received.

    Returns:
        int | None: The response type, for example 6 for market data, or None when the frame is too short to carry a header.
    """
    if len(frame) < FRAME_HEADER_LENGTH:
        return None
    return FRAME_HEADER_STRUCT.unpack_from(frame, 0)[1]


def frame_message_number(frame):
    """
    Give the message number a market data frame carries, which is what an acknowledgement quotes back.

    Args:
        frame (bytes): One complete websocket frame as received.

    Returns:
        int | None: The message number, or None when the frame is not market data or is too short to carry one.
    """
    if frame_response_type(frame) != RESPONSE_TYPE_DATA_FEED:
        return None
    if len(frame) < FRAME_HEADER_LENGTH + MESSAGE_NUMBER_STRUCT.size:
        return None
    return MESSAGE_NUMBER_STRUCT.unpack_from(frame, FRAME_HEADER_LENGTH)[0]


def frame_packet_count(frame):
    """
    Count the packets one websocket frame carries, for the archive manifest.

    The archive is broker agnostic and must not interpret broker frames itself, so the counting decision lives in each broker's parser and the archive calls the function it is given. This reads the same two byte packet count that decode_frame reads, so the two can never disagree about what a frame claims. A frame that is not market data carries no packets, so the acknowledgements never inflate the manifest's reconciliation.

    Args:
        frame (bytes): One complete websocket frame as received.

    Returns:
        int: The number of packets the frame claims to carry, which is zero for anything that is not a market data frame.
    """
    if frame_response_type(frame) != RESPONSE_TYPE_DATA_FEED:
        return 0
    if len(frame) < PACKET_COUNT_OFFSET + PACKET_COUNT_STRUCT.size:
        return 0
    return PACKET_COUNT_STRUCT.unpack_from(frame, PACKET_COUNT_OFFSET)[0]


def read_field_values(frame, offset, field_count):
    """
    Read one packet's run of four byte values.

    Args:
        frame (bytes): The whole websocket frame the packet sits inside.
        offset (int): Byte offset of the first value.
        field_count (int): How many values the packet says it carries.

    Returns:
        tuple: A (values, offset) pair, where values is a list holding the number read for each field and None where the wire said the field was absent, and offset is the byte after the last value read. Reading stops early when the frame ends mid-value, and the values read so far are returned.
    """
    values = []
    for _ in range(field_count):
        if offset + FIELD_VALUE_STRUCT.size > len(frame):
            return (values, offset)
        value = FIELD_VALUE_STRUCT.unpack_from(frame, offset)[0]
        offset = offset + FIELD_VALUE_STRUCT.size
        if value == ABSENT_VALUE:
            values.append(None)
        else:
            values.append(value)
    return (values, offset)


def read_length_prefixed_string(frame, offset):
    """
    Read one string that a packet introduces with a single byte of length.

    Args:
        frame (bytes): The whole websocket frame the string sits inside.
        offset (int): Byte offset of the length byte.

    Returns:
        tuple: A (text, offset) pair, where text is None when the frame ends before the string does, and offset is the byte after the string.
    """
    if offset + 1 > len(frame):
        return (None, offset)
    length = frame[offset]
    offset = offset + 1
    if offset + length > len(frame):
        return (None, offset)
    text = frame[offset:offset + length].decode("utf-8", errors="ignore")
    return (text, offset + length)


def apply_depth_values(tick, values):
    """
    Turn a depth packet's flat run of values into the six arrays the shared contract uses.

    The wire sends five bid prices, then five ask prices, then the quantities and then the order counts, all in one run, so an array is present only when the packet reached far enough to carry any of it. Arrays keep their five places and hold None where the wire sent nothing, because trimming a level that reported nothing would make one instrument's book a different shape from another's.

    Args:
        tick (dict): The partial tick to write the arrays into.
        values (list): The packet's values in wire order, None where the wire said absent.

    Returns:
        None.
    """
    for group_number, field_name in enumerate(DEPTH_FIELD_NAMES):
        start = group_number * DEPTH_LEVELS_PER_SIDE
        if start >= len(values):
            return
        level_values = []
        for level in range(DEPTH_LEVELS_PER_SIDE):
            position = start + level
            if position < len(values):
                level_values.append(values[position])
            else:
                level_values.append(None)
        tick[field_name] = level_values


def apply_scalar_values(tick, values, field_names):
    """
    Write one packet's values onto a partial tick under their positional names.

    A value the wire reported as absent is left off the tick entirely rather than written as None, so that the assembler can tell a field this packet did not carry from one it carried as nothing.

    Args:
        tick (dict): The partial tick to write the fields into.
        values (list): The packet's values in wire order, None where the wire said absent.
        field_names (list[str]): The positional field names to read the values against.

    Returns:
        None.
    """
    for position, value in enumerate(values):
        if position >= len(field_names):
            return
        if value is None:
            continue
        field_name = field_names[position]
        if field_name in TIMESTAMP_FIELDS:
            tick[field_name] = epoch_seconds_to_datetime(value)
        else:
            tick[field_name] = value


def decode_snapshot_packet(frame, offset, arrival_time):
    """
    Decode a kind 83 packet, which names its topic and carries the instrument's full state.

    This is the only packet that names its topic, so it is the only one that can teach a reader what a topic identifier means. It also carries the multiplier, the price precision and the exchange's own identifiers, none of which any later packet repeats.

    Args:
        frame (bytes): The whole websocket frame the packet sits inside.
        offset (int): Byte offset of the byte after the packet kind.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        tuple: A (tick, offset) pair, where tick is the partial tick or None when the frame ended mid-packet, and offset is the byte after the packet.
    """
    if offset + TOPIC_IDENTIFIER_STRUCT.size > len(frame):
        return (None, len(frame))
    topic_identifier = TOPIC_IDENTIFIER_STRUCT.unpack_from(frame, offset)[0]
    offset = offset + TOPIC_IDENTIFIER_STRUCT.size

    topic_name, offset = read_length_prefixed_string(frame, offset)
    if topic_name is None:
        return (None, len(frame))

    topic_prefix, segment, exchange_token = parse_topic_name(topic_name)
    field_names = field_names_for_prefix(topic_prefix)
    if field_names is None:
        return (None, len(frame))

    if offset + 1 > len(frame):
        return (None, len(frame))
    field_count = frame[offset]
    offset = offset + 1

    values, offset = read_field_values(frame, offset, field_count)
    offset = offset + SNAPSHOT_TRAILING_SKIP_BYTES

    multiplier = None
    if offset + MULTIPLIER_STRUCT.size <= len(frame):
        multiplier = MULTIPLIER_STRUCT.unpack_from(frame, offset)[0]
    offset = offset + MULTIPLIER_STRUCT.size

    price_precision = None
    if offset < len(frame):
        price_precision = frame[offset]
    offset = offset + 1

    tick = {
        "arrival_time": arrival_time,
        "topic_identifier": topic_identifier,
        "topic_name": topic_name,
        "topic_prefix": topic_prefix,
        "segment": segment,
        "exchange_token": exchange_token,
        "tick_mode": tick_mode_for_prefix(topic_prefix),
        "tradable": topic_prefix != TOPIC_PREFIX_INDEX,
        "multiplier": multiplier,
        "price_precision": price_precision,
        "price_divisor": price_divisor(multiplier, price_precision),
        "is_snapshot": True,
    }

    if topic_prefix == TOPIC_PREFIX_DEPTH:
        apply_depth_values(tick, values)
    else:
        apply_scalar_values(tick, values, field_names)

    for string_field in SNAPSHOT_STRING_FIELDS:
        text, offset = read_length_prefixed_string(frame, offset)
        tick[string_field] = text

    return (tick, offset)


def decode_update_packet(frame, offset, arrival_time):
    """
    Decode a kind 85 packet, which carries a topic identifier and the changed values only.

    Nothing in this packet says which instrument it belongs to or which field list to read it against, so it cannot be decoded on its own. The values are carried through as a positional list and TickAssembler, which holds the topic table, is what names them.

    Args:
        frame (bytes): The whole websocket frame the packet sits inside.
        offset (int): Byte offset of the byte after the packet kind.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        tuple: A (tick, offset) pair, where tick is the partial tick or None when the frame ended mid-packet, and offset is the byte after the packet.
    """
    if offset + TOPIC_IDENTIFIER_STRUCT.size > len(frame):
        return (None, len(frame))
    topic_identifier = TOPIC_IDENTIFIER_STRUCT.unpack_from(frame, offset)[0]
    offset = offset + TOPIC_IDENTIFIER_STRUCT.size

    if offset + 1 > len(frame):
        return (None, len(frame))
    field_count = frame[offset]
    offset = offset + 1

    values, offset = read_field_values(frame, offset, field_count)
    tick = {
        "arrival_time": arrival_time,
        "topic_identifier": topic_identifier,
        "values": values,
        "is_snapshot": False,
    }
    return (tick, offset)


def decode_lite_update_packet(frame, offset, arrival_time):
    """
    Decode a kind 76 packet, which carries a topic identifier and one price.

    Lite mode is not used by this project's shards, which subscribe in full mode, but the packet is decoded rather than skipped so that a connection accidentally left in lite mode produces ticks that are visibly thin instead of silence that looks like a dead subscription.

    Args:
        frame (bytes): The whole websocket frame the packet sits inside.
        offset (int): Byte offset of the byte after the packet kind.
        arrival_time (datetime.datetime): The moment the frame was read off the socket.

    Returns:
        tuple: A (tick, offset) pair, where tick is the partial tick or None when the frame ended mid-packet, and offset is the byte after the packet.
    """
    if offset + TOPIC_IDENTIFIER_STRUCT.size > len(frame):
        return (None, len(frame))
    topic_identifier = TOPIC_IDENTIFIER_STRUCT.unpack_from(frame, offset)[0]
    offset = offset + TOPIC_IDENTIFIER_STRUCT.size

    values, offset = read_field_values(frame, offset, 1)
    tick = {
        "arrival_time": arrival_time,
        "topic_identifier": topic_identifier,
        "values": values,
        "is_snapshot": False,
    }
    return (tick, offset)


def decode_frame(frame, arrival_time):
    """
    Decode every packet in one websocket frame.

    A frame that is not market data decodes to nothing at all rather than raising, which covers the authentication, subscription, mode and channel acknowledgements the connection driver reads for itself.

    A frame that ends in the middle of a packet stops the loop and the packets read so far are returned. Raising instead would be worse than useless: this runs inside the socket read loop, so one malformed frame would take down a connection carrying thousands of instruments.

    The partial ticks this returns are not complete ticks and are not meant to be used directly. A snapshot names its topic and an update does not, so both have to go through TickAssembler before they mean anything.

    Args:
        frame (bytes): One complete websocket frame as received.
        arrival_time (datetime.datetime): The moment the frame was read off the socket, recorded by the caller so that every tick in the frame shares one timestamp.

    Returns:
        list[dict]: One partial tick per packet, in the order the packets appeared. Packets whose kind is not a recognised one end the frame, because an unknown kind has an unknown length and nothing after it can be located.
    """
    if frame_response_type(frame) != RESPONSE_TYPE_DATA_FEED:
        return []
    if len(frame) < PACKET_COUNT_OFFSET + PACKET_COUNT_STRUCT.size:
        return []

    packet_count = PACKET_COUNT_STRUCT.unpack_from(frame, PACKET_COUNT_OFFSET)[0]
    offset = FIRST_PACKET_OFFSET
    ticks = []

    for _ in range(packet_count):
        if offset >= len(frame):
            break
        packet_kind = frame[offset]
        offset = offset + 1

        if packet_kind == PACKET_KIND_SNAPSHOT:
            tick, offset = decode_snapshot_packet(frame, offset, arrival_time)
        elif packet_kind == PACKET_KIND_UPDATE:
            tick, offset = decode_update_packet(frame, offset, arrival_time)
        elif packet_kind == PACKET_KIND_LITE_UPDATE:
            tick, offset = decode_lite_update_packet(frame, offset, arrival_time)
        else:
            break

        if tick is None:
            break
        ticks.append(tick)

    return ticks


class TickAssembler:
    """
    Merges partial ticks into complete ticks, one instrument at a time.

    This carries more than its counterparts for the other brokers, because Fyers omits more. Flattrade and Shoonya name the instrument in every message and only leave out the fields that did not change, so their assemblers hold last seen values and nothing else. A Fyers update packet leaves out the instrument's name as well, identifying it only by a number that means something because an earlier snapshot said so, so this also holds the topic table that gives those numbers meaning.

    The topic table belongs to one connection. Fyers numbers topics per connection, so the same number means a different instrument on a reconnected socket, and an assembler reused across a reconnection would attribute one instrument's prices to another. A connection that reconnects builds a new assembler.

    Attributes:
        topics_by_identifier (dict): Each topic's name, prefix, segment and exchange token, keyed on the identifier snapshots introduced it under.
        ticks_by_topic (dict): The last seen value of every field, keyed on topic name.
    """

    def __init__(self):
        """
        Start with no topic table and no instrument state at all.

        Returns:
            None.
        """
        self.topics_by_identifier = {}
        self.ticks_by_topic = {}

    def remember_topic(self, tick):
        """
        Record what a snapshot said one topic identifier means.

        Args:
            tick (dict): One partial tick from a snapshot packet.

        Returns:
            None.
        """
        self.topics_by_identifier[tick["topic_identifier"]] = {
            "topic_name": tick["topic_name"],
            "topic_prefix": tick["topic_prefix"],
            "segment": tick["segment"],
            "exchange_token": tick["exchange_token"],
            "tick_mode": tick["tick_mode"],
            "tradable": tick["tradable"],
            "multiplier": tick["multiplier"],
            "price_precision": tick["price_precision"],
            "price_divisor": tick["price_divisor"],
        }

    def known_topic(self, topic_identifier):
        """
        Give what a topic identifier was said to mean, if a snapshot has said so.

        Args:
            topic_identifier (int): The identifier a packet carried.

        Returns:
            dict | None: The topic's details, or None when no snapshot has introduced this identifier on this connection.
        """
        return self.topics_by_identifier.get(topic_identifier)

    def stored_tick(self, topic):
        """
        Give the accumulated tick for one topic, creating an empty one the first time.

        Args:
            topic (dict): One topic's details from the topic table.

        Returns:
            dict: The stored tick, with every contract field present and None where the instrument has not reported one yet.
        """
        topic_name = topic["topic_name"]
        stored = self.ticks_by_topic.get(topic_name)
        if stored is not None:
            return stored

        stored = {
            "topic_name": topic_name,
            "topic_prefix": topic["topic_prefix"],
            "segment": topic["segment"],
            "exchange_token": topic["exchange_token"],
            "tick_mode": topic["tick_mode"],
            "tradable": topic["tradable"],
            "multiplier": topic["multiplier"],
            "price_precision": topic["price_precision"],
            "price_divisor": topic["price_divisor"],
        }
        for field in CONTRACT_FIELDS:
            stored[field] = None
        self.ticks_by_topic[topic_name] = stored
        return stored

    def merge(self, tick):
        """
        Merge one partial tick into its instrument's state and return the complete tick.

        An update packet whose topic identifier no snapshot has introduced returns None rather than raising. That is the expected shape of a race rather than an error: a subscription's first update can arrive before its snapshot has been read, and dropping the update loses one revision of a field that the next update will carry again, whereas guessing at the instrument would attribute it to the wrong one.

        A field the packet did not carry is left at its last seen value, and a field the instrument has never reported stays None rather than being invented as a zero.

        Args:
            tick (dict): One partial tick from decode_frame.

        Returns:
            dict | None: The complete tick for this instrument, or None when the packet was an update for a topic this connection has not seen a snapshot for.
        """
        if tick.get("is_snapshot"):
            if tick.get("topic_prefix") is None:
                return None
            self.remember_topic(tick)
            topic = self.known_topic(tick["topic_identifier"])
            stored = self.stored_tick(topic)
            for field in CONTRACT_FIELDS:
                if field in tick:
                    stored[field] = tick[field]
            stored["arrival_time"] = tick["arrival_time"]
            return dict(stored)

        topic = self.known_topic(tick["topic_identifier"])
        if topic is None:
            return None

        field_names = field_names_for_prefix(topic["topic_prefix"])
        if field_names is None:
            return None

        stored = self.stored_tick(topic)
        named = {}
        if topic["topic_prefix"] == TOPIC_PREFIX_DEPTH:
            apply_depth_values(named, tick["values"])
        else:
            apply_scalar_values(named, tick["values"], field_names)

        for field, value in named.items():
            stored[field] = value
        stored["arrival_time"] = tick["arrival_time"]
        return dict(stored)

    def known_instruments(self):
        """
        List the topics this assembler has state for.

        Returns:
            list[str]: One topic name per instrument seen so far.
        """
        return list(self.ticks_by_topic)
