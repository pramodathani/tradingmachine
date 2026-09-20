"""The commodity family: commodities, commodity indices, and the futures and options written on each of them.

Each of the six classes fixes one of UBI's commodity segments, so the kind of contract is the class rather than a segment name passed by hand, and each constructor asks for exactly the fields that identify one of its own contracts. `Commodity` and `CommodityIndex` are named by exchange and symbol, the futures classes by exchange, underlying symbol and expiry date, and the option classes by those three plus a strike price and an option type.

Symbols are readable tickers, such as `GOLD`, `CRUDEOIL` and `ALUMINIUM` for a commodity and `MCXBULLDEX` or `MCXCOMDEX` for an index. UBI carries commodities on three exchanges, `mcx`, `ncdex` and `nse`, and the indices and their derivatives on `mcx` and `ncdex` only.

`CommodityIndex` is built on `instruments.NonTradeableInstrument`, because an index cannot be traded. The other five are built on `instruments.TradeableInstrument`, so they carry the order-book values as well. All six inherit every analysis class through `instruments.Instrument`.

Three things about ordering in this family differ from equities, and two of them cost money if they are assumed away.

A quantity is counted in quotation units and must be a whole number of lots. A commodity market is not a securities market, so UBI measures the quantity against the contract's size and refuses anything that is not an exact multiple: `quantity=1` on an MCX gold future is answered with HTTP 400 and `quantity must be a whole number of lots of 100`, while `quantity=100` is one lot. UBI converts that figure to whatever each broker counts in before sending, so the number given here is the same whichever broker takes the order. On the `ncdex` the quotation unit is tonnes, although prices are quoted in quintals.

A `Commodity` cannot be ordered at all, although it inherits every order method. Its rows are the exchange's underlying reference records rather than tradeable spot contracts, no broker declares a cash market for commodities, and UBI's contract size check refuses any order in this family that is not a future or an option. Every order method on `Commodity` therefore fails, and `CommodityIndex` cannot be traded either by the ordinary index rule.

An order can also be refused for a reason that has nothing to do with the order. UBI decides each contract's size once every morning from the exchanges' own fields, and when its sources disagree the contract is untradeable for the day. That is answered with HTTP 503 and a `contract_size_status` of `conflict`, `undecided`, `no_source` or `single_source`, which means UBI does not trust the contract's size today rather than that UBI is unavailable.

A commodity or a commodity index has no quote, because the tick streams only resolve a token to a derivative segment, so `quote`, `last_price`, `ohlc` and the order-book values raise `ServiceUnavailableError` for `Commodity` and `CommodityIndex`. The four derivative classes are quoted normally, and unlike every other family ported so far they also have candles, so the analysis methods work on them.

A derivative does not hold an object for its underlying, as in `assets.equities`, even though the symbols match in this family.

Typical usage example:

  expiries = commodities.CommodityFutures.expiries(exchange="mcx", underlying_symbol="GOLD")
  contract = commodities.CommodityFutures(
      exchange="mcx",
      underlying_symbol="GOLD",
      expiry_date=expiries[0],
  )
  price = contract.last_price()
  frame = contract.relative_strength_index(window=14, days=90)

  index = commodities.CommodityIndex(exchange="mcx", symbol="MCXBULLDEX")
  chain = commodities.CommodityIndexOption.chain(
      exchange="mcx",
      underlying_symbol="MCXBULLDEX",
      expiry_date=expiries[0],
  )
"""

import datetime

import pandas as pd

from assets import exceptions
from assets import instruments
from ubi_client import client

SEARCH_LIMIT = 50

COMMODITY_SEGMENT = "commodities"

COMMODITY_FUTURES_SEGMENT = "commodity_futures"

COMMODITY_OPTIONS_SEGMENT = "commodity_options"

COMMODITY_INDICES_SEGMENT = "commodity_indices"

COMMODITY_INDEX_FUTURES_SEGMENT = "commodity_index_futures"

COMMODITY_INDEX_OPTIONS_SEGMENT = "commodity_index_options"


