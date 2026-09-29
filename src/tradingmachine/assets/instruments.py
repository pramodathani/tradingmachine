"""Instruments from UBI's unified instrument universe, with their candles, live prices and analysis.

`Instrument` looks an instrument up in UBI once, keeps its identity, lot size and tick size, and fetches candles and live prices on demand. It inherits every analysis class in `tradingmachine.assets.analysis`, so indicators, candlestick patterns, statistics and backtests are methods on the instrument. `TradeableInstrument` adds the values that come from the order book, the methods that place, change and cancel orders, a family of short methods that name the price to trade at rather than working it out, and this instrument's own orders, trades and positions. It refuses indices, and `NonTradeableInstrument` accepts only indices.

`Derivative` sits under `TradeableInstrument` and holds what every futures or option contract shares: its expiry, its underlying, which is kept when one is given to the constructor and otherwise looked up on every read through UBI's link or the family's default, its open interest range and the value of one lot. `Futures` adds the basis over the underlying, `Option` adds moneyness, intrinsic and time value, implied volatility and greeks, and both own the discovery class methods that the family classes such as `tradingmachine.assets.equities.EquityFutures` inherit by naming their segment in `SEGMENT`. `IndexFutures` and `IndexOption` narrow the two to contracts on an index.

Every index class, through `NonTradeableInstrument`, has a `constituents` property that returns the stored basket of the index's members from `tradingmachine.asset_baskets`, while the index's own price stays here.

Every call goes straight to UBI's REST API, which caches on its own side.

Typical usage example:

  infosys = instruments.TradeableInstrument(exchange="nse", segment="equities", symbol="INFY")
  frame = infosys.relative_strength_index(window=14, days=365)
  spread = infosys.bid_offer_spread

  placed = infosys.buy_at_best_bid_price(quantity=1, product="cnc")
  waiting = infosys.open_orders
  infosys.cancel_open_orders()

  nifty = instruments.NonTradeableInstrument(exchange="nse", segment="equity_indices", symbol="NIFTY")
  level = nifty.last_price

  contract = instruments.Option(instrument_id="1c39032e-270b-51e0-aa0b-fa0e1072928d")
  days_left = contract.days_to_expiry
  sensitivities = contract.greeks()
"""

from typing import TYPE_CHECKING

import datetime
import decimal
import zoneinfo

import pandas as pd

from tradingmachine.assets import exceptions
from tradingmachine.assets import option_pricing
from tradingmachine.assets.analysis import candlestick_patterns
from tradingmachine.assets.analysis import cycle_indicators
from tradingmachine.assets.analysis import math_operators
from tradingmachine.assets.analysis import math_transforms
from tradingmachine.assets.analysis import momentum_indicators
from tradingmachine.assets.analysis import overlap_studies
from tradingmachine.assets.analysis import performance_measures
from tradingmachine.assets.analysis import price_statistics
from tradingmachine.assets.analysis import price_transforms
from tradingmachine.assets.analysis import signals
from tradingmachine.assets.analysis import statistic_functions
from tradingmachine.assets.analysis import strategy_backtests
from tradingmachine.assets.analysis import volatility_indicators
from tradingmachine.assets.analysis import volume_indicators
from tradingmachine.unified_broker_interface import client
from tradingmachine.unified_broker_interface import exceptions as ubi_exceptions

if TYPE_CHECKING:
    from tradingmachine.asset_baskets import asset_basket

INDIA_TIME_ZONE = zoneinfo.ZoneInfo("Asia/Kolkata")

INDEX_SEGMENT_SUFFIX = "_indices"

INDEX_FUTURES_SEGMENT_SUFFIX = "_index_futures"

INDEX_OPTIONS_SEGMENT_SUFFIX = "_index_options"

FUTURE_SHAPE = "future"

FUTURES_SEGMENT_SUFFIX = "_futures"

OPTION_SHAPE = "option"

DERIVATIVE_SHAPES = [
    FUTURE_SHAPE,
    OPTION_SHAPE,
]

CALL_OPTION_TYPE = "CE"

PUT_OPTION_TYPE = "PE"

WEEKLY_EXPIRY_KIND = "weekly"

MONTHLY_EXPIRY_KIND = "monthly"

EXPIRY_TIME = datetime.time(15, 30)

DAYS_PER_YEAR = 365

SECONDS_PER_YEAR = DAYS_PER_YEAR * 24 * 60 * 60

PERCENT = 100

BLACK_76_MODEL = "black_76"

BLACK_SCHOLES_MODEL = "black_scholes"

UNDERLYING_SEGMENT_FOR_DERIVATIVE_SEGMENT = {
    "equity_futures": "equities",
    "equity_options": "equities",
    "equity_index_futures": "equity_indices",
    "equity_index_options": "equity_indices",
    "fixed_income_futures": None,
    "fixed_income_options": "fixed_income_futures",
    "fixed_income_index_futures": None,
    "fixed_income_index_options": "fixed_income_index_futures",
    "commodity_futures": None,
    "commodity_options": "commodity_futures",
    "commodity_index_futures": None,
    "commodity_index_options": "commodity_index_futures",
    "currency_futures": None,
    "currency_options": "currency_futures",
    "currency_index_futures": None,
    "currency_index_options": "currency_index_futures",
}

SEARCH_PATH = "/api/instruments/search"

LAST_PRICE_PATH = "/api/instruments/ltp"

MASTER_PATH = "/api/instruments/master"

ORDER_DETAILS_PATH = "/api/orders/details"

ORDER_TRADES_PATH = "/api/orders/trades"

ORDER_PLACE_PATH = "/api/orders/place"

ORDER_MODIFY_PATH = "/api/orders/modify"

ORDER_CANCEL_PATH = "/api/orders/cancel"

ORDER_PARENTS_PATH = "/api/orders/parents"

POSITIONS_PATH = "/api/portfolio/positions"

OPEN_ORDER_STATUSES = [
    "PENDING",
    "OPEN",
]

COMPLETED_ORDER_STATUSES = [
    "COMPLETE",
]

REJECTED_ORDER_STATUSES = [
    "REJECTED",
]

CANCELLED_ORDER_STATUSES = [
    "CANCELLED",
]

POSITION_PRODUCT_FOR_ORDER_PRODUCT = {
    "cnc": "delivery",
    "mis": "intraday",
    "nrml": "carry",
}

