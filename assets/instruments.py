"""Instruments from UBI's unified instrument universe, with their candles, live prices and analysis.

`Instrument` looks an instrument up in UBI once, keeps its identity, lot size and tick size, and fetches candles and live prices on demand. It inherits every analysis class in `assets.analysis`, so indicators, candlestick patterns, statistics and backtests are methods on the instrument. `TradeableInstrument` adds the values that come from the order book, the methods that place, change and cancel orders, and this instrument's own orders, trades and positions, and it refuses indices. `NonTradeableInstrument` accepts only indices.

Every call goes straight to UBI's REST API, which caches on its own side.

Typical usage example:

  infosys = instruments.TradeableInstrument(exchange="nse", segment="equities", symbol="INFY")
  frame = infosys.relative_strength_index(window=14, days=365)
  spread = infosys.bid_offer_spread()

  placed = infosys.place_order(transaction_type="buy", order_type="limit", quantity=1, product="cnc", price=1200)
  pending = infosys.orders(open_only=True)
  infosys.cancel_order(placed["order_id"])

  nifty = instruments.NonTradeableInstrument(exchange="nse", segment="equity_indices", symbol="NIFTY")
  level = nifty.last_price()
"""

import datetime
import decimal
import zoneinfo

import pandas as pd

from assets import exceptions
from assets.analysis import candlestick_patterns
from assets.analysis import cycle_indicators
from assets.analysis import math_operators
from assets.analysis import math_transforms
from assets.analysis import momentum_indicators
from assets.analysis import overlap_studies
from assets.analysis import price_statistics
from assets.analysis import price_transforms
from assets.analysis import signals
from assets.analysis import statistic_functions
from assets.analysis import strategy_backtests
from assets.analysis import volatility_indicators
from assets.analysis import volume_indicators
from ubi_client import client
from ubi_client import exceptions as ubi_exceptions

INDIA_TIME_ZONE = zoneinfo.ZoneInfo("Asia/Kolkata")

INDEX_SEGMENT_SUFFIX = "_indices"

ORDER_DETAILS_PATH = "/api/orders/details"

ORDER_TRADES_PATH = "/api/orders/trades"

ORDER_PLACE_PATH = "/api/orders/place"

ORDER_MODIFY_PATH = "/api/orders/modify"

ORDER_CANCEL_PATH = "/api/orders/cancel"

POSITIONS_PATH = "/api/portfolio/positions"

OPEN_ORDER_STATUSES = [
    "PENDING",
    "OPEN",
]