class Commodity(instruments.TradeableInstrument):
    """One commodity the exchange publishes as an underlying, such as GOLD on the mcx."""

    def __init__(
        self,
        exchange: str,
        symbol: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the commodity up in UBI's commodities segment and keeps its details.

        A commodity cannot be ordered or quoted, although it inherits the methods for both. Its row is the exchange's underlying reference record rather than a tradeable spot contract, so an order is refused by UBI and a quote raises `ServiceUnavailableError`. Use `CommodityFutures` or `CommodityOption` to trade it.

        Args:
            exchange: The str exchange the commodity is published on, `mcx`, `ncdex` or `nse`.
            symbol: The str symbol of the commodity, such as `GOLD` or `CRUDEOIL`.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            CommodityError: UBI has no commodity with that symbol on that exchange, or the instrument it returned is not in the commodities segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=COMMODITY_SEGMENT,
                symbol=symbol,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.CommodityError(
                f"UBI has no {exchange} commodity for the symbol {symbol}"
            ) from error
        if self.segment != f"{self.exchange}_{COMMODITY_SEGMENT}":
            raise exceptions.CommodityError(
                f"An instrument outside the {COMMODITY_SEGMENT} segment is not a Commodity: {self!r}"
            )

    @classmethod
    def search(
        cls,
        exchange: str,
        term: str,
        limit: int = SEARCH_LIMIT,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> pd.DataFrame | None:
        """Finds commodities whose symbol contains a term.

        UBI puts an exact match first, then symbols starting with the term, then symbols containing it, so a partial name such as `CRUDE` finds CRUDEOIL near the top.

        Args:
            exchange: The str exchange to search, such as `mcx`.
            term: The str the symbol must contain, matched without regard to case.
            limit: The int most rows to return, which UBI caps at 200.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame with `instrument_id`, `exchange`, `segment`, `shape`, `symbol` and the derivative fields left empty, or None when no commodity matches.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._search_catalogue(
            exchange,
            COMMODITY_SEGMENT,
            term,
            limit,
            unified_broker_interface,
        )


class CommodityFutures(instruments.TradeableInstrument):
    """One futures contract on a commodity, such as GOLD expiring in October."""

    def __init__(
        self,
        exchange: str,
        underlying_symbol: str,
        expiry_date: datetime.date | str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the contract up in UBI's commodity futures segment and keeps its details.

        An order's quantity is counted in quotation units and must be a whole number of lots, so `quantity=100` is one lot of a contract whose lot is 100 and `quantity=1` is refused.

        Args:
            exchange: The str exchange the contract trades on, `mcx`, `ncdex` or `nse`.
            underlying_symbol: The str symbol of the commodity the contract is written on, such as `GOLD`.
            expiry_date: The day the contract expires, as a datetime.date or a `YYYY-MM-DD` str.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            CommodityFuturesError: UBI has no such contract, or the instrument it returned is not in the commodity futures segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=COMMODITY_FUTURES_SEGMENT,
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.CommodityFuturesError(
                f"UBI has no {exchange} commodity futures contract on {underlying_symbol} expiring {expiry_date}"
            ) from error
        if self.segment != f"{self.exchange}_{COMMODITY_FUTURES_SEGMENT}":
            raise exceptions.CommodityFuturesError(
                f"An instrument outside the {COMMODITY_FUTURES_SEGMENT} segment is not a CommodityFutures: {self!r}"
            )

    @classmethod
    def expiries(
        cls,
        exchange: str,
        underlying_symbol: str,
        include_expired: bool = False,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> list[datetime.date]:
        """Lists the expiries a commodity's futures contracts are listed for.

        A contract expiring today counts as live, because it can still be traded until the market closes.

        Args:
            exchange: The str exchange, such as `mcx`.
            underlying_symbol: The str symbol of the commodity, such as `GOLD`.
            include_expired: A bool that is True to include expiries that have already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of datetime.date, soonest first, which is empty when nothing is listed on this underlying.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._expiry_dates(
            exchange,
            COMMODITY_FUTURES_SEGMENT,
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
        """Lists the futures contracts on commodities that are listed.

        The rows are identities rather than objects, because building an object looks each contract up in UBI and a long list would mean a request for every row. Build the ones you want from the rows.

        Args:
            exchange: The str exchange, such as `mcx`.
            underlying_symbol: The str symbol of the commodity to keep, such as `GOLD`, or None to list every underlying.
            include_expired: A bool that is True to include contracts whose expiry has already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame with `instrument_id`, `exchange`, `segment`, `shape`, `underlying_symbol` and `expiry_date`, sorted by expiry, or None when nothing matches.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._contracts_for(
            exchange,
            COMMODITY_FUTURES_SEGMENT,
            underlying_symbol,
            None,
            include_expired,
            unified_broker_interface,
        )


class CommodityOption(instruments.TradeableInstrument):
    """One option on a commodity, such as a GOLD call at a given strike and expiry."""

    def __init__(
        self,
        exchange: str,
        underlying_symbol: str,
        expiry_date: datetime.date | str,
        strike_price: float,
        option_type: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the option up in UBI's commodity options segment and keeps its details.

        An order's quantity is counted in quotation units and must be a whole number of lots, so `quantity=100` is one lot of a contract whose lot is 100 and `quantity=1` is refused.

        Args:
            exchange: The str exchange the option trades on, `mcx`, `ncdex` or `nse`.
            underlying_symbol: The str symbol of the commodity the option is written on, such as `GOLD`.
            expiry_date: The day the option expires, as a datetime.date or a `YYYY-MM-DD` str.
            strike_price: The float strike price of the option in the commodity's own quotation units.
            option_type: The str option type, `CE` for a call or `PE` for a put.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            CommodityOptionError: UBI has no such option, or the instrument it returned is not in the commodity options segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=COMMODITY_OPTIONS_SEGMENT,
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date,
                strike_price=strike_price,
                option_type=option_type,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.CommodityOptionError(
                f"UBI has no {exchange} commodity option on {underlying_symbol} expiring {expiry_date} at strike {strike_price} {option_type}"
            ) from error
        if self.segment != f"{self.exchange}_{COMMODITY_OPTIONS_SEGMENT}":
            raise exceptions.CommodityOptionError(
                f"An instrument outside the {COMMODITY_OPTIONS_SEGMENT} segment is not a CommodityOption: {self!r}"
            )

    @classmethod
    def expiries(
        cls,
        exchange: str,
        underlying_symbol: str,
        include_expired: bool = False,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> list[datetime.date]:
        """Lists the expiries a commodity's options are listed for.

        A contract expiring today counts as live, because it can still be traded until the market closes.

        Args:
            exchange: The str exchange, such as `mcx`.
            underlying_symbol: The str symbol of the commodity, such as `GOLD`.
            include_expired: A bool that is True to include expiries that have already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of datetime.date, soonest first, which is empty when nothing is listed on this underlying.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._expiry_dates(
            exchange,
            COMMODITY_OPTIONS_SEGMENT,
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
        """Lists the strike prices listed on one commodity for one expiry.

        Args:
            exchange: The str exchange, such as `mcx`.
            underlying_symbol: The str symbol of the commodity, such as `GOLD`.
            expiry_date: The expiry to list, as a datetime.date or a `YYYY-MM-DD` str.
            include_expired: A bool that is True to allow an expiry that has already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of float strike prices in the commodity's own quotation units, lowest first, which is empty when nothing is listed for that expiry.

        Raises:
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
        """Lists every option listed on one commodity for one expiry.

        The rows are identities rather than objects, because building an object looks each contract up in UBI and a chain of hundreds of contracts would mean hundreds of requests. Build the few you want from the rows.

        Args:
            exchange: The str exchange, such as `mcx`.
            underlying_symbol: The str symbol of the commodity, such as `GOLD`.
            expiry_date: The expiry to list, as a datetime.date or a `YYYY-MM-DD` str.
            include_expired: A bool that is True to allow an expiry that has already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame with `instrument_id`, `exchange`, `segment`, `shape`, `underlying_symbol`, `expiry_date`, `strike_price` and `option_type`, sorted by strike price and then option type, or None when nothing matches.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            ValueError: expiry_date is a str that is not a valid ISO date.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._contracts_for(
            exchange,
            COMMODITY_OPTIONS_SEGMENT,
            underlying_symbol,
            expiry_date,
            include_expired,
            unified_broker_interface,
        )


class CommodityIndex(instruments.NonTradeableInstrument):
    """One commodity index, such as MCXBULLDEX on the mcx, which is followed rather than traded."""

    def __init__(
        self,
        exchange: str,
        symbol: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the index up in UBI's commodity indices segment and keeps its details.

        No broker's tick stream resolves a commodity index, so `quote`, `last_price` and `ohlc` raise `ServiceUnavailableError` even though the index itself is listed.

        Args:
            exchange: The str exchange that publishes the index, `mcx` or `ncdex`.
            symbol: The str symbol of the index, such as `MCXBULLDEX` or `MCXCOMDEX`.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            CommodityIndexError: UBI has no index with that symbol on that exchange, or the instrument it returned is not in the commodity indices segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=COMMODITY_INDICES_SEGMENT,
                symbol=symbol,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.CommodityIndexError(
                f"UBI has no {exchange} commodity index for the symbol {symbol}"
            ) from error
        if self.segment != f"{self.exchange}_{COMMODITY_INDICES_SEGMENT}":
            raise exceptions.CommodityIndexError(
                f"An instrument outside the {COMMODITY_INDICES_SEGMENT} segment is not a CommodityIndex: {self!r}"
            )

    @classmethod
    def search(
        cls,
        exchange: str,
        term: str,
        limit: int = SEARCH_LIMIT,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> pd.DataFrame | None:
        """Finds commodity indices whose symbol contains a term.

        UBI puts an exact match first, then symbols starting with the term, then symbols containing it, so a partial name such as `BULL` finds MCXBULLDEX near the top.

        Args:
            exchange: The str exchange to search, such as `mcx`.
            term: The str the symbol must contain, matched without regard to case.
            limit: The int most rows to return, which UBI caps at 200.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame with `instrument_id`, `exchange`, `segment`, `shape`, `symbol` and the derivative fields left empty, or None when no index matches.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._search_catalogue(
            exchange,
            COMMODITY_INDICES_SEGMENT,
            term,
            limit,
            unified_broker_interface,
        )


class CommodityIndexFutures(instruments.TradeableInstrument):
    """One futures contract on a commodity index, such as MCXBULLDEX expiring in October."""

    def __init__(
        self,
        exchange: str,
        underlying_symbol: str,
        expiry_date: datetime.date | str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the contract up in UBI's commodity index futures segment and keeps its details.

        An order's quantity is counted in quotation units and must be a whole number of lots, so `quantity=30` is one lot of a contract whose lot is 30 and `quantity=1` is refused.

        Args:
            exchange: The str exchange the contract trades on, such as `mcx`.
            underlying_symbol: The str symbol of the index the contract is written on, such as `MCXBULLDEX`.
            expiry_date: The day the contract expires, as a datetime.date or a `YYYY-MM-DD` str.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            CommodityIndexFuturesError: UBI has no such contract, or the instrument it returned is not in the commodity index futures segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=COMMODITY_INDEX_FUTURES_SEGMENT,
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.CommodityIndexFuturesError(
                f"UBI has no {exchange} commodity index futures contract on {underlying_symbol} expiring {expiry_date}"
            ) from error
        if self.segment != f"{self.exchange}_{COMMODITY_INDEX_FUTURES_SEGMENT}":
            raise exceptions.CommodityIndexFuturesError(
                f"An instrument outside the {COMMODITY_INDEX_FUTURES_SEGMENT} segment is not a CommodityIndexFutures: {self!r}"
            )

    @classmethod
    def expiries(
        cls,
        exchange: str,
        underlying_symbol: str,
        include_expired: bool = False,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> list[datetime.date]:
        """Lists the expiries an index's futures contracts are listed for.

        A contract expiring today counts as live, because it can still be traded until the market closes.

        Args:
            exchange: The str exchange, such as `mcx`.
            underlying_symbol: The str symbol of the index, such as `MCXBULLDEX`.
            include_expired: A bool that is True to include expiries that have already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of datetime.date, soonest first, which is empty when nothing is listed on this underlying.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._expiry_dates(
            exchange,
            COMMODITY_INDEX_FUTURES_SEGMENT,
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
        """Lists the futures contracts on commodity indices that are listed.

        The rows are identities rather than objects, because building an object looks each contract up in UBI and a long list would mean a request for every row. Build the ones you want from the rows.

        Args:
            exchange: The str exchange, such as `mcx`.
            underlying_symbol: The str symbol of the index to keep, such as `MCXBULLDEX`, or None to list every underlying.
            include_expired: A bool that is True to include contracts whose expiry has already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame with `instrument_id`, `exchange`, `segment`, `shape`, `underlying_symbol` and `expiry_date`, sorted by expiry, or None when nothing matches.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._contracts_for(
            exchange,
            COMMODITY_INDEX_FUTURES_SEGMENT,
            underlying_symbol,
            None,
            include_expired,
            unified_broker_interface,
        )


class CommodityIndexOption(instruments.TradeableInstrument):
    """One option on a commodity index, such as an MCXBULLDEX call at a given strike and expiry."""

    def __init__(
        self,
        exchange: str,
        underlying_symbol: str,
        expiry_date: datetime.date | str,
        strike_price: float,
        option_type: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the option up in UBI's commodity index options segment and keeps its details.

        An order's quantity is counted in quotation units and must be a whole number of lots, so `quantity=30` is one lot of a contract whose lot is 30 and `quantity=1` is refused.

        Args:
            exchange: The str exchange the option trades on, such as `mcx`.
            underlying_symbol: The str symbol of the index the option is written on, such as `MCXBULLDEX`.
            expiry_date: The day the option expires, as a datetime.date or a `YYYY-MM-DD` str.
            strike_price: The float strike price of the option in the index's own units.
            option_type: The str option type, `CE` for a call or `PE` for a put.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            CommodityIndexOptionError: UBI has no such option, or the instrument it returned is not in the commodity index options segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=COMMODITY_INDEX_OPTIONS_SEGMENT,
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date,
                strike_price=strike_price,
                option_type=option_type,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.CommodityIndexOptionError(
                f"UBI has no {exchange} commodity index option on {underlying_symbol} expiring {expiry_date} at strike {strike_price} {option_type}"
            ) from error
        if self.segment != f"{self.exchange}_{COMMODITY_INDEX_OPTIONS_SEGMENT}":
            raise exceptions.CommodityIndexOptionError(
                f"An instrument outside the {COMMODITY_INDEX_OPTIONS_SEGMENT} segment is not a CommodityIndexOption: {self!r}"
            )

    @classmethod
    def expiries(
        cls,
        exchange: str,
        underlying_symbol: str,
        include_expired: bool = False,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> list[datetime.date]:
        """Lists the expiries an index's options are listed for.

        A contract expiring today counts as live, because it can still be traded until the market closes.

        Args:
            exchange: The str exchange, such as `mcx`.
            underlying_symbol: The str symbol of the index, such as `MCXBULLDEX`.
            include_expired: A bool that is True to include expiries that have already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of datetime.date, soonest first, which is empty when nothing is listed on this underlying.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._expiry_dates(
            exchange,
            COMMODITY_INDEX_OPTIONS_SEGMENT,
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
        """Lists the strike prices listed on one commodity index for one expiry.

        Args:
            exchange: The str exchange, such as `mcx`.
            underlying_symbol: The str symbol of the index, such as `MCXBULLDEX`.
            expiry_date: The expiry to list, as a datetime.date or a `YYYY-MM-DD` str.
            include_expired: A bool that is True to allow an expiry that has already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of float strike prices in the index's own units, lowest first, which is empty when nothing is listed for that expiry.

        Raises:
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
        """Lists every option listed on one commodity index for one expiry.

        The rows are identities rather than objects, because building an object looks each contract up in UBI and a long chain would mean a request for every row. Build the few you want from the rows.

        Args:
            exchange: The str exchange, such as `mcx`.
            underlying_symbol: The str symbol of the index, such as `MCXBULLDEX`.
            expiry_date: The expiry to list, as a datetime.date or a `YYYY-MM-DD` str.
            include_expired: A bool that is True to allow an expiry that has already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame with `instrument_id`, `exchange`, `segment`, `shape`, `underlying_symbol`, `expiry_date`, `strike_price` and `option_type`, sorted by strike price and then option type, or None when nothing matches.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            ValueError: expiry_date is a str that is not a valid ISO date.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._contracts_for(
            exchange,
            COMMODITY_INDEX_OPTIONS_SEGMENT,
            underlying_symbol,
            expiry_date,
            include_expired,
            unified_broker_interface,
        )