ORDER_PRODUCT_FOR_POSITION_PRODUCT = {
    "delivery": "cnc",
    "intraday": "mis",
    "carry": "nrml",
}


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
    performance_measures.PerformanceMeasures,
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
        underlying_instrument_id: The str UUID UBI gives for the instrument a future or option is written on, or None for a security or when UBI does not say.
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
        details: dict | None = None,
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
            details: The dict UBI returned for this instrument from `/api/instruments/details`, such as one entry of a list request, which is used instead of looking the instrument up again, or None to look it up from the other arguments.

        Raises:
            InstrumentError: UBI has no instrument matching the lookup.
            BadRequestError: The lookup is incomplete or malformed, such as a future without an expiry_date.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        if unified_broker_interface is None:
            unified_broker_interface = Instrument.shared_unified_broker_interface()
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
        if details is None:
            details = self._fetch_details(lookup)
        self._apply_details(details)

    def _apply_details(self, details: dict) -> None:
        """Copies the instrument's identity, lot size and tick size from UBI's details.

        Args:
            details: The dict UBI returns from `/api/instruments/details` for this instrument.

        Returns:
            None.

        Raises:
            KeyError: details lacks a field every UBI details answer carries, such as `instrument_id`.
            ValueError: A date in details is not a valid ISO date.
        """
        self.instrument_id = details["instrument_id"]
        self.exchange = details["exchange"]
        self.segment = details["segment"]
        self.shape = details["shape"]
        self.symbol = details["symbol"]
        self.underlying_symbol = details["underlying_symbol"]
        self.expiry_date = self._parse_date(details["expiry_date"])
        self.strike_price = details["strike_price"]
        self.option_type = details["option_type"]
        self.underlying_instrument_id = details.get("underlying_instrument_id")
        self.mapping_date = self._parse_date(details["mapping_date"])
        self.first_seen_date = self._parse_date(details["first_seen_date"])
        self.last_seen_date = self._parse_date(details["last_seen_date"])
        self.lot_size = details.get("lot_size")
        self.tick_size = self._parse_decimal(details.get("tick_size"))
        self.carried_by = details["carried_by"]

    @classmethod
    def shared_unified_broker_interface(
        cls,
    ) -> client.UnifiedBrokerInterface:
        """Returns the one client all instruments share, creating it on first use.

        UBI holds a single access token, so separate clients would keep replacing each other's token. The client is stored on `Instrument` itself rather than on cls, so subclasses share the same one. It is public so that code outside the instruments, such as `tradingmachine.accounts.account.Account`, can share it too.

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

    @classmethod
    def _search_catalogue(
        cls,
        exchange: str,
        segment: str,
        term: str,
        limit: int,
        unified_broker_interface: client.UnifiedBrokerInterface | None,
    ) -> pd.DataFrame | None:
        """Finds instruments in one segment whose name contains a term.

        UBI ranks an exact match first, then names starting with the term, then names containing it. This is the right way to look for a security by name, and the wrong way to look for a contract: UBI returns at most 200 rows in expiry order and offers no way to page past them, so for a segment with many expiries every row comes from the oldest one. Use `_contracts_for` for a future or an option.

        Args:
            exchange: The str exchange to search, such as `nse`.
            segment: The str segment to search, bare such as `equities` or prefixed such as `nse_equities`.
            term: The str the name must contain, matched without regard to case.
            limit: The int most rows to return, which UBI caps at 200.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame of identities, with `instrument_id`, `exchange`, `segment`, `shape`, `symbol`, `underlying_symbol`, `expiry_date`, `strike_price` and `option_type`, or None when nothing matches.

        Raises:
            BadRequestError: The exchange or segment is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        if unified_broker_interface is None:
            unified_broker_interface = cls.shared_unified_broker_interface()
        answer = unified_broker_interface.get(
            SEARCH_PATH,
            params={
                "exchange": exchange,
                "segment": segment,
                "q": term,
                "limit": limit,
            },
        )
        return cls._identity_frame(answer["instruments"])

    @classmethod
    def _master_catalogue(
        cls,
        exchange: str,
        segment: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None,
    ) -> pd.DataFrame | None:
        """Fetches every instrument UBI holds in one segment.

        There is no limit on this, and UBI streams it, so even the largest segment arrives in a second or two. It is the only way to reach a live expiry in a segment whose oldest expiries fill the search route's 200 rows.

        Args:
            exchange: The str exchange, such as `nse`.
            segment: The str segment, bare such as `equity_options` or prefixed such as `nse_equity_options`.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame of every identity in the segment, shaped as `_search_catalogue` returns, or None when the segment holds nothing.

        Raises:
            BadRequestError: The exchange or segment is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        if unified_broker_interface is None:
            unified_broker_interface = cls.shared_unified_broker_interface()
        rows = unified_broker_interface.get(
            MASTER_PATH,
            params={
                "exchange": exchange,
                "segment": segment,
            },
        )
        return cls._identity_frame(rows)

    @classmethod
    def _contracts_for(
        cls,
        exchange: str,
        segment: str,
        underlying_symbol: str | None,
        expiry_date: datetime.date | str | None,
        include_expired: bool,
        unified_broker_interface: client.UnifiedBrokerInterface | None,
    ) -> pd.DataFrame | None:
        """Finds the contracts in one segment, narrowed by underlying and expiry.

        The whole segment is fetched and narrowed here, because UBI's search route cannot reach a live expiry and its master route takes no filters.

        Args:
            exchange: The str exchange, such as `nse`.
            segment: The str segment of the contracts, such as `equity_options`.
            underlying_symbol: The str symbol of the underlying to keep, or None to keep every underlying.
            expiry_date: The expiry to keep, as a datetime.date or a `YYYY-MM-DD` str, or None to keep every expiry.
            include_expired: A bool that is True to keep contracts whose expiry has passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame of the matching identities, sorted by expiry, strike price and option type, or None when nothing matches.

        Raises:
            BadRequestError: The exchange or segment is not one UBI knows.
            ValueError: expiry_date is a str that is not a valid ISO date.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        frame = cls._master_catalogue(
            exchange,
            segment,
            unified_broker_interface,
        )
        if frame is None:
            return None
        wanted_expiry = expiry_date
        if isinstance(wanted_expiry, str):
            wanted_expiry = datetime.date.fromisoformat(wanted_expiry)
        today = datetime.datetime.now(INDIA_TIME_ZONE).date()
        kept_rows = []
        for row in frame.to_dict("records"):
            if underlying_symbol is not None:
                if row["underlying_symbol"] != underlying_symbol.upper():
                    continue
            if row["expiry_date"] is None:
                continue
            if wanted_expiry is not None and row["expiry_date"] != wanted_expiry:
                continue
            if not include_expired and row["expiry_date"] < today:
                continue
            kept_rows.append(row)
        if not kept_rows:
            return None
        kept_frame = pd.DataFrame(kept_rows)
        sorted_frame = kept_frame.sort_values(
            [
                "expiry_date",
                "strike_price",
                "option_type",
            ],
            na_position="first",
        )
        return sorted_frame.reset_index(drop=True)

    @classmethod
    def _expiry_dates(
        cls,
        exchange: str,
        segment: str,
        underlying_symbol: str,
        include_expired: bool,
        unified_broker_interface: client.UnifiedBrokerInterface | None,
    ) -> list[datetime.date]:
        """Lists the expiries one underlying has contracts for in a segment.

        Args:
            exchange: The str exchange, such as `nse`.
            segment: The str segment of the contracts, such as `equity_futures`.
            underlying_symbol: The str symbol of the underlying, such as `RELIANCE`.
            include_expired: A bool that is True to include expiries that have passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of datetime.date, soonest first, which is empty when the underlying has no contracts.

        Raises:
            BadRequestError: The exchange or segment is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        frame = cls._contracts_for(
            exchange,
            segment,
            underlying_symbol,
            None,
            include_expired,
            unified_broker_interface,
        )
        if frame is None:
            return []
        return sorted(set(frame["expiry_date"]))

    @classmethod
    def _identity_frame(cls, rows: list[dict]) -> pd.DataFrame | None:
        """Turns UBI's identity rows into a frame, with real dates in it.

        Args:
            rows: A list of dicts as UBI's search and master routes return them.

        Returns:
            A pandas.DataFrame of the rows, with `expiry_date` as a datetime.date, or None when there are no rows.

        Raises:
            ValueError: An expiry date is not a valid ISO date.
        """
        if not rows:
            return None
        dated_rows = []
        for row in rows:
            dated_row = dict(row)
            expiry_date = row.get("expiry_date")
            if not expiry_date:
                dated_row["expiry_date"] = None
            else:
                dated_row["expiry_date"] = cls._parse_date(expiry_date)
            dated_rows.append(dated_row)
        return pd.DataFrame(dated_rows)

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

    @property
    def quote(self) -> dict:
        """The instrument's full unified quote, read from UBI on every access.

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

    @property
    def last_price(self) -> float | None:
        """The instrument's last traded price, read from UBI on every access.

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

    @property
    def ohlc(self) -> dict:
        """The day's open, high and low with the last and previous close prices, read from UBI on every access.

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
        details: dict | None = None,
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
            details: The dict UBI returned for this instrument from `/api/instruments/details`, such as one entry of a list request, which is used instead of looking the instrument up again, or None to look it up from the other arguments.

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
            details=details,
        )
        if self.segment.endswith(INDEX_SEGMENT_SUFFIX):
            raise exceptions.TradeableInstrumentError(
                f"An index cannot be traded, so it is not a TradeableInstrument: {self!r}"
            )

    @property
    def bids(self) -> list[dict]:
        """The buy side of the order book, read from UBI on every access.

        Returns:
            A list of up to five dicts with `price`, `quantity` and `orders`, best first, which is empty when nobody is bidding.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        return self.quote["depth"]["buy"]

    @property
    def asks(self) -> list[dict]:
        """The sell side of the order book, read from UBI on every access.

        Returns:
            A list of up to five dicts with `price`, `quantity` and `orders`, best first, which is empty when nobody is offering.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        return self.quote["depth"]["sell"]

    @property
    def best_bid(self) -> dict | None:
        """The highest bid in the order book.

        Returns:
            A dict with `price`, `quantity` and `orders`, or None when nobody is bidding.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        return self._best_level(self.bids)

    @property
    def best_offer(self) -> dict | None:
        """The lowest offer in the order book.

        Returns:
            A dict with `price`, `quantity` and `orders`, or None when nobody is offering.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        return self._best_level(self.asks)

    @property
    def bid_offer_spread(self) -> float | None:
        """The gap between the best offer and the best bid, measured from one quote.

        Returns:
            The float spread in rupees, or None when either side of the order book is empty.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        depth = self.quote["depth"]
        best_bid = self._best_level(depth["buy"])
        best_offer = self._best_level(depth["sell"])
        if best_bid is None or best_offer is None:
            return None
        return best_offer["price"] - best_bid["price"]

    @property
    def mid_price(self) -> float | None:
        """The price halfway between the best bid and the best offer, from one quote.

        Returns:
            The float mid price in rupees, or None when either side of the order book is empty.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        depth = self.quote["depth"]
        best_bid = self._best_level(depth["buy"])
        best_offer = self._best_level(depth["sell"])
        if best_bid is None or best_offer is None:
            return None
        return (best_bid["price"] + best_offer["price"]) / 2

    @property
    def volume_weighted_average_price(self) -> float | None:
        """Today's volume weighted average price.

        Returns:
            The float price in rupees, or None when the broker serving the quote does not report it.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        return self.quote["average_price"]

    @property
    def last_quantity(self) -> int | None:
        """The quantity of the last trade.

        Returns:
            The int quantity in underlying units, not lots, or None when unknown.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        return self.quote["last_quantity"]

    @property
    def total_traded_volume(self) -> int | None:
        """The quantity traded so far today.

        Returns:
            The int volume in underlying units, not lots, or None when unknown.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        return self.quote["volume"]

    @property
    def open_interest(self) -> int | None:
        """The open interest of a future or an option.

        Returns:
            The int open interest in underlying units, or None for a security or when unknown.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        return self.quote["oi"]

    @property
    def last_trade_time(self) -> datetime.datetime | None:
        """When the last trade happened.

        Returns:
            The time as a datetime.datetime in India time, or None when the broker does not send one reliably.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        epoch_seconds = self.quote["last_trade_time"]
        if epoch_seconds is None:
            return None
        return datetime.datetime.fromtimestamp(epoch_seconds, INDIA_TIME_ZONE)

    def place_order(
        self,
        transaction_type: str,
        order_type: str,
        quantity: int | None,
        product: str,
        price: float | None = None,
        trigger_price: float | None = None,
        validity: str | None = None,
        disclosed_quantity: int | None = None,
        after_market: bool = False,
        tag: str | None = None,
        dry_run: bool = False,
        price_reference: dict | None = None,
        quantity_reference: dict | None = None,
        synthetic: dict | None = None,
    ) -> dict:
        """Places one order in this instrument through UBI.

        UBI chooses the broker itself, so no broker is named here. The values are sent exactly as given, without rounding the price to the tick size or checking the quantity against the lot size, because UBI and the broker behind it hold those rules.

        UBI couples the price fields to the order type and answers HTTP 400 when they do not agree: a `limit` or `sl` order needs a price, an `sl` or `sl-m` order needs a trigger price, and a `market` or `sl-m` order must carry no price at all. A `price_reference` stands in for the price and a `quantity_reference` for the quantity.

        An outcome of `accepted` means the broker took the order, not that the order survived. The exchange can still refuse it afterwards, which is what happens to an ordinary order sent while the market is closed, so the order's real fate is read from `orders` rather than from this answer. Neither this class nor UBI checks the market's hours, so use `after_market` to queue an order for the next session.

        Every order goes through UBI's order engine, which is the only way UBI places orders. A plain `limit` order with a price of its own, `day` validity, no `synthetic` object and `after_market` False is not sent to a broker straight away: the engine holds it as a `virtual_limit` order and sends it only once the other side of the book reaches its price, answering HTTP 202 with an outcome of `armed`, a `parent_id` and no `order_id`. Such a held order is changed with `modify_order(parent_id=...)` and cancelled with `cancel_parent`, and it never appears in `orders` until it has been sent. Pass `synthetic={"type": "simple"}` to send a limit order at once, which matters for an instrument that has no live quote, because the engine would hold its order for the whole day without ever sending it.

        Args:
            transaction_type: The str side of the order, `buy` or `sell`. UBI overrides it for a quantity reference that reduces or closes a position.
            order_type: The str kind of order, `market`, `limit`, `sl` or `sl-m`.
            quantity: The int quantity in underlying units, not lots, or None when a quantity reference supplies it.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            price: The float limit price in rupees, or None for an order type that takes no price or when a price reference supplies it.
            trigger_price: The float trigger price in rupees, or None for an order type that takes no trigger.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            disclosed_quantity: The int quantity to show on the exchange, or None to disclose the whole order.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.
            dry_run: A bool that is True to have UBI build the broker's request and return it without sending it.
            price_reference: A dict that describes the price instead of stating it, such as `{"kind": "offer_level", "level": 2}`, which UBI resolves from the live quote and rounds to the tick, or None. Its `kind` is `absolute`, `bid_level`, `offer_level`, `mid`, `vwap`, `last` or `marketable`, and it may carry `price`, `level`, `buffer_percent`, `offset_percent` and `offset_ticks`.
            quantity_reference: A dict that describes the quantity instead of stating it, such as `{"kind": "liquidate_position", "product": "intraday"}`, which UBI resolves from the positions, or None. Its `kind` is `add_to_position`, `reduce_position` or `liquidate_position`, and its optional `product` is spelled the positions' way.
            synthetic: A dict that makes the order one of UBI's synthetic order types, such as `{"type": "bracket", "stop_price": 990, "stop_limit_price": 988, "target_price": 1010}`, or None for a plain order. The classes in `tradingmachine.orders` build it.

        Returns:
            A dict with `broker`, `instrument_id`, `order_id`, `outcome`, `status_message`, `broker_response`, `skipped`, `timing_ms` and `intent_id`, and `parent_id` for an order the engine recorded, or, for a dry run, a dict with `dry_run` and the `request` UBI would have sent. The `order_id` is None unless the outcome is `accepted`. A held limit order, and a synthetic order that is waiting for a price or a time, answers with an outcome of `armed` or `scheduled` and a `broker` and `order_id` of None. The types that send several orders at once add a list of `order_ids`, and their `outcome` is `partial` when some of those orders were accepted and some were not.

        Raises:
            BadRequestError: A field is invalid, the price fields do not fit the order type, or a synthetic order's own fields are wrong.
            LossLockoutError: The day's loss is past UBI's daily loss limit.
            NotFoundError: No broker has a mapping for this instrument.
            ConflictError: A quantity reference asked to reduce or close a position that is not held, a reduce-only order would not reduce the position, or the engine read the order too late or had already started it before a restart.
            OrderRejectedError: The broker refused the order, and the detail holds its answer.
            RateLimitError: The broker's daily order cap has no room for this order.
            ServiceUnavailableError: No broker could take the order, the order engine is not running, or a price reference could not be resolved.
            OrderOutcomeUnknownError: The order was sent but its outcome is unknown, so read the order book, or `Account.intent` with the detail's `intent_id`, before sending it again.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        body = {
            "instrument_id": self.instrument_id,
            "transaction_type": transaction_type,
            "order_type": order_type,
            "product": product,
            "after_market": after_market,
            "dry_run": dry_run,
        }
        optional_fields = {
            "quantity": quantity,
            "price": price,
            "trigger_price": trigger_price,
            "validity": validity,
            "disclosed_quantity": disclosed_quantity,
            "tag": tag,
            "price_reference": price_reference,
            "quantity_reference": quantity_reference,
            "synthetic": synthetic,
        }
        for field, value in optional_fields.items():
            if value is not None:
                body[field] = value
        return self._unified_broker_interface.post(ORDER_PLACE_PATH, body=body)

    def modify_order(
        self,
        order_id: str | None = None,
        quantity: int | None = None,
        price: float | None = None,
        trigger_price: float | None = None,
        order_type: str | None = None,
        validity: str | None = None,
        disclosed_quantity: int | None = None,
        broker: str | None = None,
        dry_run: bool = False,
        parent_id: str | None = None,
    ) -> dict:
        """Changes one pending order through UBI.

        UBI finds the order by its id in the brokers' order books, so this does not check that the order belongs to this instrument. Give at least one field to change; every field left as None keeps the value the order already has.

        Those order books are copies that UBI's own collectors refresh every few seconds, so an order placed a moment ago is not in them yet and raises NotFoundError. Wait for the order to appear in `orders` before changing it.

        An order that is a leg of one of UBI's synthetic orders is handed to the engine, which lets the order type carry on from the change, so a trailing stop trails from the new trigger. Only its `price`, `trigger_price` and `quantity` can change, and anything else raises ConflictError.

        An order the engine is still holding, such as a plain limit order waiting for the other side to reach its price, has no broker order id yet. Name it by the `parent_id` that `place_order` answered with instead of `order_id`; only its `price` and `quantity` can change, and nothing is sent to a broker.

        Args:
            order_id: The str id the broker gave the order, as `place_order` returned it, or None when naming a held order by `parent_id`.
            quantity: The int new total quantity in underlying units, counting what is already filled, or None to leave it.
            price: The float new limit price in rupees, or None to leave it.
            trigger_price: The float new trigger price in rupees, or None to leave it.
            order_type: The str new kind of order, `market`, `limit`, `sl` or `sl-m`, or None to leave it.
            validity: The str new validity, `day` or `ioc`, or None to leave it.
            disclosed_quantity: The int new quantity to show on the exchange, or None to leave it.
            broker: The str name of the broker holding the order, which is needed only after a ConflictError reporting that two brokers share the id, or None.
            dry_run: A bool that is True to have UBI build the broker's request and return it without sending it.
            parent_id: The str id of an order the engine is still holding, as `place_order` returned it, or None when naming a broker order by `order_id`.

        Returns:
            A dict with `broker`, `order_id`, `instrument_id`, `status_before_modify`, `outcome`, `status_message`, `broker_response` and `timing_ms`, and `parent_id` and `synthetic_type` for a leg of a synthetic order, or, for a dry run, a dict with `dry_run` and the `request` UBI would have sent. A held order answers with `parent_id`, `synthetic_type`, `held` set to True, the new `price` and `quantity`, and an `outcome` of `accepted`.

        Raises:
            BadRequestError: No field was given to change, or a field is invalid or is one this broker cannot change.
            NotFoundError: No broker's order book holds this order id, or the engine holds no parent with this parent id.
            ConflictError: The order is already complete, cancelled, rejected or expired, two brokers hold the id and the detail lists them under `brokers`, a leg of a synthetic order was asked to change a field other than its price, trigger price or quantity, or a held order has already been sent, when the detail names its `broker` and `order_id`.
            OrderRejectedError: The broker refused the change, and the detail holds its answer.
            ServiceUnavailableError: The broker's order rate budget was full, so the change was not sent.
            OrderOutcomeUnknownError: The change was sent but its outcome is unknown.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        body = {
            "dry_run": dry_run,
        }
        changeable_fields = {
            "order_id": order_id,
            "parent_id": parent_id,
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

        Those order books are copies that UBI's own collectors refresh every few seconds, so an order placed a moment ago is not in them yet and raises NotFoundError. Wait for the order to appear in `orders` before cancelling it.

        An order that is a leg of one of UBI's synthetic orders is cancelled through the engine, so the order type knows about it, but the synthetic order itself carries on. Use `cancel_parent` to stop a synthetic order, or to cancel an order the engine is still holding, which has no broker order id.

        Args:
            order_id: The str id the broker gave the order, as `place_order` returned it.
            broker: The str name of the broker holding the order, which is needed only after a ConflictError reporting that two brokers share the id, or None.
            dry_run: A bool that is True to have UBI build the broker's request and return it without sending it.

        Returns:
            A dict with `broker`, `order_id`, `status_before_cancel`, `outcome`, `status_message`, `broker_response` and `timing_ms`, and `parent_id` and `synthetic_type` for a leg of a synthetic order, or, for a dry run, a dict with `dry_run` and the `request` UBI would have sent.

        Raises:
            BadRequestError: The order id, broker or dry run flag is malformed.
            NotFoundError: No broker's order book holds this order id.
            ConflictError: The order is already complete, cancelled, rejected or expired, or two brokers hold the id and the detail lists them under `brokers`.
            OrderRejectedError: The broker refused the cancellation, and the detail holds its answer.
            ServiceUnavailableError: The broker's order rate budget was full, so the cancellation was not sent.
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

    def cancel_open_orders(self) -> pd.DataFrame | None:
        """Cancels every order in this instrument that is still waiting, whether at a broker or held in UBI's order engine.

        The engine's open parents in this instrument are cancelled first, each with the orders it has resting at a broker, because a synthetic order left running could place a new order after its old ones were cancelled. Then every open order in the order book that did not belong to one of those parents is cancelled in one request. Every order and parent is attempted even when an earlier one fails, and a failure is reported in the returned frame rather than raised, so one order that can no longer be cancelled does not leave the rest of them open.

        Returns:
            A pandas.DataFrame with one row per parent or order, holding `parent_id`, `order_id`, `broker`, `cancelled` and `error`, where `parent_id` is None for an order cancelled on its own, `order_id` and `broker` are None for a parent, and `error` is None for a cancel that was accepted and the status and message of the failure otherwise, or None when nothing in this instrument is waiting.

        Raises:
            BrokerError: No broker's order book could be read.
            ServiceUnavailableError: UBI's order book document is missing or too old to serve, or UBI's parents could not be read.
            UnifiedBrokerInterfaceError: The order book or the parents could not be read for any other reason, or the list of cancels was refused whole. A failure to cancel one order or parent is reported in the frame instead.
        """
        outcomes = []
        cancelled_parent_ids = []
        open_parents = self.parents
        if open_parents is not None:
            for parent_id in open_parents["parent_order_id"]:
                outcome, engine_answered = self._cancel_one_parent(parent_id)
                if engine_answered:
                    cancelled_parent_ids.append(parent_id)
                outcomes.append(outcome)
        open_orders = self.open_orders
        if open_orders is not None:
            orders_to_cancel = []
            for row in open_orders.to_dict("records"):
                if row.get("engine_parent_id") in cancelled_parent_ids:
                    continue
                orders_to_cancel.append(
                    {
                        "order_id": row["order_id"],
                        "broker": row["broker"],
                    }
                )
            outcomes.extend(self._cancel_order_list(orders_to_cancel))
        if not outcomes:
            return None
        return pd.DataFrame(outcomes)

    def _cancel_one_parent(self, parent_id: str) -> tuple[dict, bool]:
        """Cancels one parent for `cancel_open_orders`, reporting a failure rather than raising it.

        Args:
            parent_id: The str id of the parent to cancel.

        Returns:
            A tuple (outcome, engine_answered), where outcome is a dict with `parent_id`, `order_id`, `broker`, `cancelled` and `error` for the returned frame, and engine_answered is a bool that is True when the engine took the cancel, so the parent's own orders need no separate cancel.

        Raises:
            Nothing.
        """
        outcome = {
            "parent_id": parent_id,
            "order_id": None,
            "broker": None,
            "cancelled": True,
            "error": None,
        }
        try:
            answer = self.cancel_parent(parent_id)
        except ubi_exceptions.UnifiedBrokerInterfaceError as error:
            outcome["cancelled"] = False
            outcome["error"] = f"{type(error).__name__}: {error.message}"
            return outcome, False
        state = answer.get("state")
        if state != "cancelled":
            outcome["cancelled"] = False
            outcome["error"] = (
                f"the parent is {state}, because a broker refused or did not confirm the cancel of one of its orders"
            )
        return outcome, True

    def _cancel_order_list(self, orders_to_cancel: list[dict]) -> list[dict]:
        """Cancels broker orders in one request for `cancel_open_orders`, reporting each failure rather than raising it.

        Args:
            orders_to_cancel: A list of dicts, each with the `order_id` and `broker` of one order.

        Returns:
            A list of dicts, one per order in the same order, each with `parent_id`, `order_id`, `broker`, `cancelled` and `error` for the returned frame, which is empty when orders_to_cancel is.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the whole list, or could not be reached.
        """
        if not orders_to_cancel:
            return []
        answer = self._unified_broker_interface.delete(
            ORDER_CANCEL_PATH,
            body={
                "orders": orders_to_cancel,
            },
        )
        outcomes = []
        for result in answer["results"]:
            order = orders_to_cancel[result["request_index"]]
            outcome = {
                "parent_id": None,
                "order_id": order["order_id"],
                "broker": order["broker"],
                "cancelled": True,
                "error": None,
            }
            if result["status"] != 200:
                response = result["response"]
                message = response.get("error") or response.get("status_message")
                outcome["cancelled"] = False
                outcome["error"] = f"HTTP {result['status']}: {message}"
            outcomes.append(outcome)
        return outcomes

    @property
    def parents(self) -> pd.DataFrame | None:
        """The synthetic orders and held orders in this instrument that UBI's order engine has not finished.

        A parent is one order the engine was asked for, such as a bracket, a trailing stop or a held limit order, and its legs are the broker orders it placed. This is the only way to see a parent that has placed nothing yet, such as an armed trigger. UBI lists every open parent in the account, so this reads them all and keeps this instrument's own.

        Returns:
            A pandas.DataFrame with one row per parent, holding UBI's parent fields, among them `parent_order_id`, `synthetic_type`, `state`, `instrument_id`, `body`, `parameters` and `legs`, or None when no parent in this instrument is open.

        Raises:
            ServiceUnavailableError: UBI's parents could not be read.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        rows = self._unified_broker_interface.get(ORDER_PARENTS_PATH)["parents"]
        return self._frame_for_this_instrument(rows)

    def parent(self, parent_id: str) -> dict:
        """Reads one of the order engine's parents, whether or not it has finished.

        UBI finds the parent by its id alone, so this does not check that it belongs to this instrument.

        Args:
            parent_id: The str `parent_id` that `place_order` answered with.

        Returns:
            A dict holding the parent as the engine keeps it, with `parent_order_id`, `synthetic_type`, `state`, `instrument_id`, the caller's `body`, the type's `parameters` and one entry per leg under `legs`.

        Raises:
            NotFoundError: The order engine holds no parent with this id.
            ServiceUnavailableError: UBI's parents could not be read.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self._unified_broker_interface.get(
            ORDER_PARENTS_PATH,
            params={
                "parent_id": parent_id,
            },
        )

    def cancel_parent(self, parent_id: str) -> dict:
        """Cancels one of the order engine's parents, with every leg it still has resting at a broker.

        This is how a synthetic order is stopped and how an order the engine is still holding is cancelled. A position the parent has already opened is not closed.

        When a broker refuses the cancel of one leg, or its outcome is unknown, UBI answers HTTP 207, which is returned rather than raised, with the parent's `state` as `cancelling` rather than `cancelled`. The parent no longer acts, and becomes `cancelled` once the broker reports that leg finished, so read `cancelled_legs` to see which one may still be live, and call this again to retry it.

        Args:
            parent_id: The str `parent_id` that `place_order` answered with.

        Returns:
            A dict with `parent_id`, `synthetic_type`, `state`, `intent_id` and `cancelled_legs`, one entry per leg with its `leg_id`, `broker`, `order_id`, `outcome` and `status_message`.

        Raises:
            BadRequestError: The parent id is malformed.
            NotFoundError: The order engine holds no parent with this id.
            ConflictError: The parent has already finished.
            ServiceUnavailableError: The order engine is not running.
            OrderOutcomeUnknownError: The engine did not answer in time.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self._unified_broker_interface.delete(
            ORDER_PARENTS_PATH,
            body={
                "parent_id": parent_id,
            },
        )

    def parent_orders(self, parent_id: str) -> pd.DataFrame | None:
        """Today's broker orders that one of the order engine's parents placed.

        Args:
            parent_id: The str `parent_id` that `place_order` answered with.

        Returns:
            A pandas.DataFrame shaped like `orders`, whose `leg_role` column says what each order was to the parent, such as `entry`, `stop` or `target`, or None when the parent has placed nothing that the order book shows yet.

        Raises:
            BrokerError: No broker's order book could be read.
            ServiceUnavailableError: UBI's order book document is missing or too old to serve.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        rows = self._unified_broker_interface.get(
            ORDER_DETAILS_PATH,
            params={
                "parent_id": parent_id,
            },
        )["orders"]
        if not rows:
            return None
        return pd.DataFrame(rows)

    def parent_trades(self, parent_id: str) -> pd.DataFrame | None:
        """Today's trades in the broker orders that one of the order engine's parents placed.

        Args:
            parent_id: The str `parent_id` that `place_order` answered with.

        Returns:
            A pandas.DataFrame shaped like `trades`, or None when none of the parent's orders has traded.

        Raises:
            BrokerError: No broker's trade book could be read.
            ServiceUnavailableError: UBI's trade book document is missing or too old to serve.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        rows = self._unified_broker_interface.get(
            ORDER_TRADES_PATH,
            params={
                "parent_id": parent_id,
            },
        )["trades"]
        if not rows:
            return None
        return pd.DataFrame(rows)

    @property
    def orders(self) -> pd.DataFrame | None:
        """Every one of today's orders in this instrument, whatever its status.

        UBI serves the whole account's order book and has no endpoint for one instrument, so reading this reads the whole book and keeps this instrument's own rows. The book is not merged across brokers, so one order placed at one broker appears once, and the same instrument traded at two brokers gives a row from each.

        The `status` column holds UBI's own upper-case status, one of `PENDING`, `OPEN`, `COMPLETE`, `CANCELLED`, `REJECTED` or `EXPIRED`. An order still waiting in the market is `PENDING` at some brokers and `OPEN` at others, so `open_orders` is the way to ask for those, and `completed_orders`, `rejected_orders` and `cancelled_orders` give the other common groups already filtered. Any status without a member of its own, such as `EXPIRED`, is found by filtering this frame. An order UBI's order engine is still holding, such as a limit order waiting for the book to reach its price, has not reached a broker and is not here; it is in `parents`.

        Returns:
            A pandas.DataFrame with UBI's order fields, among them `broker`, `order_id`, `status`, `transaction_type`, `product`, `order_type`, `quantity`, `filled_quantity`, `price`, `trigger_price`, `average_price` and `order_timestamp`, and `engine_parent_id`, `leg_role`, `synthetic_type` and `intent_id`, which name the order engine parent that placed the order and are None for an order placed elsewhere, or None when this instrument has no orders today.

        Raises:
            BrokerError: No broker's order book could be read.
            ServiceUnavailableError: UBI's order book document is missing or too old to serve.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self._orders_with_status(None)

    @property
    def open_orders(self) -> pd.DataFrame | None:
        """Today's orders in this instrument that can still be changed.

        An order counts as open while it is waiting in the market, which UBI reports as `PENDING` at some brokers and `OPEN` at others. Those are the orders `modify_order` and `cancel_order` will accept; every other status is final. An order UBI's order engine is still holding has not reached the market, so it is not here; `parents` lists it.

        Returns:
            A pandas.DataFrame shaped like `orders`, or None when nothing is waiting in the market for this instrument.

        Raises:
            BrokerError: No broker's order book could be read.
            ServiceUnavailableError: UBI's order book document is missing or too old to serve.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self._orders_with_status(OPEN_ORDER_STATUSES)

    @property
    def completed_orders(self) -> pd.DataFrame | None:
        """Today's orders in this instrument that filled in full.

        Returns:
            A pandas.DataFrame shaped like `orders`, or None when nothing filled in this instrument today.

        Raises:
            BrokerError: No broker's order book could be read.
            ServiceUnavailableError: UBI's order book document is missing or too old to serve.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self._orders_with_status(COMPLETED_ORDER_STATUSES)

    @property
    def rejected_orders(self) -> pd.DataFrame | None:
        """Today's orders in this instrument that a broker or the exchange refused.

        The `status_message` column holds the reason each one was refused, in the words of whoever refused it.

        Returns:
            A pandas.DataFrame shaped like `orders`, or None when nothing was refused in this instrument today.

        Raises:
            BrokerError: No broker's order book could be read.
            ServiceUnavailableError: UBI's order book document is missing or too old to serve.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self._orders_with_status(REJECTED_ORDER_STATUSES)

    @property
    def cancelled_orders(self) -> pd.DataFrame | None:
        """Today's orders in this instrument that were cancelled.

        Returns:
            A pandas.DataFrame shaped like `orders`, or None when nothing was cancelled in this instrument today.

        Raises:
            BrokerError: No broker's order book could be read.
            ServiceUnavailableError: UBI's order book document is missing or too old to serve.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self._orders_with_status(CANCELLED_ORDER_STATUSES)

    def _orders_with_status(
        self,
        wanted_statuses: list[str] | None,
    ) -> pd.DataFrame | None:
        """Reads the order book and keeps this instrument's rows in the wanted statuses.

        Args:
            wanted_statuses: A list of upper-case UBI statuses to keep, or None to keep every status.

        Returns:
            A pandas.DataFrame of the matching rows, or None when no row matches.

        Raises:
            BrokerError: No broker's order book could be read.
            ServiceUnavailableError: UBI's order book document is missing or too old to serve.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        rows = self._unified_broker_interface.get(ORDER_DETAILS_PATH)["orders"]
        if wanted_statuses is None:
            return self._frame_for_this_instrument(rows)
        wanted_rows = []
        for row in rows:
            if row["status"] in wanted_statuses:
                wanted_rows.append(row)
        return self._frame_for_this_instrument(wanted_rows)

    @property
    def trades(self) -> pd.DataFrame | None:
        """Today's trades in this instrument.

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

    def buy_at_market_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Buys at whatever price the market is asking.

        A market order takes the best price on offer and fills straight away while the market is open. The price is therefore not known before the order is sent, and in a thin book it can be a good deal worse than the last traded price.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="buy",
            order_type="market",
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def sell_at_market_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Sells at whatever price the market is bidding.

        A market order takes the best price being bid and fills straight away while the market is open. The price is therefore not known before the order is sent, and in a thin book it can be a good deal worse than the last traded price.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="sell",
            order_type="market",
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def buy_at_limit_price(
        self,
        price: float,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
        hold: bool = True,
    ) -> dict:
        """Buys at a price of your choosing, or better.

        A limit buy never pays more than the price given. It waits in the market until someone sells at that price or lower, and it may never fill at all.

        UBI's order engine holds a `day` limit order that is not an after-market order rather than resting it at a broker, and sends it only once the other side of the book reaches the price, so an order that never fills costs no order messages. Until then `place_order` answers with an outcome of `armed` and a `parent_id` rather than an `order_id`, the order is not in `orders` but in `parents`, and it is changed with `modify_order(parent_id=...)` and cancelled with `cancel_parent`.

        Args:
            price: The float limit price in rupees.
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.
            hold: A bool that is True to let UBI's order engine hold a `day` order until the other side of the book reaches the price, and False to send it to a broker at once. An after-market order is always sent at once, whatever this says. Pass False for an instrument with no live quote, whose order the engine would otherwise hold all day without sending.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        synthetic = None
        if not hold:
            synthetic = {
                "type": "simple",
            }
        return self.place_order(
            transaction_type="buy",
            order_type="limit",
            price=price,
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
            synthetic=synthetic,
        )

    def sell_at_limit_price(
        self,
        price: float,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
        hold: bool = True,
    ) -> dict:
        """Sells at a price of your choosing, or better.

        A limit sell never accepts less than the price given. It waits in the market until someone buys at that price or higher, and it may never fill at all.

        UBI's order engine holds a `day` limit order that is not an after-market order rather than resting it at a broker, and sends it only once the other side of the book reaches the price, so an order that never fills costs no order messages. Until then `place_order` answers with an outcome of `armed` and a `parent_id` rather than an `order_id`, the order is not in `orders` but in `parents`, and it is changed with `modify_order(parent_id=...)` and cancelled with `cancel_parent`.

        Args:
            price: The float limit price in rupees.
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.
            hold: A bool that is True to let UBI's order engine hold a `day` order until the other side of the book reaches the price, and False to send it to a broker at once. An after-market order is always sent at once, whatever this says. Pass False for an instrument with no live quote, whose order the engine would otherwise hold all day without sending.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        synthetic = None
        if not hold:
            synthetic = {
                "type": "simple",
            }
        return self.place_order(
            transaction_type="sell",
            order_type="limit",
            price=price,
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
            synthetic=synthetic,
        )

    def buy_at_best_bid_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Buys patiently, joining the queue at the highest price anyone is bidding.

        This is the patient side of the pair. It prices the order alongside everyone already waiting at the best price on its own side of the book, so it saves the spread but only fills when the market comes to it.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="buy",
            order_type="limit",
            price_reference={
                "kind": "bid_level",
                "level": 1,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def buy_at_best_offer_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Buys at once, by crossing the spread to the lowest price anyone is offering.

        This is the aggressive side of the pair. It prices the order where the other side of the market already is, so it fills immediately against whoever is waiting there, and it pays the spread for that certainty.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="buy",
            order_type="limit",
            price_reference={
                "kind": "offer_level",
                "level": 1,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def sell_at_best_offer_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Sells patiently, joining the queue at the lowest price anyone is offering.

        This is the patient side of the pair. It prices the order alongside everyone already waiting at the best price on its own side of the book, so it saves the spread but only fills when the market comes to it.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="sell",
            order_type="limit",
            price_reference={
                "kind": "offer_level",
                "level": 1,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def sell_at_best_bid_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Sells at once, by crossing the spread to the highest price anyone is bidding.

        This is the aggressive side of the pair. It prices the order where the other side of the market already is, so it fills immediately against whoever is waiting there, and it pays the spread for that certainty.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="sell",
            order_type="limit",
            price_reference={
                "kind": "bid_level",
                "level": 1,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def buy_at_mid_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Buys halfway between the best bid and the best offer.

        The mid price sits inside the spread, where nobody is waiting, so the order is better than joining its own side of the book and cheaper than crossing to the other. It fills only if the market moves that far. UBI works the midpoint out when it sends the order and rounds it to the tick, down for a buy and up for a sell, so the order never crosses the spread.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="buy",
            order_type="limit",
            price_reference={
                "kind": "mid",
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def sell_at_mid_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Sells halfway between the best bid and the best offer.

        The mid price sits inside the spread, where nobody is waiting, so the order is better than joining its own side of the book and cheaper than crossing to the other. It fills only if the market moves that far. UBI works the midpoint out when it sends the order and rounds it to the tick, down for a buy and up for a sell, so the order never crosses the spread.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="sell",
            order_type="limit",
            price_reference={
                "kind": "mid",
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def buy_at_volume_weighted_average_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Buys at the average price the day has traded at so far.

        The volume weighted average price is where the day's business has actually been done, which makes it a common benchmark to measure a fill against. It has no relation to where the book is now, so the order may cross the spread or sit far away from it. Not every broker reports it. UBI reads it when it sends the order and rounds it to the tick.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="buy",
            order_type="limit",
            price_reference={
                "kind": "vwap",
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def sell_at_volume_weighted_average_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Sells at the average price the day has traded at so far.

        The volume weighted average price is where the day's business has actually been done, which makes it a common benchmark to measure a fill against. It has no relation to where the book is now, so the order may cross the spread or sit far away from it. Not every broker reports it. UBI reads it when it sends the order and rounds it to the tick.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="sell",
            order_type="limit",
            price_reference={
                "kind": "vwap",
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def buy_at_marketable_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
        buffer_percent: float | None = None,
    ) -> dict:
        """Buys now with a limit order priced at the best offer, the price it takes to fill immediately.

        This is what a market order has become in India: brokers convert an API market order into a limit order with price protection, and some refuse market orders outright. A marketable limit states the cap itself, so the order fills at once up to that price and never beyond it. UBI reads the best offer when it sends the order, and `buffer_percent` moves the cap that far above it to reach deeper into the book. Pair it with `validity="ioc"` to cancel whatever cannot fill at once.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.
            buffer_percent: The float percentage to move the cap past the best offer, such as 0.5, or None for no buffer. A cap too far from the market is refused by the exchange's price protection.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        price_reference = {
            "kind": "marketable",
        }
        if buffer_percent is not None:
            price_reference["buffer_percent"] = buffer_percent
        return self.place_order(
            transaction_type="buy",
            order_type="limit",
            price_reference=price_reference,
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def sell_at_marketable_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
        buffer_percent: float | None = None,
    ) -> dict:
        """Sells now with a limit order priced at the best bid, the price it takes to fill immediately.

        This is what a market order has become in India: brokers convert an API market order into a limit order with price protection, and some refuse market orders outright. A marketable limit states the cap itself, so the order fills at once up to that price and never beyond it. UBI reads the best bid when it sends the order, and `buffer_percent` moves the cap that far below it to reach deeper into the book. Pair it with `validity="ioc"` to cancel whatever cannot fill at once.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.
            buffer_percent: The float percentage to move the cap past the best bid, such as 0.5, or None for no buffer. A cap too far from the market is refused by the exchange's price protection.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        price_reference = {
            "kind": "marketable",
        }
        if buffer_percent is not None:
            price_reference["buffer_percent"] = buffer_percent
        return self.place_order(
            transaction_type="sell",
            order_type="limit",
            price_reference=price_reference,
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def buy_at_last_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Buys with a limit order at the price the instrument last traded at.

        The last traded price is where the most recent deal was done, which may be on either side of the book by the time the order arrives, so the order may fill at once or rest. UBI reads it when it sends the order and rounds it to the tick.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="buy",
            order_type="limit",
            price_reference={
                "kind": "last",
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def sell_at_last_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Sells with a limit order at the price the instrument last traded at.

        The last traded price is where the most recent deal was done, which may be on either side of the book by the time the order arrives, so the order may fill at once or rest. UBI reads it when it sends the order and rounds it to the tick.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="sell",
            order_type="limit",
            price_reference={
                "kind": "last",
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def buy_at_second_best_bid_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Buys at the second best price on the buy side of the book.

        This is more patient than pricing at the best level, because the order waits behind everyone at the second best price on its own side. It fills less often, and at a better price when it does.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="buy",
            order_type="limit",
            price_reference={
                "kind": "bid_level",
                "level": 2,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def buy_at_third_best_bid_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Buys at the third best price on the buy side of the book.

        This is more patient than pricing at the best level, because the order waits behind everyone at the third best price on its own side. It fills less often, and at a better price when it does.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="buy",
            order_type="limit",
            price_reference={
                "kind": "bid_level",
                "level": 3,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def buy_at_fourth_best_bid_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Buys at the fourth best price on the buy side of the book.

        This is more patient than pricing at the best level, because the order waits behind everyone at the fourth best price on its own side. It fills less often, and at a better price when it does.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="buy",
            order_type="limit",
            price_reference={
                "kind": "bid_level",
                "level": 4,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def buy_at_fifth_best_bid_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Buys at the fifth best price on the buy side of the book.

        This is more patient than pricing at the best level, because the order waits behind everyone at the fifth best price on its own side. It fills less often, and at a better price when it does.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="buy",
            order_type="limit",
            price_reference={
                "kind": "bid_level",
                "level": 5,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def sell_at_second_best_bid_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Sells at the second best price on the buy side of the book.

        This is more aggressive than pricing at the best level, because the order reaches past the front of the other side and can sweep every level down to the second. Expect a larger fill at a worse average price.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="sell",
            order_type="limit",
            price_reference={
                "kind": "bid_level",
                "level": 2,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def sell_at_third_best_bid_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Sells at the third best price on the buy side of the book.

        This is more aggressive than pricing at the best level, because the order reaches past the front of the other side and can sweep every level down to the third. Expect a larger fill at a worse average price.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="sell",
            order_type="limit",
            price_reference={
                "kind": "bid_level",
                "level": 3,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def sell_at_fourth_best_bid_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Sells at the fourth best price on the buy side of the book.

        This is more aggressive than pricing at the best level, because the order reaches past the front of the other side and can sweep every level down to the fourth. Expect a larger fill at a worse average price.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="sell",
            order_type="limit",
            price_reference={
                "kind": "bid_level",
                "level": 4,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def sell_at_fifth_best_bid_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Sells at the fifth best price on the buy side of the book.

        This is more aggressive than pricing at the best level, because the order reaches past the front of the other side and can sweep every level down to the fifth. Expect a larger fill at a worse average price.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="sell",
            order_type="limit",
            price_reference={
                "kind": "bid_level",
                "level": 5,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def buy_at_second_best_offer_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Buys at the second best price on the sell side of the book.

        This is more aggressive than pricing at the best level, because the order reaches past the front of the other side and can sweep every level down to the second. Expect a larger fill at a worse average price.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="buy",
            order_type="limit",
            price_reference={
                "kind": "offer_level",
                "level": 2,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def buy_at_third_best_offer_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Buys at the third best price on the sell side of the book.

        This is more aggressive than pricing at the best level, because the order reaches past the front of the other side and can sweep every level down to the third. Expect a larger fill at a worse average price.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="buy",
            order_type="limit",
            price_reference={
                "kind": "offer_level",
                "level": 3,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def buy_at_fourth_best_offer_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Buys at the fourth best price on the sell side of the book.

        This is more aggressive than pricing at the best level, because the order reaches past the front of the other side and can sweep every level down to the fourth. Expect a larger fill at a worse average price.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="buy",
            order_type="limit",
            price_reference={
                "kind": "offer_level",
                "level": 4,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def buy_at_fifth_best_offer_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Buys at the fifth best price on the sell side of the book.

        This is more aggressive than pricing at the best level, because the order reaches past the front of the other side and can sweep every level down to the fifth. Expect a larger fill at a worse average price.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="buy",
            order_type="limit",
            price_reference={
                "kind": "offer_level",
                "level": 5,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def sell_at_second_best_offer_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Sells at the second best price on the sell side of the book.

        This is more patient than pricing at the best level, because the order waits behind everyone at the second best price on its own side. It fills less often, and at a better price when it does.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="sell",
            order_type="limit",
            price_reference={
                "kind": "offer_level",
                "level": 2,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def sell_at_third_best_offer_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Sells at the third best price on the sell side of the book.

        This is more patient than pricing at the best level, because the order waits behind everyone at the third best price on its own side. It fills less often, and at a better price when it does.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="sell",
            order_type="limit",
            price_reference={
                "kind": "offer_level",
                "level": 3,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def sell_at_fourth_best_offer_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Sells at the fourth best price on the sell side of the book.

        This is more patient than pricing at the best level, because the order waits behind everyone at the fourth best price on its own side. It fills less often, and at a better price when it does.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="sell",
            order_type="limit",
            price_reference={
                "kind": "offer_level",
                "level": 4,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def sell_at_fifth_best_offer_price(
        self,
        quantity: int,
        product: str,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Sells at the fifth best price on the sell side of the book.

        This is more patient than pricing at the best level, because the order waits behind everyone at the fifth best price on its own side. It fills less often, and at a better price when it does.

        Args:
            quantity: The int quantity in underlying units, not lots.
            product: The str product, `cnc` for delivery, `mis` for intraday or `nrml` for carry forward.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            ServiceUnavailableError: UBI could not work the price out, because there is no live quote, the order book is not that deep or no tick size is agreed, which is what the book looks like outside market hours.
            BadRequestError: A field is invalid.
            OrderRejectedError: The broker refused the order.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.place_order(
            transaction_type="sell",
            order_type="limit",
            price_reference={
                "kind": "offer_level",
                "level": 5,
            },
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    @property
    def positions_value(self) -> float | None:
        """What this instrument's open positions are worth at the moment.

        Each position is counted as its quantity times its last price, and the sign is kept, so a long position adds and a short one subtracts. A short position is an obligation to buy back, which is what the negative number says.

        UBI prices a holding for you but not a position, so this is worked out here. When any position has no last price, the whole answer is None rather than a total quietly missing one of its parts.

        Unlike the methods that change a position, this counts every position, including those held under `margin_trading`, `cover` and `bracket`, because they are real money even though UBI cannot send an order to close them.

        Returns:
            The float value in rupees of every position in this instrument added together, or None when nothing is held or any position has no last price.

        Raises:
            BrokerError: No broker's positions could be read.
            ServiceUnavailableError: UBI's positions document is missing or too old to serve.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        frame = self.net_positions
        if frame is None:
            return None
        total = 0.0
        for row in frame.to_dict("records"):
            last_price = row["last_price"]
            if last_price is None or pd.isna(last_price):
                return None
            total = total + row["quantity"] * last_price
        return round(total, 2)

    @property
    def positions_pnl(self) -> dict | None:
        """What this instrument's positions have made or lost.

        The realised part is profit already booked by closing some of a position today, and the unrealised part is what is still riding on what remains open. Both are added across every position in this instrument.

        Unlike the methods that change a position, this counts every position, including those held under `margin_trading`, `cover` and `bracket`.

        Returns:
            A dict with `realized`, `unrealized` and `total` in rupees, or None when nothing is held in this instrument.

        Raises:
            BrokerError: No broker's positions could be read.
            ServiceUnavailableError: UBI's positions document is missing or too old to serve.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        frame = self.net_positions
        if frame is None:
            return None
        realized = 0.0
        unrealized = 0.0
        for row in frame.to_dict("records"):
            realized = realized + row["pnl"]["realized"]
            unrealized = unrealized + row["pnl"]["unrealized"]
        return {
            "realized": round(realized, 2),
            "unrealized": round(unrealized, 2),
            "total": round(realized + unrealized, 2),
        }

    def add_to_position(
        self,
        quantity: int,
        product: str | None = None,
        transaction_type: str | None = None,
        price: float | None = None,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Makes an existing position bigger, or opens a new one.

        The direction follows the position you already hold: a long position is added to by buying and a short one by selling, so `transaction_type` is needed only when you hold nothing yet. Holding nothing also means there is no position to read a product from, so `product` is needed then too.

        Only positions held under `cnc`, `mis` and `nrml` are visible here. UBI also reports positions under `margin_trading`, `cover` and `bracket`, which come from order kinds it cannot send, and those are ignored as though they were not there.

        Args:
            quantity: The int quantity to add, in underlying units and always positive, whichever way the position points.
            product: The str product of the position to add to, `cnc`, `mis` or `nrml`, or None when only one position is held.
            transaction_type: The str direction to open in, `buy` or `sell`, used only when no position is held yet.
            price: The float limit price in rupees, or None to send a market order.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            PositionError: Several positions are held and none was named, or the direction given contradicts the position held, or nothing is held and no direction and product were given.
            UnifiedBrokerInterfaceError: Any failure reported by, or on the way to, UBI.
        """
        frame = self._tradeable_positions()
        if frame is None:
            return self._open_a_new_position(
                quantity=quantity,
                product=product,
                transaction_type=transaction_type,
                price=price,
                validity=validity,
                after_market=after_market,
                tag=tag,
            )
        row = self._position_row(product)
        if row["quantity"] > 0:
            wanted_direction = "buy"
        else:
            wanted_direction = "sell"
        if transaction_type is not None:
            if transaction_type.lower() != wanted_direction:
                raise exceptions.PositionError(
                    f"This is a position of {row['quantity']} under {row['product']}, so a {transaction_type.lower()} reduces it rather than adding to it; use reduce_position: {self!r}"
                )
        return self._place_to_change_position(
            transaction_type=wanted_direction,
            quantity=quantity,
            product=ORDER_PRODUCT_FOR_POSITION_PRODUCT[row["product"]],
            price=price,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def reduce_position(
        self,
        quantity: int,
        product: str | None = None,
        price: float | None = None,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Makes an existing position smaller, without turning it around.

        UBI works the direction out from the position when it sends the order: a long position is reduced by selling and a short one by buying. It also caps the order at what is held, so asking for more than the position closes the whole position and never opens a new one the other way round.

        Only positions held under `cnc`, `mis` and `nrml` are visible here, for the reason given on `add_to_position`. When no product is named, the positions are read once to find the only one held; when one is named, nothing is read here and UBI reads the positions itself.

        Args:
            quantity: The int largest quantity to close, in underlying units and always positive, whichever way the position points.
            product: The str product of the position to reduce, `cnc`, `mis` or `nrml`, or None when only one position is held.
            price: The float limit price in rupees, or None to send a market order.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            PositionError: No product was named and nothing is held, or several positions are held, or the product named is not `cnc`, `mis` or `nrml`.
            ConflictError: The product named is not held in this instrument.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self._place_to_close_position(
            kind="reduce_position",
            quantity=quantity,
            product=product,
            price=price,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def liquidate_position(
        self,
        product: str | None = None,
        price: float | None = None,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Closes one position in this instrument completely.

        UBI reads the position when it sends the order and closes the whole of it, so a long position is sold and a short one is bought back.

        Only positions held under `cnc`, `mis` and `nrml` are visible here, for the reason given on `add_to_position`. When no product is named, the positions are read once to find the only one held; when one is named, nothing is read here and UBI reads the positions itself.

        Args:
            product: The str product of the position to close, `cnc`, `mis` or `nrml`, or None when only one position is held.
            price: The float limit price in rupees, or None to send a market order.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            PositionError: No product was named and nothing is held, or several positions are held, or the product named is not `cnc`, `mis` or `nrml`.
            ConflictError: The product named is not held in this instrument.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self._place_to_close_position(
            kind="liquidate_position",
            quantity=None,
            product=product,
            price=price,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def _place_to_close_position(
        self,
        kind: str,
        quantity: int | None,
        product: str | None,
        price: float | None,
        validity: str | None,
        after_market: bool,
        tag: str | None,
    ) -> dict:
        """Sends an order that UBI sizes and directs from the position it closes.

        The side sent is only a placeholder, because UBI replaces it with the one that closes the position. The order is marked as closing a position, so it may use the part of a broker's daily order cap that UBI keeps for exits.

        Args:
            kind: The str quantity reference kind, `reduce_position` or `liquidate_position`.
            quantity: The int largest quantity to close, or None to close the whole position.
            product: The str order product of the position, `cnc`, `mis` or `nrml`, or None to use the only position held.
            price: The float limit price in rupees, or None to send a market order.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns.

        Raises:
            PositionError: No product was named and there is not exactly one position, or the product is not `cnc`, `mis` or `nrml`.
            UnifiedBrokerInterfaceError: Any failure reported by, or on the way to, UBI.
        """
        if product is None:
            row = self._position_row(None)
            product = ORDER_PRODUCT_FOR_POSITION_PRODUCT[row["product"]]
        position_product = POSITION_PRODUCT_FOR_ORDER_PRODUCT.get(product.lower())
        if position_product is None:
            raise exceptions.PositionError(
                f"Positions can be closed only under cnc, mis or nrml, not {product!r}: {self!r}"
            )
        if price is None:
            order_type = "market"
        else:
            order_type = "limit"
        return self.place_order(
            transaction_type="sell",
            order_type=order_type,
            quantity=quantity,
            product=product,
            price=price,
            validity=validity,
            after_market=after_market,
            tag=tag,
            quantity_reference={
                "kind": kind,
                "product": position_product,
            },
            synthetic={
                "type": "simple",
                "closes_position": True,
            },
        )

    def liquidate_all_positions(
        self,
        price: float | None = None,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> pd.DataFrame | None:
        """Closes every position this instrument holds, under every product.

        The positions are read once to list them, and each is then closed with its own order, which UBI sizes and directs from the position when it sends it. Every one is attempted even when an earlier one fails, so a single refusal does not leave the rest open. A position held under a product UBI cannot send an order for, which is `margin_trading`, `cover` or `bracket`, is reported as ignored rather than passed over in silence, and has to be closed at the broker directly.

        Args:
            price: The float limit price in rupees for every order, or None to send market orders.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the orders as after-market orders.
            tag: A str of up to twenty letters and digits to label the orders with, or None.

        Returns:
            A pandas.DataFrame with one row per position, holding `product`, `order_product`, `quantity`, `closed`, `order_id` and `error`, or None when this instrument holds no position at all.

        Raises:
            BrokerError: No broker's positions could be read.
            ServiceUnavailableError: UBI's positions document is missing or too old to serve.
            UnifiedBrokerInterfaceError: The positions could not be read for any other reason. A failure to close one position is reported in the frame instead.
        """
        frame = self.net_positions
        if frame is None:
            return None
        outcomes = []
        for row in frame.to_dict("records"):
            order_product = ORDER_PRODUCT_FOR_POSITION_PRODUCT.get(row["product"])
            outcome = {
                "product": row["product"],
                "order_product": order_product,
                "quantity": row["quantity"],
                "closed": False,
                "order_id": None,
                "error": None,
            }
            if order_product is None:
                outcome["error"] = (
                    f"ignored: UBI cannot send a {row['product']} order, so close this at the broker"
                )
                outcomes.append(outcome)
                continue
            try:
                answer = self.liquidate_position(
                    product=order_product,
                    price=price,
                    validity=validity,
                    after_market=after_market,
                    tag=tag,
                )
            except (
                exceptions.PositionError,
                ubi_exceptions.UnifiedBrokerInterfaceError,
            ) as error:
                outcome["error"] = f"{type(error).__name__}: {error}"
            else:
                outcome["closed"] = True
                outcome["order_id"] = answer.get("order_id")
            outcomes.append(outcome)
        return pd.DataFrame(outcomes)

    def _tradeable_positions(self) -> pd.DataFrame | None:
        """Reads this instrument's positions, keeping the ones UBI can trade.

        UBI reports a position's product as `delivery`, `intraday`, `carry`, `margin_trading`, `cover` or `bracket`, but it accepts orders only for the first three. The last three come from order kinds its place route cannot send, so they are dropped here, which is the one place that happens.

        Returns:
            A pandas.DataFrame of the positions that can be traded through UBI, or None when there are none.

        Raises:
            BrokerError: No broker's positions could be read.
            ServiceUnavailableError: UBI's positions document is missing or too old to serve.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        frame = self.net_positions
        if frame is None:
            return None
        tradeable_rows = []
        for row in frame.to_dict("records"):
            if row["product"] in ORDER_PRODUCT_FOR_POSITION_PRODUCT:
                tradeable_rows.append(row)
        if not tradeable_rows:
            return None
        return pd.DataFrame(tradeable_rows)

    def _position_row(self, product: str | None) -> dict:
        """Picks the one position to act on.

        Args:
            product: The str order product naming the position, `cnc`, `mis` or `nrml`, or None to use the only position held.

        Returns:
            The dict row of the position, with UBI's own `product` spelling in it.

        Raises:
            PositionError: Nothing tradeable is held, or the named product is not held, or several are held and none was named.
        """
        frame = self._tradeable_positions()
        if frame is None:
            raise exceptions.PositionError(
                f"No position is held in this instrument that UBI can send an order for: {self!r}"
            )
        rows = frame.to_dict("records")
        if product is None:
            if len(rows) == 1:
                return rows[0]
            held_products = []
            for row in rows:
                held_products.append(row["product"])
            raise exceptions.PositionError(
                f"Positions are held under {', '.join(sorted(held_products))}, so name the product to act on: {self!r}"
            )
        wanted_product = POSITION_PRODUCT_FOR_ORDER_PRODUCT.get(product.lower())
        for row in rows:
            if row["product"] == wanted_product:
                return row
        held_products = []
        for row in rows:
            held_products.append(row["product"])
        raise exceptions.PositionError(
            f"No {product} position is held in this instrument, which holds {', '.join(sorted(held_products))}: {self!r}"
        )

    def _place_to_change_position(
        self,
        transaction_type: str,
        quantity: int,
        product: str,
        price: float | None,
        validity: str | None,
        after_market: bool,
        tag: str | None,
    ) -> dict:
        """Sends the order that changes a position, as a market or a limit order.

        Args:
            transaction_type: The str direction to trade in, `buy` or `sell`.
            quantity: The int quantity in underlying units.
            product: The str order product, `cnc`, `mis` or `nrml`.
            price: The float limit price in rupees, or None to send a market order.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns.

        Raises:
            UnifiedBrokerInterfaceError: Any failure reported by, or on the way to, UBI.
        """
        if transaction_type == "buy":
            if price is None:
                return self.buy_at_market_price(
                    quantity=quantity,
                    product=product,
                    validity=validity,
                    after_market=after_market,
                    tag=tag,
                )
            return self.buy_at_limit_price(
                price=price,
                quantity=quantity,
                product=product,
                validity=validity,
                after_market=after_market,
                tag=tag,
            )
        if price is None:
            return self.sell_at_market_price(
                quantity=quantity,
                product=product,
                validity=validity,
                after_market=after_market,
                tag=tag,
            )
        return self.sell_at_limit_price(
            price=price,
            quantity=quantity,
            product=product,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def _open_a_new_position(
        self,
        quantity: int,
        product: str | None,
        transaction_type: str | None,
        price: float | None,
        validity: str | None,
        after_market: bool,
        tag: str | None,
    ) -> dict:
        """Opens a position in an instrument that holds none.

        Args:
            quantity: The int quantity in underlying units.
            product: The str order product to open under, `cnc`, `mis` or `nrml`, or None.
            transaction_type: The str direction to open in, `buy` or `sell`, or None.
            price: The float limit price in rupees, or None to send a market order.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns.

        Raises:
            PositionError: No direction or no product was given, and neither can be read from a position that does not exist.
            UnifiedBrokerInterfaceError: Any failure reported by, or on the way to, UBI.
        """
        if transaction_type is None or product is None:
            raise exceptions.PositionError(
                f"No position is held in this instrument, so opening one needs both transaction_type and product: {self!r}"
            )
        return self._place_to_change_position(
            transaction_type=transaction_type.lower(),
            quantity=quantity,
            product=product,
            price=price,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

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
        details: dict | None = None,
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
            details: The dict UBI returned for this instrument from `/api/instruments/details`, such as one entry of a list request, which is used instead of looking the instrument up again, or None to look it up from the other arguments.

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
            details=details,
        )
        if not self.segment.endswith(INDEX_SEGMENT_SUFFIX):
            raise exceptions.NonTradeableInstrumentError(
                f"Only an index is a NonTradeableInstrument, and this can be traded: {self!r}"
            )

    @property
    def constituents(self) -> "asset_basket.AssetBasket | None":
        """The stored basket of the index's members, usually a tradingmachine.asset_baskets.index.Index, or None when none is stored for today, read from MongoDB and UBI on every access.

        The index's own price stays on this object; the basket describes what the index holds, and every analysis and performance method works on it too. UBI stores no constituents, so a basket exists only when one was saved with this index as its linked instrument, for instance by tradingmachine.asset_baskets.basket_csv_importer.BasketCsvImporter.

        Raises:
            BasketMemberError: UBI could not find one or more of the stored members.
            pymongo.errors.PyMongoError: MongoDB could not be reached.
        """
        from tradingmachine.asset_baskets import basket_store

        store = basket_store.BasketStore(
            unified_broker_interface=self._unified_broker_interface,
        )
        return store.load_for_instrument(self)


class Derivative(TradeableInstrument):
    """A futures or option contract, which expires on a set day and is written on an underlying instrument.

    This is the shared base of `Futures` and `Option`, and it holds what is true of every contract: when it expires, what it is written on, how much of it is open, and what one lot of it is worth. It is rarely built directly; the family classes such as `tradingmachine.assets.equities.EquityFutures` inherit it.

    The underlying is found in this order, and the first that applies wins. An underlying given as an object when the contract is built is kept and used as it is. Otherwise UBI's `underlying_instrument_id`, resolved from the brokers' own records, is used when UBI supplies one. Otherwise the family's default applies, from `UNDERLYING_SEGMENT_FOR_DERIVATIVE_SEGMENT`: an equity contract's share or index found by its symbol, the nearest future for an option on a commodity, a currency pair or a bond, and nothing for a future outside equities, whose cash underlying has no price in UBI. Nothing but the given object is stored, so the other ways look the underlying up again on every read, and `UnderlyingError` says when none of them finds one.

    Attributes:
        SEGMENT: The str bare UBI segment a family class supplies, such as `equity_futures`, which the discovery class methods read; None on the base classes.
        underlying_segment: The str exchange-prefixed segment of the underlying, such as `nse_equities`, `nse_equity_indices` or `mcx_commodity_futures`: the given underlying's own segment, or else the one the family's default searches, or None when the family has no default.
    """

    SEGMENT = None

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
        underlying: Instrument | None = None,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the contract up in UBI and checks that it is a future or an option.

        Args:
            instrument_id: The str UUID of the contract, or None to look it up by exchange, segment and identity fields.
            exchange: The str exchange, such as `nse`, or None when instrument_id is given.
            segment: The str segment, bare such as `equity_futures` or prefixed such as `nse_equity_futures`, or None when instrument_id is given.
            symbol: The str symbol of a security, or None, since a contract has none.
            underlying_symbol: The str symbol of the contract's underlying, such as `RELIANCE`, or None when instrument_id is given.
            expiry_date: The expiry of the contract as a datetime.date or a `YYYY-MM-DD` str, or None when instrument_id is given.
            strike_price: The float strike price of an option, or None for a future.
            option_type: The str option type of an option, `CE` or `PE`, or None for a future.
            underlying: The Instrument the contract is written on, such as an Equity, an EquityIndex or a future, which the contract keeps and uses for `underlying` and `underlying_price`, or None to use UBI's link to the underlying or else the family's default, looked up on every read.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            TypeError: underlying is given and is not an Instrument.
            DerivativeError: The instrument is neither a future nor an option, has no expiry date, or is in a segment with no known underlying segment and no underlying was given.
            TradeableInstrumentError: The instrument is an index.
            InstrumentError: UBI has no instrument matching the lookup.
            BadRequestError: The lookup is incomplete or malformed.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        if underlying is not None and not isinstance(underlying, Instrument):
            raise TypeError(
                f"The underlying must be an Instrument, not a {type(underlying).__name__}: {underlying!r}"
            )
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
        if self.shape not in DERIVATIVE_SHAPES:
            raise exceptions.DerivativeError(
                f"Only a future or an option is a {type(self).__name__}, and this is a {self.shape}: {self!r}"
            )
        if self.expiry_date is None:
            raise exceptions.DerivativeError(
                f"A contract needs an expiry date, and UBI gave none: {self!r}"
            )
        self._given_underlying = underlying
        if underlying is not None:
            self.underlying_segment = underlying.segment
        else:
            self.underlying_segment = self._underlying_segment_from_table()

    def _underlying_segment_from_table(self) -> str | None:
        """Works out where the family's default underlying is found, from the contract's own segment.

        Returns:
            The str exchange-prefixed segment, such as `nse_equity_indices` for an index option on the nse or `mcx_commodity_futures` for an option on a commodity, or None when the family has no default underlying for this kind of contract.

        Raises:
            DerivativeError: The contract's segment is not one of the sixteen derivative segments in `UNDERLYING_SEGMENT_FOR_DERIVATIVE_SEGMENT`.
        """
        bare_segment = self.segment.removeprefix(f"{self.exchange}_")
        if bare_segment not in UNDERLYING_SEGMENT_FOR_DERIVATIVE_SEGMENT:
            raise exceptions.DerivativeError(
                f"The {self.segment} segment has no known underlying segment, so give the underlying when building the contract: {self!r}"
            )
        underlying_bare_segment = UNDERLYING_SEGMENT_FOR_DERIVATIVE_SEGMENT[
            bare_segment
        ]
        if underlying_bare_segment is None:
            return None
        return f"{self.exchange}_{underlying_bare_segment}"

    def _look_up_underlying(self) -> Instrument:
        """Finds the underlying when none was given, trying UBI's link first and then the family's default.

        Returns:
            The underlying as an Instrument: a TradeableInstrument or NonTradeableInstrument for UBI's link or an equity's share or index, or a Futures for an option priced off a future.

        Raises:
            UnderlyingError: UBI gives no link, and the family has no default for this contract, or the default finds nothing.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        if self.underlying_instrument_id is not None:
            try:
                return TradeableInstrument(
                    instrument_id=self.underlying_instrument_id,
                    unified_broker_interface=self._unified_broker_interface,
                )
            except exceptions.TradeableInstrumentError:
                return NonTradeableInstrument(
                    instrument_id=self.underlying_instrument_id,
                    unified_broker_interface=self._unified_broker_interface,
                )
        if self.underlying_segment is None:
            raise exceptions.UnderlyingError(
                f"UBI links {self!r} to no underlying, and a {self.segment} contract has no default one, because its cash underlying has no price in UBI; give the underlying when building it"
            )
        if self.underlying_segment.endswith(FUTURES_SEGMENT_SUFFIX):
            return self._nearest_future()
        try:
            if self.underlying_segment.endswith(INDEX_SEGMENT_SUFFIX):
                return NonTradeableInstrument(
                    exchange=self.exchange,
                    segment=self.underlying_segment,
                    symbol=self.underlying_symbol,
                    unified_broker_interface=self._unified_broker_interface,
                )
            return TradeableInstrument(
                exchange=self.exchange,
                segment=self.underlying_segment,
                symbol=self.underlying_symbol,
                unified_broker_interface=self._unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.UnderlyingError(
                f"UBI has no {self.underlying_segment} instrument with the symbol {self.underlying_symbol}, so {self!r} has no underlying; give it when building the contract"
            ) from error

    def _nearest_future(self) -> "Futures":
        """Finds the future the contract is priced off: the same underlying's future that expires first on or after the contract does.

        On or after, rather than in the same month, because an option can settle into a later future: an MCX GOLD option expiring at the end of October settles into the December future, since the October one has already expired.

        Returns:
            The future as a Futures.

        Raises:
            UnderlyingError: No live future on the same underlying expires on or after the contract.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        frame = self._contracts_for(
            self.exchange,
            self.underlying_segment,
            self.underlying_symbol,
            None,
            False,
            self._unified_broker_interface,
        )
        chosen_instrument_id = None
        chosen_expiry = None
        if frame is not None:
            for row in frame.to_dict("records"):
                if row["expiry_date"] < self.expiry_date:
                    continue
                if chosen_expiry is None or row["expiry_date"] < chosen_expiry:
                    chosen_instrument_id = row["instrument_id"]
                    chosen_expiry = row["expiry_date"]
        if chosen_instrument_id is None:
            raise exceptions.UnderlyingError(
                f"No live {self.underlying_segment} contract on {self.underlying_symbol} expires on or after {self.expiry_date.isoformat()}, so {self!r} has no underlying; give it when building the contract"
            )
        return Futures(
            instrument_id=chosen_instrument_id,
            unified_broker_interface=self._unified_broker_interface,
        )

    def _underlying_is_future(self) -> bool:
        """Says whether the contract is priced off a future, which decides between the Black-76 and Black-Scholes models.

        Returns:
            A bool that is True when the given underlying is a future, or, with none given, when the family's default is a future.

        Raises:
            Nothing.
        """
        if self._given_underlying is not None:
            return self._given_underlying.shape == FUTURE_SHAPE
        if self.underlying_segment is None:
            return False
        return self.underlying_segment.endswith(FUTURES_SEGMENT_SUFFIX)

    @property
    def days_to_expiry(self) -> int:
        """The number of calendar days from today until the contract expires, counted in India time.

        Returns:
            The int number of days, which is 0 on the day of expiry and negative once the contract has expired.

        Raises:
            Nothing.
        """
        today = datetime.datetime.now(INDIA_TIME_ZONE).date()
        return (self.expiry_date - today).days

    @property
    def expired(self) -> bool:
        """Whether the contract's expiry date has passed, counted in India time.

        A contract expiring today is not expired, because it can still be traded until the market closes. This matches the rule the discovery class methods use.

        Returns:
            A bool that is True once the expiry date is in the past.

        Raises:
            Nothing.
        """
        return self.days_to_expiry < 0

    @property
    def expiry_kind(self) -> str:
        """Whether the contract is the month's last expiry for its underlying or one of the weekly expiries before it.

        A contract is monthly when no later contract on the same underlying in the same segment expires in the same calendar month, and weekly otherwise. Quarterly and half-yearly contracts count as monthly, because each is the last of its month. Each read downloads the segment's whole instrument list from UBI, which takes about two seconds for single-stock options.

        Returns:
            The str `monthly` or `weekly`.

        Raises:
            BadRequestError: The exchange or segment is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        expiry_dates = self._expiry_dates(
            self.exchange,
            self.segment,
            self.underlying_symbol,
            True,
            self._unified_broker_interface,
        )
        for expiry_date in expiry_dates:
            if expiry_date <= self.expiry_date:
                continue
            same_year = expiry_date.year == self.expiry_date.year
            same_month = expiry_date.month == self.expiry_date.month
            if same_year and same_month:
                return WEEKLY_EXPIRY_KIND
        return MONTHLY_EXPIRY_KIND

    @property
    def next_expiry(self) -> datetime.date | None:
        """The first live expiry after this contract's on the same underlying in the same segment, which is where a position rolls to.

        Each read downloads the segment's whole instrument list from UBI, which takes about two seconds for single-stock options.

        Returns:
            The datetime.date of the next expiry, or None when this is the last one listed.

        Raises:
            BadRequestError: The exchange or segment is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        expiry_dates = self._expiry_dates(
            self.exchange,
            self.segment,
            self.underlying_symbol,
            False,
            self._unified_broker_interface,
        )
        for expiry_date in expiry_dates:
            if expiry_date > self.expiry_date:
                return expiry_date
        return None

    @property
    def underlying(self) -> Instrument:
        """The instrument the contract is written on, found in the order the class docstring gives.

        A given underlying is returned as it is, with no request, whatever its class. Any other is looked up again on every read, so bind it to a local variable to use it more than once: UBI's link or an equity's share or index comes back as a `TradeableInstrument` or `NonTradeableInstrument`, never a family class such as `Equity`, because this module cannot import the family modules, and an option's default future comes back as a `Futures`.

        Returns:
            The underlying as an Instrument.

        Raises:
            UnderlyingError: No underlying was given, UBI gives no link, and the family's default finds none.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        if self._given_underlying is not None:
            return self._given_underlying
        return self._look_up_underlying()

    @property
    def underlying_price(self) -> float | None:
        """The underlying's last traded price, read from UBI on every access.

        It is the last price of the instrument `underlying` finds, read as cheaply as that way allows: a given underlying's own `last_price`, one request by instrument id for UBI's link, one request by exchange, segment and symbol for an equity's share or index, and the future's lookup and last price for an option priced off a future.

        Returns:
            The float last price of the underlying, or None when UBI has none.

        Raises:
            UnderlyingError: No underlying was given, UBI gives no link, and the family's default finds none, which is the case for every future outside equities.
            ServiceUnavailableError: UBI has no recent quote for the underlying and no broker could supply one.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        if self._given_underlying is not None:
            return self._given_underlying.last_price
        if self.underlying_instrument_id is not None:
            response = self._unified_broker_interface.get(
                LAST_PRICE_PATH,
                params={
                    "instrument_id": self.underlying_instrument_id,
                },
            )
            return response["last_price"]
        if self.underlying_segment is None:
            return self._look_up_underlying().last_price
        if self.underlying_segment.endswith(FUTURES_SEGMENT_SUFFIX):
            return self._nearest_future().last_price
        try:
            response = self._unified_broker_interface.get(
                LAST_PRICE_PATH,
                params={
                    "exchange": self.exchange,
                    "segment": self.underlying_segment,
                    "symbol": self.underlying_symbol,
                },
            )
        except ubi_exceptions.NotFoundError as error:
            raise exceptions.UnderlyingError(
                f"UBI has no {self.underlying_segment} instrument with the symbol {self.underlying_symbol}, so {self!r} has no underlying; give it when building the contract: {error.message}"
            ) from error
        return response["last_price"]

    @property
    def open_interest_day_high(self) -> int | None:
        """The highest open interest reached today.

        Returns:
            The int open interest in underlying units, or None when the broker serving the quote does not report it.

        Raises:
            ServiceUnavailableError: UBI has no recent quote and no broker could supply one.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.quote["oi_day_high"]

    @property
    def open_interest_day_low(self) -> int | None:
        """The lowest open interest reached today.

        Returns:
            The int open interest in underlying units, or None when the broker serving the quote does not report it.

        Raises:
            ServiceUnavailableError: UBI has no recent quote and no broker could supply one.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.quote["oi_day_low"]

    @property
    def contract_value(self) -> float | None:
        """What one lot of the contract is worth at its last price, which is the last price times the lot size.

        For a future this is the exposure one lot carries, and for an option it is the premium one lot costs. The lot size is the one UBI reports for the instrument, which for currency contracts is the plurality of the brokers' figures rather than the lot an order is measured against, so there it is approximate.

        Returns:
            The float value in rupees, or None when the last price or the lot size is unknown.

        Raises:
            ServiceUnavailableError: UBI has no recent quote and no broker could supply one.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        last_price = self.last_price
        if last_price is None or self.lot_size is None:
            return None
        return last_price * self.lot_size


class Futures(Derivative):
    """A futures contract, an agreement to buy or sell the underlying at a set price on the expiry date.

    It holds the members every futures contract shares, such as its basis over the underlying, and the discovery class methods `expiries` and `contracts`, which read the segment a family class names in `SEGMENT`. The family classes such as `tradingmachine.assets.equities.EquityFutures` inherit it; built directly, it accepts any futures contract, including one on an index.
    """

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
        underlying: Instrument | None = None,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the contract up in UBI and checks that it is a futures contract.

        Args:
            instrument_id: The str UUID of the contract, or None to look it up by exchange, segment and identity fields.
            exchange: The str exchange, such as `nse`, or None when instrument_id is given.
            segment: The str segment, bare such as `equity_futures` or prefixed such as `nse_equity_futures`, or None when instrument_id is given.
            symbol: The str symbol of a security, or None, since a contract has none.
            underlying_symbol: The str symbol of the contract's underlying, such as `RELIANCE`, or None when instrument_id is given.
            expiry_date: The expiry of the contract as a datetime.date or a `YYYY-MM-DD` str, or None when instrument_id is given.
            strike_price: A float strike price, or None, since a future has none.
            option_type: A str option type, or None, since a future has none.
            underlying: The Instrument the contract is written on, such as an Equity, an EquityIndex or a future, which the contract keeps and uses for `underlying` and `underlying_price`, or None to use UBI's link to the underlying or else the family's default, looked up on every read.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            TypeError: underlying is given and is not an Instrument.
            FuturesError: The instrument is an option rather than a future.
            DerivativeError: The instrument is not a contract at all, or has no expiry date.
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
            underlying=underlying,
            unified_broker_interface=unified_broker_interface,
        )
        if self.shape != FUTURE_SHAPE:
            raise exceptions.FuturesError(
                f"Only a futures contract is a {type(self).__name__}, and this is an {self.shape}: {self!r}"
            )

    @classmethod
    def expiries(
        cls,
        exchange: str,
        underlying_symbol: str,
        include_expired: bool = False,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> list[datetime.date]:
        """Lists the expiries an underlying's futures contracts are listed for in the class's segment.

        A contract expiring today counts as live, because it can still be traded until the market closes. Call it on a family class such as `EquityFutures`, which names its segment.

        Args:
            exchange: The str exchange, such as `nse` or `mcx`.
            underlying_symbol: The str symbol of the underlying, such as `RELIANCE`, `NIFTY` or `GOLD`.
            include_expired: A bool that is True to include expiries that have already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of datetime.date, soonest first, which is empty when nothing is listed on this underlying.

        Raises:
            FuturesError: The class names no segment, which is true of `Futures` and `IndexFutures` themselves.
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        if cls.SEGMENT is None:
            raise exceptions.FuturesError(
                f"{cls.__name__} names no segment, so call expiries on a family class such as EquityFutures"
            )
        return cls._expiry_dates(
            exchange,
            cls.SEGMENT,
            underlying_symbol,
            include_expired,
            unified_broker_interface,
        )

    @classmethod
    def contracts(
        cls,
        exchange: str,
        underlying_symbol: str | None = None,
        include_expired: bool = False,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> pd.DataFrame | None:
        """Lists the futures contracts listed in the class's segment.

        The rows are identities rather than objects, because building an object looks each contract up in UBI and a long list would mean a request for every row. Build the ones you want from the rows. Call it on a family class such as `EquityFutures`, which names its segment.

        Args:
            exchange: The str exchange, such as `nse` or `mcx`.
            underlying_symbol: The str symbol of the underlying to keep, such as `RELIANCE`, or None to list every underlying.
            include_expired: A bool that is True to include contracts whose expiry has already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame with `instrument_id`, `exchange`, `segment`, `shape`, `underlying_symbol` and `expiry_date`, sorted by expiry, or None when nothing matches.

        Raises:
            FuturesError: The class names no segment, which is true of `Futures` and `IndexFutures` themselves.
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        if cls.SEGMENT is None:
            raise exceptions.FuturesError(
                f"{cls.__name__} names no segment, so call contracts on a family class such as EquityFutures"
            )
        return cls._contracts_for(
            exchange,
            cls.SEGMENT,
            underlying_symbol,
            None,
            include_expired,
            unified_broker_interface,
        )

    @property
    def basis(self) -> float | None:
        """How far the future's last price is above the underlying's, read from two quotes.

        A positive basis, or premium, is usual, because holding the future instead of the underlying saves the cost of financing it until expiry. The two prices come from two requests and may be a moment apart.

        Returns:
            The float basis in the underlying's price units, or None when either last price is unknown.

        Raises:
            UnderlyingError: The future's underlying cannot be found, which is the case for every future outside equities unless one is given.
            ServiceUnavailableError: UBI has no recent quote for the future or its underlying.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        last_price = self.last_price
        underlying_price = self.underlying_price
        if last_price is None or underlying_price is None:
            return None
        return last_price - underlying_price

    @property
    def basis_percent(self) -> float | None:
        """The basis as a percentage of the underlying's last price, read from two quotes.

        Returns:
            The float percentage, such as 0.4 for a future 0.4 per cent above its underlying, or None when either last price is unknown or the underlying's is zero.

        Raises:
            UnderlyingError: The future's underlying cannot be found, which is the case for every future outside equities unless one is given.
            ServiceUnavailableError: UBI has no recent quote for the future or its underlying.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        last_price = self.last_price
        underlying_price = self.underlying_price
        if last_price is None or underlying_price is None:
            return None
        if underlying_price == 0:
            return None
        return (last_price - underlying_price) / underlying_price * PERCENT

    @property
    def cost_of_carry(self) -> float | None:
        """The basis annualised, which is the yearly rate of return the future's premium implies, read from two quotes.

        It is the basis percentage scaled by the calendar days left, so a future 0.5 per cent above its underlying with 30 days to go carries about 6.1 per cent a year. It is compared with the risk-free rate to judge whether the future is dear or cheap. In the last few days before expiry the scaling magnifies small differences, so a basis of 0.15 per cent with one day left reads as 55 per cent a year and says little.

        Returns:
            The float annual percentage, or None when the contract expires today or has expired, or when either last price is unknown.

        Raises:
            UnderlyingError: The future's underlying cannot be found, which is the case for every future outside equities unless one is given.
            ServiceUnavailableError: UBI has no recent quote for the future or its underlying.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        days_to_expiry = self.days_to_expiry
        if days_to_expiry <= 0:
            return None
        basis_percent = self.basis_percent
        if basis_percent is None:
            return None
        return basis_percent * DAYS_PER_YEAR / days_to_expiry


class Option(Derivative):
    """An option contract, the right but not the obligation to buy the underlying at the strike price, for a call, or to sell it, for a put.

    It holds the members every option shares: its moneyness against the underlying, its premium split into intrinsic and time value, and its implied volatility and greeks from `tradingmachine.assets.option_pricing.BlackScholes`. It also holds the discovery class methods `expiries`, `strikes` and `chain`, which read the segment a family class names in `SEGMENT`. The family classes such as `tradingmachine.assets.equities.EquityOption` inherit it; built directly, it accepts any option, including one on an index.

    The pricing methods treat the option as European and without dividends, and take it to expire at 15:30 India time on its expiry date, which is what UBI's own order engine assumes. MCX commodity options trade until later in the evening, so for them 15:30 is an approximation.
    """

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
        underlying: Instrument | None = None,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the option up in UBI and checks that it is an option with a strike price and an option type.

        Args:
            instrument_id: The str UUID of the option, or None to look it up by exchange, segment and identity fields.
            exchange: The str exchange, such as `nse`, or None when instrument_id is given.
            segment: The str segment, bare such as `equity_options` or prefixed such as `nse_equity_options`, or None when instrument_id is given.
            symbol: The str symbol of a security, or None, since an option has none.
            underlying_symbol: The str symbol of the option's underlying, such as `RELIANCE`, or None when instrument_id is given.
            expiry_date: The expiry of the option as a datetime.date or a `YYYY-MM-DD` str, or None when instrument_id is given.
            strike_price: The float strike price of the option, or None when instrument_id is given.
            option_type: The str option type, `CE` for a call or `PE` for a put, or None when instrument_id is given.
            underlying: The Instrument the contract is written on, such as an Equity, an EquityIndex or a future, which the contract keeps and uses for `underlying` and `underlying_price`, or None to use UBI's link to the underlying or else the family's default, looked up on every read.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            TypeError: underlying is given and is not an Instrument.
            OptionError: The instrument is a future rather than an option, or UBI gave it no strike price or option type.
            DerivativeError: The instrument is not a contract at all, or has no expiry date.
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
            underlying=underlying,
            unified_broker_interface=unified_broker_interface,
        )
        if self.shape != OPTION_SHAPE:
            raise exceptions.OptionError(
                f"Only an option is an {type(self).__name__}, and this is a {self.shape}: {self!r}"
            )
        if self.strike_price is None or self.option_type is None:
            raise exceptions.OptionError(
                f"An option needs a strike price and an option type, and UBI did not give both: {self!r}"
            )

    @classmethod
    def expiries(
        cls,
        exchange: str,
        underlying_symbol: str,
        include_expired: bool = False,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> list[datetime.date]:
        """Lists the expiries an underlying's options are listed for in the class's segment.

        A contract expiring today counts as live, because it can still be traded until the market closes. Call it on a family class such as `EquityOption`, which names its segment.

        Args:
            exchange: The str exchange, such as `nse` or `mcx`.
            underlying_symbol: The str symbol of the underlying, such as `RELIANCE`, `NIFTY` or `GOLD`.
            include_expired: A bool that is True to include expiries that have already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of datetime.date, soonest first, which is empty when nothing is listed on this underlying.

        Raises:
            OptionError: The class names no segment, which is true of `Option` and `IndexOption` themselves.
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        if cls.SEGMENT is None:
            raise exceptions.OptionError(
                f"{cls.__name__} names no segment, so call expiries on a family class such as EquityOption"
            )
        return cls._expiry_dates(
            exchange,
            cls.SEGMENT,
            underlying_symbol,
            include_expired,
            unified_broker_interface,
        )

    @classmethod
    def strikes(
        cls,
        exchange: str,
        underlying_symbol: str,
        expiry_date: datetime.date | str,
        include_expired: bool = False,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> list[float]:
        """Lists the strike prices listed on one underlying for one expiry in the class's segment.

        It builds the chain and takes its distinct strikes, so it costs the same as `chain`. Call it on a family class such as `EquityOption`, which names its segment.

        Args:
            exchange: The str exchange, such as `nse` or `mcx`.
            underlying_symbol: The str symbol of the underlying, such as `RELIANCE` or `NIFTY`.
            expiry_date: The expiry to list, as a datetime.date or a `YYYY-MM-DD` str.
            include_expired: A bool that is True to allow an expiry that has already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of float strike prices in the underlying's price units, lowest first, which is empty when nothing is listed for that expiry.

        Raises:
            OptionError: The class names no segment, which is true of `Option` and `IndexOption` themselves.
            BadRequestError: The exchange is not one UBI knows.
            ValueError: expiry_date is a str that is not a valid ISO date.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        frame = cls.chain(
            exchange,
            underlying_symbol,
            expiry_date,
            include_expired,
            unified_broker_interface,
        )
        if frame is None:
            return []
        return sorted(set(frame["strike_price"]))

    @classmethod
    def chain(
        cls,
        exchange: str,
        underlying_symbol: str,
        expiry_date: datetime.date | str,
        include_expired: bool = False,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> pd.DataFrame | None:
        """Lists every option listed on one underlying for one expiry in the class's segment.

        The rows are identities rather than objects, because building an object looks each contract up in UBI and a chain of hundreds of contracts would mean hundreds of requests. Build the few you want from the rows. Call it on a family class such as `EquityOption`, which names its segment.

        Args:
            exchange: The str exchange, such as `nse` or `mcx`.
            underlying_symbol: The str symbol of the underlying, such as `RELIANCE` or `NIFTY`.
            expiry_date: The expiry to list, as a datetime.date or a `YYYY-MM-DD` str.
            include_expired: A bool that is True to allow an expiry that has already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame with `instrument_id`, `exchange`, `segment`, `shape`, `underlying_symbol`, `expiry_date`, `strike_price` and `option_type`, sorted by strike price and then option type, or None when nothing matches.

        Raises:
            OptionError: The class names no segment, which is true of `Option` and `IndexOption` themselves.
            BadRequestError: The exchange is not one UBI knows.
            ValueError: expiry_date is a str that is not a valid ISO date.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        if cls.SEGMENT is None:
            raise exceptions.OptionError(
                f"{cls.__name__} names no segment, so call chain on a family class such as EquityOption"
            )
        return cls._contracts_for(
            exchange,
            cls.SEGMENT,
            underlying_symbol,
            expiry_date,
            include_expired,
            unified_broker_interface,
        )

    @property
    def is_call(self) -> bool:
        """Whether the option is a call, the right to buy the underlying.

        Returns:
            A bool that is True when the option type is `CE`.

        Raises:
            Nothing.
        """
        return self.option_type == CALL_OPTION_TYPE

    @property
    def is_put(self) -> bool:
        """Whether the option is a put, the right to sell the underlying.

        Returns:
            A bool that is True when the option type is `PE`.

        Raises:
            Nothing.
        """
        return self.option_type == PUT_OPTION_TYPE

    @property
    def intrinsic_value(self) -> float | None:
        """What the option would be worth if exercised now, read from the underlying's last price.

        For a call it is how far the underlying is above the strike, and for a put how far it is below, and it is never less than zero.

        Returns:
            The float intrinsic value per unit of the underlying, or None when the underlying's last price is unknown.

        Raises:
            UnderlyingError: The option's underlying cannot be found.
            ServiceUnavailableError: UBI has no recent quote for the underlying.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        underlying_price = self.underlying_price
        if underlying_price is None:
            return None
        return self._intrinsic_value_at(underlying_price)

    @property
    def time_value(self) -> float | None:
        """The part of the premium above the intrinsic value, which is what the time left until expiry is worth, read from two quotes.

        Returns:
            The float time value per unit of the underlying, or None when either last price is unknown.

        Raises:
            UnderlyingError: The option's underlying cannot be found.
            ServiceUnavailableError: UBI has no recent quote for the option or its underlying.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        last_price = self.last_price
        intrinsic_value = self.intrinsic_value
        if last_price is None or intrinsic_value is None:
            return None
        return last_price - intrinsic_value

    @property
    def in_the_money(self) -> bool | None:
        """Whether the option has intrinsic value, read from the underlying's last price.

        Returns:
            A bool that is True when a call's strike is below the underlying or a put's is above it, or None when the underlying's last price is unknown.

        Raises:
            UnderlyingError: The option's underlying cannot be found.
            ServiceUnavailableError: UBI has no recent quote for the underlying.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        intrinsic_value = self.intrinsic_value
        if intrinsic_value is None:
            return None
        return intrinsic_value > 0

    @property
    def moneyness_percent(self) -> float | None:
        """How far the option is in or out of the money, as a percentage of the underlying's last price.

        The sign says which: positive means in the money and negative means out of it, for a call and a put alike, so a call struck 2 per cent above the underlying reads about -2.

        Returns:
            The float signed percentage, or None when the underlying's last price is unknown or zero.

        Raises:
            UnderlyingError: The option's underlying cannot be found.
            ServiceUnavailableError: UBI has no recent quote for the underlying.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        underlying_price = self.underlying_price
        if underlying_price is None or underlying_price == 0:
            return None
        distance = (underlying_price - self.strike_price) / underlying_price * PERCENT
        if self.is_call:
            return distance
        return -distance

    @property
    def breakeven_price(self) -> float | None:
        """The underlying price at expiry at which a buyer of the option at its last price neither gains nor loses.

        Returns:
            The float price, which is the strike plus the premium for a call and the strike less the premium for a put, or None when the option's last price is unknown.

        Raises:
            ServiceUnavailableError: UBI has no recent quote and no broker could supply one.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        last_price = self.last_price
        if last_price is None:
            return None
        if self.is_call:
            return self.strike_price + last_price
        return self.strike_price - last_price

    @property
    def premium_per_lot(self) -> float | None:
        """What buying one lot of the option costs at its last price, which is the last price times the lot size.

        Returns:
            The float premium in rupees, or None when the last price or the lot size is unknown.

        Raises:
            ServiceUnavailableError: UBI has no recent quote and no broker could supply one.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.contract_value

    @property
    def notional_value(self) -> float | None:
        """The value of the underlying one lot controls at the strike price, which is the strike times the lot size.

        Returns:
            The float value in rupees, or None when the lot size is unknown.

        Raises:
            Nothing.
        """
        if self.lot_size is None:
            return None
        return self.strike_price * self.lot_size

    def implied_volatility(
        self,
        risk_free_rate: float = option_pricing.DEFAULT_RISK_FREE_RATE,
        underlying_price: float | None = None,
    ) -> float | None:
        """Finds the volatility at which the pricing model reproduces the option's last price.

        The model is Black-76 when the option is priced off a future, which is the default for an option on a commodity, a currency pair or a bond and the case whenever the given underlying is a future, and Black-Scholes otherwise. The underlying's price is read from UBI unless one is given, and a figure given is taken as the same kind of price, spot or forward, as the underlying it stands in for; giving one asks what the volatility would be at another underlying price. The option still needs a last price of its own, which some contracts lack, such as the MCX GOLD options checked on 2026-09-28.

        Args:
            risk_free_rate: The float annual risk-free interest rate, continuously compounded, such as 0.065 for 6.5 per cent.
            underlying_price: The float price of the underlying to use, or None to read the underlying's last price from UBI.

        Returns:
            The float annual volatility, such as 0.12 for 12 per cent, or None when either price is unknown, when the option is at or past 15:30 India time on its expiry date, or when the premium is below the option's discounted intrinsic value.

        Raises:
            ValueError: underlying_price is given and is not above zero.
            UnderlyingError: No underlying price is given and the option's underlying cannot be found.
            ServiceUnavailableError: UBI has no recent quote for the option, or for the underlying when no price is given.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        years_to_expiry = self._years_to_expiry()
        if years_to_expiry <= 0:
            return None
        if underlying_price is None:
            underlying_price = self.underlying_price
        premium = self.last_price
        if underlying_price is None or premium is None:
            return None
        return self._pricing_model().implied_volatility(
            premium,
            underlying_price,
            self.strike_price,
            years_to_expiry,
            risk_free_rate,
            self.is_call,
        )

    def greeks(
        self,
        risk_free_rate: float = option_pricing.DEFAULT_RISK_FREE_RATE,
        volatility: float | None = None,
        underlying_price: float | None = None,
    ) -> dict | None:
        """Works out the option's fair price and greeks with the pricing model that fits its underlying.

        The model is Black-76 when the option is priced off a future and Black-Scholes otherwise, as `implied_volatility` explains, and the answer names it. Under Black-76 delta and gamma are measured against the future's price, and rho holds that price still, so it only discounts. Without a volatility, the option's implied volatility is used, so the fair price equals the last price and the greeks describe the option as the market prices it. Theta is per calendar day, and vega and rho are per percentage point, which is how brokers' option chains show them.

        Args:
            risk_free_rate: The float annual risk-free interest rate, continuously compounded, such as 0.065 for 6.5 per cent.
            volatility: The float annual volatility to use, such as 0.12 for 12 per cent, or None to use the option's implied volatility.
            underlying_price: The float price of the underlying to use, or None to read the underlying's last price from UBI.

        Returns:
            A dict with `model`, the str `black_76` or `black_scholes`, and `volatility`, `price`, `delta`, `gamma`, `theta`, `vega` and `rho`, each a float, or None when the prices needed are unknown, when the option is at or past 15:30 India time on its expiry date, or when no implied volatility can be found.

        Raises:
            ValueError: underlying_price or volatility is given and is not above zero.
            UnderlyingError: No underlying price is given and the option's underlying cannot be found.
            ServiceUnavailableError: UBI has no recent quote for the option, or for the underlying when no price is given.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        years_to_expiry = self._years_to_expiry()
        if years_to_expiry <= 0:
            return None
        if underlying_price is None:
            underlying_price = self.underlying_price
        if underlying_price is None:
            return None
        if volatility is None:
            volatility = self.implied_volatility(
                risk_free_rate=risk_free_rate,
                underlying_price=underlying_price,
            )
        if volatility is None:
            return None
        model_class = self._pricing_model()
        model = model_class(
            underlying_price,
            self.strike_price,
            years_to_expiry,
            risk_free_rate,
            volatility,
            self.is_call,
        )
        if model_class is option_pricing.Black76:
            model_name = BLACK_76_MODEL
        else:
            model_name = BLACK_SCHOLES_MODEL
        return {
            "model": model_name,
            "volatility": volatility,
            "price": model.price,
            "delta": model.delta,
            "gamma": model.gamma,
            "theta": model.theta,
            "vega": model.vega,
            "rho": model.rho,
        }

    def _pricing_model(self) -> type[option_pricing.OptionPricingModel]:
        """Picks the pricing model that fits what the option is priced off.

        Returns:
            The class option_pricing.Black76 when the option is priced off a future, and option_pricing.BlackScholes otherwise.

        Raises:
            Nothing.
        """
        if self._underlying_is_future():
            return option_pricing.Black76
        return option_pricing.BlackScholes

    def _intrinsic_value_at(self, underlying_price: float) -> float:
        """Works out the option's intrinsic value at a given underlying price.

        Args:
            underlying_price: The float price of the underlying.

        Returns:
            The float intrinsic value, never less than zero.

        Raises:
            Nothing.
        """
        if self.is_call:
            return max(underlying_price - self.strike_price, 0.0)
        return max(self.strike_price - underlying_price, 0.0)

    def _years_to_expiry(self) -> float:
        """Works out the time from now until 15:30 India time on the expiry date, in years.

        Returns:
            The float number of years, which is zero or negative at or after that moment.

        Raises:
            Nothing.
        """
        expiry_moment = datetime.datetime.combine(
            self.expiry_date,
            EXPIRY_TIME,
            INDIA_TIME_ZONE,
        )
        now = datetime.datetime.now(INDIA_TIME_ZONE)
        return (expiry_moment - now).total_seconds() / SECONDS_PER_YEAR


class IndexFutures(Futures):
    """A futures contract on an index, which settles in cash because an index cannot be delivered.

    It adds a guarantee to `Futures` rather than members: the contract is in an index futures segment, so its default underlying is the index, found by symbol as a `NonTradeableInstrument` unless it is given or UBI links it. The family classes such as `tradingmachine.assets.equities.EquityIndexFutures` inherit it.
    """

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
        underlying: Instrument | None = None,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the contract up in UBI and checks that it is a futures contract on an index.

        Args:
            instrument_id: The str UUID of the contract, or None to look it up by exchange, segment and identity fields.
            exchange: The str exchange, such as `nse`, or None when instrument_id is given.
            segment: The str segment, bare such as `equity_index_futures` or prefixed such as `nse_equity_index_futures`, or None when instrument_id is given.
            symbol: The str symbol of a security, or None, since a contract has none.
            underlying_symbol: The str symbol of the index, such as `NIFTY`, or None when instrument_id is given.
            expiry_date: The expiry of the contract as a datetime.date or a `YYYY-MM-DD` str, or None when instrument_id is given.
            strike_price: A float strike price, or None, since a future has none.
            option_type: A str option type, or None, since a future has none.
            underlying: The Instrument the contract is written on, such as an Equity, an EquityIndex or a future, which the contract keeps and uses for `underlying` and `underlying_price`, or None to use UBI's link to the underlying or else the family's default, looked up on every read.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            TypeError: underlying is given and is not an Instrument.
            IndexFuturesError: The contract is a future on something other than an index.
            FuturesError: The instrument is an option rather than a future.
            DerivativeError: The instrument is not a contract at all, or has no expiry date.
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
            underlying=underlying,
            unified_broker_interface=unified_broker_interface,
        )
        if not self.segment.endswith(INDEX_FUTURES_SEGMENT_SUFFIX):
            raise exceptions.IndexFuturesError(
                f"Only a futures contract on an index is an {type(self).__name__}, and this is in {self.segment}: {self!r}"
            )


class IndexOption(Option):
    """An option on an index, which settles in cash because an index cannot be delivered.

    It adds a guarantee to `Option` rather than members: the option is in an index options segment, so its default underlying is the index, found by symbol as a `NonTradeableInstrument` unless it is given or UBI links it. The family classes such as `tradingmachine.assets.equities.EquityIndexOption` inherit it.
    """

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
        underlying: Instrument | None = None,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the option up in UBI and checks that it is an option on an index.

        Args:
            instrument_id: The str UUID of the option, or None to look it up by exchange, segment and identity fields.
            exchange: The str exchange, such as `nse`, or None when instrument_id is given.
            segment: The str segment, bare such as `equity_index_options` or prefixed such as `nse_equity_index_options`, or None when instrument_id is given.
            symbol: The str symbol of a security, or None, since an option has none.
            underlying_symbol: The str symbol of the index, such as `NIFTY`, or None when instrument_id is given.
            expiry_date: The expiry of the option as a datetime.date or a `YYYY-MM-DD` str, or None when instrument_id is given.
            strike_price: The float strike price of the option in index points, or None when instrument_id is given.
            option_type: The str option type, `CE` for a call or `PE` for a put, or None when instrument_id is given.
            underlying: The Instrument the contract is written on, such as an Equity, an EquityIndex or a future, which the contract keeps and uses for `underlying` and `underlying_price`, or None to use UBI's link to the underlying or else the family's default, looked up on every read.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            TypeError: underlying is given and is not an Instrument.
            IndexOptionError: The option is written on something other than an index.
            OptionError: The instrument is a future rather than an option, or UBI gave it no strike price or option type.
            DerivativeError: The instrument is not a contract at all, or has no expiry date.
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
            underlying=underlying,
            unified_broker_interface=unified_broker_interface,
        )
        if not self.segment.endswith(INDEX_OPTIONS_SEGMENT_SUFFIX):
            raise exceptions.IndexOptionError(
                f"Only an option on an index is an {type(self).__name__}, and this is in {self.segment}: {self!r}"
            )