class Instrument(
    price_statistics.PriceStatistics,
    overlap_studies.OverlapStudies,
    momentum_indicators.MomentumIndicators,
    volume_indicators.VolumeIndicators,
    cycle_indicators.CycleIndicators,
    price_transforms.PriceTransforms,
    volatility_indicators.VolatilityIndicators,
    statistic_functions.StatisticFunctions,
    math_transforms.MathTransforms,
    math_operators.MathOperators,
    candlestick_patterns.CandlestickPatterns,
    signals.Signals,
    strategy_backtests.StrategyBacktests,
):
    """One instrument in UBI's unified instrument universe.

    Attributes:
        instrument_id: The str UUID UBI computes for the instrument, the same at every broker.
        exchange: The str lower-case exchange, such as `nse` or `mcx`.
        segment: The str exchange-prefixed segment, such as `nse_equities`.
        shape: The str shape of the segment: `security`, `future` or `option`.
        symbol: The str symbol of a security, or None for a future or option.
        underlying_symbol: The str symbol of a future's or option's underlying, or None for a security.
        expiry_date: The datetime.date a future or option expires, or None for a security.
        strike_price: The float strike price of an option, or None for anything else.
        option_type: The str option type, `CE` or `PE`, or None for anything else.
        mapping_date: The datetime.date of the UBI mapping the details were read from.
        first_seen_date: The datetime.date UBI first saw the instrument, or None when unknown.
        last_seen_date: The datetime.date UBI last saw the instrument, or None when unknown.
        lot_size: The int number of underlying units in one lot, or None when UBI's brokers do not agree.
        tick_size: The decimal.Decimal smallest price step in rupees, or None when UBI's brokers do not agree.
        carried_by: A list of dicts, one per broker carrying the instrument, each with that broker's own token, order symbol, lot size and tick size.
    """

    _shared_unified_broker_interface = None

    def __init__(
        self,
        instrument_id: str | None = None,
        exchange: str | None = None,
        segment: str | None = None,
        symbol: str | None = None,
        underlying_symbol: str | None = None,
        expiry_date: datetime.date | str | None = None,
        strike_price: float | None = None,
        option_type: str | None = None,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the instrument up in UBI and keeps its details.

        Give either instrument_id, or exchange, segment and the identity fields the segment's shape needs: symbol for a security, underlying_symbol and expiry_date for a future, and all four of underlying_symbol, expiry_date, strike_price and option_type for an option.

        Args:
            instrument_id: The str UUID of the instrument, or None to look it up by exchange, segment and identity fields.
            exchange: The str exchange, such as `nse`, or None when instrument_id is given.
            segment: The str segment, bare such as `equities` or prefixed such as `nse_equities`, or None when instrument_id is given.
            symbol: The str symbol of a security, or None.
            underlying_symbol: The str symbol of a future's or option's underlying, or None.
            expiry_date: The expiry of a future or option as a datetime.date or a `YYYY-MM-DD` str, or None.
            strike_price: The float strike price of an option, or None.
            option_type: The str option type of an option, `CE` or `PE`, or None.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            InstrumentError: UBI has no instrument matching the lookup.
            BadRequestError: The lookup is incomplete or malformed, such as a future without an expiry_date.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        if unified_broker_interface is None:
            unified_broker_interface = Instrument._get_shared_unified_broker_interface()
        self._unified_broker_interface = unified_broker_interface
        lookup = {
            "instrument_id": instrument_id,
            "exchange": exchange,
            "segment": segment,
            "symbol": symbol,
            "underlying_symbol": underlying_symbol,
            "expiry_date": expiry_date,
            "strike_price": strike_price,
            "option_type": option_type,
        }
        details = self._fetch_details(lookup)
        self.instrument_id = details["instrument_id"]
        self.exchange = details["exchange"]
        self.segment = details["segment"]
        self.shape = details["shape"]
        self.symbol = details["symbol"]
        self.underlying_symbol = details["underlying_symbol"]
        self.expiry_date = self._parse_date(details["expiry_date"])
        self.strike_price = details["strike_price"]
        self.option_type = details["option_type"]
        self.mapping_date = self._parse_date(details["mapping_date"])
        self.first_seen_date = self._parse_date(details["first_seen_date"])
        self.last_seen_date = self._parse_date(details["last_seen_date"])
        self.lot_size = details.get("lot_size")
        self.tick_size = self._parse_decimal(details.get("tick_size"))
        self.carried_by = details["carried_by"]

    @classmethod
    def _get_shared_unified_broker_interface(
        cls,
    ) -> client.UnifiedBrokerInterface:
        """Returns the one client all instruments share, creating it on first use.

        UBI holds a single access token, so separate clients would keep replacing each other's token. The client is stored on `Instrument` itself rather than on cls, so subclasses share the same one.

        Returns:
            The shared client.UnifiedBrokerInterface.

        Raises:
            ValueError: The client's base url or MongoDB credentials are not configured.
        """
        if Instrument._shared_unified_broker_interface is None:
            Instrument._shared_unified_broker_interface = (
                client.UnifiedBrokerInterface()
            )
        return Instrument._shared_unified_broker_interface

    def _fetch_details(self, lookup: dict) -> dict:
        """Reads the instrument's details from UBI.

        Args:
            lookup: A dict of the constructor's lookup arguments, where None means not given.

        Returns:
            The dict UBI returns from `/api/instruments/details`.

        Raises:
            InstrumentError: UBI has no instrument matching the lookup.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        parameters = {}
        if lookup["instrument_id"] is not None:
            parameters["instrument_id"] = lookup["instrument_id"]
        else:
            for name, value in lookup.items():
                if value is not None:
                    parameters[name] = value
        try:
            return self._unified_broker_interface.get(
                "/api/instruments/details",
                params=parameters,
            )
        except ubi_exceptions.NotFoundError as error:
            raise exceptions.InstrumentError(
                f"UBI has no instrument matching {parameters}: {error.message}"
            ) from error

    @staticmethod
    def _parse_date(value: str | None) -> datetime.date | None:
        """Turns an ISO date string from UBI into a date.

        Args:
            value: A `YYYY-MM-DD` str, or None.

        Returns:
            The datetime.date, or None when value is None.

        Raises:
            ValueError: value is not a valid ISO date.
        """
        if value is None:
            return None
        return datetime.date.fromisoformat(value)

    @staticmethod
    def _parse_decimal(value: str | None) -> decimal.Decimal | None:
        """Turns a number string from UBI into an exact decimal.

        Args:
            value: A str such as `0.05`, or None.

        Returns:
            The decimal.Decimal, or None when value is None.

        Raises:
            decimal.InvalidOperation: value is not a number.
        """
        if value is None:
            return None
        return decimal.Decimal(value)

    def __repr__(self) -> str:
        """Describes the instrument by exchange, segment and identity fields.

        Each value is shown as its own type, so a strike price reads as the number 24000.0 rather than as text. A date is shown in its `YYYY-MM-DD` form, which is what the constructor accepts, rather than as `datetime.date(2026, 9, 29)`.

        Returns:
            A str such as `Instrument(exchange='nse', segment='nse_equities', symbol='INFY')`.

        Raises:
            Nothing.
        """
        identity = {
            "symbol": self.symbol,
            "underlying_symbol": self.underlying_symbol,
            "expiry_date": self.expiry_date,
            "strike_price": self.strike_price,
            "option_type": self.option_type,
        }
        described_fields = [
            f"exchange={self.exchange!r}",
            f"segment={self.segment!r}",
        ]
        for field, value in identity.items():
            if value is None:
                continue
            if isinstance(value, datetime.date):
                described_fields.append(f"{field}={value.isoformat()!r}")
            else:
                described_fields.append(f"{field}={value!r}")
        return f"{type(self).__name__}({', '.join(described_fields)})"

    def __eq__(self, other: object) -> bool:
        """Compares two instruments by their UBI instrument id.

        Args:
            other: The object to compare with, of any type.

        Returns:
            A bool that is True when other is an Instrument with the same instrument_id, or NotImplemented for any other type.

        Raises:
            Nothing.
        """
        if not isinstance(other, Instrument):
            return NotImplemented
        return self.instrument_id == other.instrument_id

    def __hash__(self) -> int:
        """Hashes the instrument by its UBI instrument id.

        Returns:
            The int hash of instrument_id.

        Raises:
            Nothing.
        """
        return hash(self.instrument_id)

    def prices(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> pd.DataFrame | None:
        """Fetches the instrument's candles for a range from UBI.

        Give either from_date and to_date, or days. UBI serves any range in one request.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            A pandas.DataFrame sorted by time, with `exchange`, `segment`, `interval`, `datetime` in India time, `open`, `high`, `low`, `close`, `volume` and `oi` columns, plus `price_factor` when the prices are adjusted, or None when UBI has no candles for the range.

        Raises:
            BadRequestError: The range or interval is invalid, such as both days and from_date given.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        parameters = {
            "instrument_id": self.instrument_id,
            "interval": interval,
        }
        if adjusted:
            parameters["adjusted"] = "true"
        else:
            parameters["adjusted"] = "false"
        if from_date is not None:
            parameters["from"] = from_date
        if to_date is not None:
            parameters["to"] = to_date
        if days is not None:
            parameters["days"] = days
        response = self._unified_broker_interface.get(
            "/api/instruments/prices",
            params=parameters,
        )
        if not response["candles"]:
            return None
        frame = pd.DataFrame(response["candles"], columns=response["columns"])
        frame = frame.rename(columns={"time": "datetime"})
        frame["datetime"] = pd.to_datetime(frame["datetime"]).dt.tz_convert(
            INDIA_TIME_ZONE
        )
        frame.insert(0, "interval", interval)
        frame.insert(0, "segment", self.segment)
        frame.insert(0, "exchange", self.exchange)
        return frame.sort_values("datetime").reset_index(drop=True)

    def quote(self) -> dict:
        """Fetches the instrument's full unified quote from UBI.

        Returns:
            The quote as a dict, with `last_price`, `average_price`, `ohlc`, `previous_close`, `change_percent`, `volume`, `oi`, `depth` and the other fields of UBI's unified quote.

        Raises:
            ServiceUnavailableError: UBI has no recent quote and no broker could supply one.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self._unified_broker_interface.get(
            "/api/instruments/quote",
            params={
                "instrument_id": self.instrument_id,
            },
        )

    def last_price(self) -> float | None:
        """Fetches the instrument's last traded price from UBI.

        Returns:
            The float last price in rupees, or None when UBI has none.

        Raises:
            ServiceUnavailableError: UBI has no recent quote and no broker could supply one.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        response = self._unified_broker_interface.get(
            "/api/instruments/ltp",
            params={
                "instrument_id": self.instrument_id,
            },
        )
        return response["last_price"]

    def ohlc(self) -> dict:
        """Fetches the day's open, high and low with the last and previous close prices from UBI.

        Returns:
            A dict with `last_price`, `ohlc` (a dict of `open`, `high` and `low`), `previous_close`, `change_percent`, `last_trade_time` and the instrument's identity fields.

        Raises:
            ServiceUnavailableError: UBI has no recent quote and no broker could supply one.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self._unified_broker_interface.get(
            "/api/instruments/ohlc",
            params={
                "instrument_id": self.instrument_id,
            },
        )


class TradeableInstrument(Instrument):
    """An instrument that can be traded, which is anything except an index."""

    def __init__(
        self,
        instrument_id: str | None = None,
        exchange: str | None = None,
        segment: str | None = None,
        symbol: str | None = None,
        underlying_symbol: str | None = None,
        expiry_date: datetime.date | str | None = None,
        strike_price: float | None = None,
        option_type: str | None = None,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the instrument up in UBI and checks that it is not an index.

        Args:
            instrument_id: The str UUID of the instrument, or None to look it up by exchange, segment and identity fields.
            exchange: The str exchange, such as `nse`, or None when instrument_id is given.
            segment: The str segment, bare such as `equities` or prefixed such as `nse_equities`, or None when instrument_id is given.
            symbol: The str symbol of a security, or None.
            underlying_symbol: The str symbol of a future's or option's underlying, or None.
            expiry_date: The expiry of a future or option as a datetime.date or a `YYYY-MM-DD` str, or None.
            strike_price: The float strike price of an option, or None.
            option_type: The str option type of an option, `CE` or `PE`, or None.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            TradeableInstrumentError: The instrument is an index.
            InstrumentError: UBI has no instrument matching the lookup.
            BadRequestError: The lookup is incomplete or malformed.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        super().__init__(
            instrument_id=instrument_id,
            exchange=exchange,
            segment=segment,
            symbol=symbol,
            underlying_symbol=underlying_symbol,
            expiry_date=expiry_date,
            strike_price=strike_price,
            option_type=option_type,
            unified_broker_interface=unified_broker_interface,
        )
        if self.segment.endswith(INDEX_SEGMENT_SUFFIX):
            raise exceptions.TradeableInstrumentError(
                f"An index cannot be traded, so it is not a TradeableInstrument: {self!r}"
            )

    def bids(self) -> list[dict]:
        """Fetches the buy side of the order book.

        Returns:
            A list of up to five dicts with `price`, `quantity` and `orders`, best first, which is empty when nobody is bidding.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        return self.quote()["depth"]["buy"]

    def asks(self) -> list[dict]:
        """Fetches the sell side of the order book.

        Returns:
            A list of up to five dicts with `price`, `quantity` and `orders`, best first, which is empty when nobody is offering.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        return self.quote()["depth"]["sell"]

    def best_bid(self) -> dict | None:
        """Fetches the highest bid in the order book.

        Returns:
            A dict with `price`, `quantity` and `orders`, or None when nobody is bidding.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        return self._best_level(self.bids())

    def best_offer(self) -> dict | None:
        """Fetches the lowest offer in the order book.

        Returns:
            A dict with `price`, `quantity` and `orders`, or None when nobody is offering.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        return self._best_level(self.asks())

    def bid_offer_spread(self) -> float | None:
        """Fetches one quote and measures the gap between its best offer and best bid.

        Returns:
            The float spread in rupees, or None when either side of the order book is empty.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        depth = self.quote()["depth"]
        best_bid = self._best_level(depth["buy"])
        best_offer = self._best_level(depth["sell"])
        if best_bid is None or best_offer is None:
            return None
        return best_offer["price"] - best_bid["price"]

    def mid_price(self) -> float | None:
        """Fetches one quote and finds the price halfway between its best bid and best offer.

        Returns:
            The float mid price in rupees, or None when either side of the order book is empty.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        depth = self.quote()["depth"]
        best_bid = self._best_level(depth["buy"])
        best_offer = self._best_level(depth["sell"])
        if best_bid is None or best_offer is None:
            return None
        return (best_bid["price"] + best_offer["price"]) / 2

    def volume_weighted_average_price(self) -> float | None:
        """Fetches today's volume weighted average price.

        Returns:
            The float price in rupees, or None when the broker serving the quote does not report it.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        return self.quote()["average_price"]

    def last_quantity(self) -> int | None:
        """Fetches the quantity of the last trade.

        Returns:
            The int quantity in underlying units, not lots, or None when unknown.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        return self.quote()["last_quantity"]

    def total_traded_volume(self) -> int | None:
        """Fetches the quantity traded so far today.

        Returns:
            The int volume in underlying units, not lots, or None when unknown.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        return self.quote()["volume"]

    def open_interest(self) -> int | None:
        """Fetches the open interest of a future or option.

        Returns:
            The int open interest in underlying units, or None for a security or when unknown.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        return self.quote()["oi"]

    def last_trade_time(self) -> datetime.datetime | None:
        """Fetches when the last trade happened.

        Returns:
            The time as a datetime.datetime in India time, or None when the broker does not send one reliably.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        epoch_seconds = self.quote()["last_trade_time"]
        if epoch_seconds is None:
            return None
        return datetime.datetime.fromtimestamp(epoch_seconds, INDIA_TIME_ZONE)

    def place_order(
        self,
        transaction_type: str,
        order_type: str,
        quantity: int,
        product: str,
        price: float | None = None,
        trigger_price: float | None = None,
        validity: str | None = None,
        disclosed_quantity: int | None = None,
        after_market: bool = False,
        tag: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Places one order in this instrument through UBI.

        UBI chooses the broker itself, so no broker is named here. The values are sent exactly as given, without rounding the price to the tick size or checking the quantity against the lot size, because UBI and the broker behind it hold those rules.

        UBI couples the price fields to the order type and answers HTTP 400 when they do not agree: a `limit` or `sl` order needs a price, an `sl` or `sl-m` order needs a trigger price, and a `market` or `sl-m` order must carry no price at all.

        Args:
            transaction_type: The str side of the order, `buy` or `sell`.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            price: The float limit price in rupees, or None for an order type that takes no price.
            trigger_price: The float trigger price in rupees, or None for an order type that takes no trigger.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            disclosed_quantity: The int quantity to show on the exchange, or None to disclose the whole order.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.
            dry_run: A bool that is True to have UBI build the broker's request and return it without sending it.

        Returns:
            A dict with `broker`, `instrument_id`, `order_id`, `outcome`, `status_message`, `broker_response`, `skipped` and `timing_ms`, or, for a dry run, a dict with `dry_run` and the `request` UBI would have sent. The `order_id` is None unless the outcome is `accepted`.

        Raises:
            BadRequestError: A field is invalid, or the price fields do not fit the order type.
            NotFoundError: No broker has a mapping for this instrument.
            OrderRejectedError: The broker refused the order, and the detail holds its answer.
            ServiceUnavailableError: No broker could take the order.
            OrderOutcomeUnknownError: The order was sent but its outcome is unknown, so read the order book before sending it again.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        body = {
            "instrument_id": self.instrument_id,
            "transaction_type": transaction_type,
            "order_type": order_type,
            "quantity": quantity,
            "product": product,
            "after_market": after_market,
            "dry_run": dry_run,
        }
        optional_fields = {
            "price": price,
            "trigger_price": trigger_price,
            "validity": validity,
            "disclosed_quantity": disclosed_quantity,
            "tag": tag,
        }
        for field, value in optional_fields.items():
            if value is not None:
                body[field] = value
        return self._unified_broker_interface.post(ORDER_PLACE_PATH, body=body)

    def modify_order(
        self,
        order_id: str,
        quantity: int | None = None,
        price: float | None = None,
        trigger_price: float | None = None,
        order_type: str | None = None,
        validity: str | None = None,
        disclosed_quantity: int | None = None,
        broker: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Changes one pending order through UBI.

        UBI finds the order by its id in the brokers' order books, so this does not check that the order belongs to this instrument. Give at least one field to change; every field left as None keeps the value the order already has.

        Args:
            order_id: The str id the broker gave the order, as `place_order` returned it.
            quantity: The int new total quantity in underlying units, counting what is already filled, or None to leave it.
            price: The float new limit price in rupees, or None to leave it.
            trigger_price: The float new trigger price in rupees, or None to leave it.
            order_type: The str new kind of order, `market`, `limit`, `sl` or `sl-m`, or None to leave it.
            validity: The str new validity, `day` or `ioc`, or None to leave it.
            disclosed_quantity: The int new quantity to show on the exchange, or None to leave it.
            broker: The str name of the broker holding the order, which is needed only after a ConflictError reporting that two brokers share the id, or None.
            dry_run: A bool that is True to have UBI build the broker's request and return it without sending it.

        Returns:
            A dict with `broker`, `order_id`, `instrument_id`, `status_before_modify`, `outcome`, `status_message`, `broker_response` and `timing_ms`, or, for a dry run, a dict with `dry_run` and the `request` UBI would have sent.

        Raises:
            BadRequestError: No field was given to change, or a field is invalid or is one this broker cannot change.
            NotFoundError: No broker's order book holds this order id.
            ConflictError: The order is already complete, cancelled, rejected or expired, or two brokers hold the id and the detail lists them under `brokers`.
            OrderRejectedError: The broker refused the change, and the detail holds its answer.
            OrderOutcomeUnknownError: The change was sent but its outcome is unknown.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        body = {
            "order_id": order_id,
            "dry_run": dry_run,
        }
        changeable_fields = {
            "quantity": quantity,
            "price": price,
            "trigger_price": trigger_price,
            "order_type": order_type,
            "validity": validity,
            "disclosed_quantity": disclosed_quantity,
            "broker": broker,
        }
        for field, value in changeable_fields.items():
            if value is not None:
                body[field] = value
        return self._unified_broker_interface.put(ORDER_MODIFY_PATH, body=body)

    def cancel_order(
        self,
        order_id: str,
        broker: str | None = None,
        dry_run: bool = False,
    ) -> dict:
        """Cancels one pending order through UBI.

        UBI finds the order by its id in the brokers' order books, so this does not check that the order belongs to this instrument.

        Args:
            order_id: The str id the broker gave the order, as `place_order` returned it.
            broker: The str name of the broker holding the order, which is needed only after a ConflictError reporting that two brokers share the id, or None.
            dry_run: A bool that is True to have UBI build the broker's request and return it without sending it.

        Returns:
            A dict with `broker`, `order_id`, `status_before_cancel`, `outcome`, `status_message`, `broker_response` and `timing_ms`, or, for a dry run, a dict with `dry_run` and the `request` UBI would have sent.

        Raises:
            BadRequestError: The order id, broker or dry run flag is malformed.
            NotFoundError: No broker's order book holds this order id.
            ConflictError: The order is already complete, cancelled, rejected or expired, or two brokers hold the id and the detail lists them under `brokers`.
            OrderRejectedError: The broker refused the cancellation, and the detail holds its answer.
            OrderOutcomeUnknownError: The cancellation was sent but its outcome is unknown.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        body = {
            "order_id": order_id,
            "dry_run": dry_run,
        }
        if broker is not None:
            body["broker"] = broker
        return self._unified_broker_interface.delete(ORDER_CANCEL_PATH, body=body)

    def orders(self, open_only: bool = False) -> pd.DataFrame | None:
        """Fetches today's orders in this instrument.

        UBI serves the whole account's order book and has no endpoint for one instrument, so this reads the book and keeps its own rows. The book is not merged across brokers, so one order placed at one broker appears once, and the same instrument traded at two brokers gives a row from each.

        Args:
            open_only: A bool that is True to keep only the orders that can still be changed or cancelled, which are the ones whose status is `PENDING` or `OPEN`.

        Returns:
            A pandas.DataFrame with UBI's order fields, among them `broker`, `order_id`, `status`, `transaction_type`, `product`, `order_type`, `quantity`, `filled_quantity`, `price`, `trigger_price`, `average_price` and `order_timestamp`, or None when this instrument has no such orders today.

        Raises:
            BrokerError: No broker's order book could be read.
            ServiceUnavailableError: UBI's order book document is missing or too old to serve.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        rows = self._unified_broker_interface.get(ORDER_DETAILS_PATH)["orders"]
        if open_only:
            open_rows = []
            for row in rows:
                if row["status"] in OPEN_ORDER_STATUSES:
                    open_rows.append(row)
            rows = open_rows
        return self._frame_for_this_instrument(rows)

    def trades(self) -> pd.DataFrame | None:
        """Fetches today's trades in this instrument.

        UBI serves the whole account's trade book and has no endpoint for one instrument, so this reads the book and keeps its own rows. One order can produce several trades, and each trade names the order it came from.

        Returns:
            A pandas.DataFrame with UBI's trade fields, among them `broker`, `trade_id`, `order_id`, `transaction_type`, `product`, `quantity`, `price`, `value` and `trade_timestamp`, or None when this instrument has no trades today.

        Raises:
            BrokerError: No broker's trade book could be read.
            ServiceUnavailableError: UBI's trade book document is missing or too old to serve.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        rows = self._unified_broker_interface.get(ORDER_TRADES_PATH)["trades"]
        return self._frame_for_this_instrument(rows)

    @property
    def net_positions(self) -> pd.DataFrame | None:
        """The positions held in this instrument now, merged across every broker.

        This is UBI's `net` bucket, which counts everything open in this instrument whenever it was opened, as against `day_positions`, which counts only today.

        A position is what a derivative or an intraday trade leaves open, as against a holding, which is a share kept in the demat account and belongs to `Equity` instead.

        Reading this sends one request to UBI every time, because UBI serves the whole account's positions and has no endpoint for a single instrument. UBI merges the brokers' positions by instrument and product, so one instrument gives one row per product it is held under, and no row names a broker.

        Returns:
            A pandas.DataFrame with `instrument_id`, `symbol`, `exchange`, `segment`, `product`, `quantity`, `buy`, `sell`, `average_price`, `last_price`, `pnl`, `day_change` and `day_change_percentage`, where `quantity` is positive when long and negative when short, or None when nothing is held in this instrument.

        Raises:
            BrokerError: No broker's positions could be read.
            ServiceUnavailableError: UBI's positions document is missing or too old to serve.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        rows = self._unified_broker_interface.get(POSITIONS_PATH)["net"]
        return self._frame_for_this_instrument(rows)

    @property
    def day_positions(self) -> pd.DataFrame | None:
        """Today's own positions in this instrument, without what was carried in.

        This is UBI's `day` bucket. It has the same shape as `net_positions` and counts only what was opened and closed today, so it is usually empty even when `net_positions` is not, because only some brokers report a position on a day basis at all.

        Returns:
            A pandas.DataFrame with the same columns as `net_positions`, or None when no broker reports a day position in this instrument.

        Raises:
            BrokerError: No broker's positions could be read.
            ServiceUnavailableError: UBI's positions document is missing or too old to serve.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        rows = self._unified_broker_interface.get(POSITIONS_PATH)["day"]
        return self._frame_for_this_instrument(rows)

    def _frame_for_this_instrument(
        self,
        rows: list[dict],
    ) -> pd.DataFrame | None:
        """Keeps the rows belonging to this instrument and makes a frame of them.

        A row UBI could not trace back to an instrument carries a null `instrument_id` and is left out, because there is no other field that names this instrument reliably: a row's exchange is the broker's own code, such as `NSE_EQ`, and its trading symbol is the broker's own spelling of the contract.

        Args:
            rows: A list of dicts from one of UBI's order, trade or position documents, each with an `instrument_id`.

        Returns:
            A pandas.DataFrame of the matching rows, or None when no row belongs to this instrument.

        Raises:
            Nothing.
        """
        matching_rows = []
        for row in rows:
            if row["instrument_id"] == self.instrument_id:
                matching_rows.append(row)
        if not matching_rows:
            return None
        return pd.DataFrame(matching_rows)

    @staticmethod
    def _best_level(levels: list[dict]) -> dict | None:
        """Picks the best level from one side of an order book.

        Args:
            levels: A list of dicts with `price`, `quantity` and `orders`, best first.

        Returns:
            The first dict in levels, or None when levels is empty.

        Raises:
            Nothing.
        """
        if not levels:
            return None
        return levels[0]


class NonTradeableInstrument(Instrument):
    """An instrument that cannot be traded directly, which is an index."""

    def __init__(
        self,
        instrument_id: str | None = None,
        exchange: str | None = None,
        segment: str | None = None,
        symbol: str | None = None,
        underlying_symbol: str | None = None,
        expiry_date: datetime.date | str | None = None,
        strike_price: float | None = None,
        option_type: str | None = None,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the instrument up in UBI and checks that it is an index.

        Args:
            instrument_id: The str UUID of the instrument, or None to look it up by exchange, segment and identity fields.
            exchange: The str exchange, such as `nse`, or None when instrument_id is given.
            segment: The str segment, bare such as `equity_indices` or prefixed such as `nse_equity_indices`, or None when instrument_id is given.
            symbol: The str symbol of the index, such as `NIFTY`, or None.
            underlying_symbol: The str symbol of an underlying, or None, since an index has none.
            expiry_date: An expiry as a datetime.date or a `YYYY-MM-DD` str, or None, since an index has none.
            strike_price: A float strike price, or None, since an index has none.
            option_type: A str option type, or None, since an index has none.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            NonTradeableInstrumentError: The instrument is not an index, so it can be traded.
            InstrumentError: UBI has no instrument matching the lookup.
            BadRequestError: The lookup is incomplete or malformed.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        super().__init__(
            instrument_id=instrument_id,
            exchange=exchange,
            segment=segment,
            symbol=symbol,
            underlying_symbol=underlying_symbol,
            expiry_date=expiry_date,
            strike_price=strike_price,
            option_type=option_type,
            unified_broker_interface=unified_broker_interface,
        )
        if not self.segment.endswith(INDEX_SEGMENT_SUFFIX):
            raise exceptions.NonTradeableInstrumentError(
                f"Only an index is a NonTradeableInstrument, and this can be traded: {self!r}"
            )
