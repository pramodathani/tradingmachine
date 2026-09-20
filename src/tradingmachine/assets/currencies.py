"""The currency family: currency pairs and the futures and options written on them.

Each of the six classes fixes one of UBI's currency segments, so the kind of contract is the class rather than a segment name passed by hand, and each constructor asks for exactly the fields that identify one of its own contracts. `Currency` and `CurrencyIndex` are named by exchange and symbol, the futures classes by exchange, underlying symbol and expiry date, and the option classes by those three plus a strike price and an option type.

Symbols are the readable pair names, and UBI carries only seven of them on the nse: `EURINR`, `EURUSD`, `GBPINR`, `GBPUSD`, `JPYINR`, `USDINR` and `USDJPY`. The bse adds over-the-counter variants such as `EURINROTC`. Currencies trade on the nse and the bse only.

Half of this family does not exist in UBI. There are no rows at all in `currency_indices`, `currency_index_futures` or `currency_index_options`, on any exchange, and no broker maps anything into them, so `CurrencyIndex`, `CurrencyIndexFutures` and `CurrencyIndexOption` resolve nothing today. They are written so that the family has the same shape as every other asset class and so that they work the moment UBI gains a mapping, and they fail cleanly: a lookup raises the class's own error and the discovery calls return an empty list or None.

`CurrencyIndex` is built on `instruments.NonTradeableInstrument`, because an index cannot be traded. The other five are built on `instruments.TradeableInstrument`, so they carry the order-book values as well. All six inherit every analysis class through `instruments.Instrument`.

Ordering here works as it does for commodities rather than for shares. A quantity is counted in quotation units and must be a whole number of lots, because a currency market is not a securities market, so UBI measures the quantity against the contract's size and refuses anything that is not an exact multiple. An order can also be refused with HTTP 503 and a `contract_size_status` when UBI does not trust the contract's size for the day, which means the contract rather than the service is the problem.

A `Currency` cannot be ordered at all, although it inherits every order method. Its rows are the exchange's underlying reference records rather than tradeable spot contracts, no broker declares a cash market for currencies, and UBI's contract size check refuses any order in this family that is not a future or an option.

Coverage of prices is thinner than for commodities. A currency pair itself has no quote, because the tick streams only resolve a token to a derivative segment. The nse derivatives are quoted, the bse ones are not, and UBI stores no candles for anything in this family, so `prices` returns None and the analysis methods have nothing to work on.

A derivative does not hold an object for its underlying, as in `tradingmachine.assets.equities`, even though the symbols match in this family.

Typical usage example:

  expiries = currencies.CurrencyFutures.expiries(exchange="nse", underlying_symbol="USDINR")
  contract = currencies.CurrencyFutures(
      exchange="nse",
      underlying_symbol="USDINR",
      expiry_date=expiries[0],
  )
  rate = contract.last_price()

  chain = currencies.CurrencyOption.chain(
      exchange="nse",
      underlying_symbol="USDINR",
      expiry_date=expiries[0],
  )
"""

import datetime

import pandas as pd

from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments
from tradingmachine.ubi_client import client

SEARCH_LIMIT = 50

CURRENCY_SEGMENT = "currencies"

CURRENCY_FUTURES_SEGMENT = "currency_futures"

CURRENCY_OPTIONS_SEGMENT = "currency_options"

CURRENCY_INDICES_SEGMENT = "currency_indices"

CURRENCY_INDEX_FUTURES_SEGMENT = "currency_index_futures"

CURRENCY_INDEX_OPTIONS_SEGMENT = "currency_index_options"


class Currency(instruments.TradeableInstrument):
    """One currency pair the exchange publishes as an underlying, such as USDINR on the nse."""

    def __init__(
        self,
        exchange: str,
        symbol: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the pair up in UBI's currencies segment and keeps its details.

        A currency pair cannot be ordered or quoted, although it inherits the methods for both. Its row is the exchange's underlying reference record rather than a tradeable spot contract, so an order is refused by UBI and a quote raises `ServiceUnavailableError`. Use `CurrencyFutures` or `CurrencyOption` to trade it.

        Args:
            exchange: The str exchange the pair is published on, `nse` or `bse`.
            symbol: The str symbol of the pair, such as `USDINR` or `EURINR`.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            CurrencyError: UBI has no pair with that symbol on that exchange, or the instrument it returned is not in the currencies segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=CURRENCY_SEGMENT,
                symbol=symbol,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.CurrencyError(
                f"UBI has no {exchange} currency pair for the symbol {symbol}"
            ) from error
        if self.segment != f"{self.exchange}_{CURRENCY_SEGMENT}":
            raise exceptions.CurrencyError(
                f"An instrument outside the {CURRENCY_SEGMENT} segment is not a Currency: {self!r}"
            )

    @classmethod
    def search(
        cls,
        exchange: str,
        term: str,
        limit: int = SEARCH_LIMIT,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> pd.DataFrame | None:
        """Finds currency pairs whose symbol contains a term.

        UBI puts an exact match first, then symbols starting with the term, then symbols containing it, so a partial name such as `USD` finds USDINR near the top. UBI carries only seven pairs on the nse, so a short term may return all of them.

        Args:
            exchange: The str exchange to search, `nse` or `bse`.
            term: The str the symbol must contain, matched without regard to case.
            limit: The int most rows to return, which UBI caps at 200.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame with `instrument_id`, `exchange`, `segment`, `shape`, `symbol` and the derivative fields left empty, or None when no pair matches.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._search_catalogue(
            exchange,
            CURRENCY_SEGMENT,
            term,
            limit,
            unified_broker_interface,
        )


class CurrencyFutures(instruments.TradeableInstrument):
    """One futures contract on a currency pair, such as USDINR expiring in September."""

    def __init__(
        self,
        exchange: str,
        underlying_symbol: str,
        expiry_date: datetime.date | str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the contract up in UBI's currency futures segment and keeps its details.

        An order's quantity is counted in quotation units and must be a whole number of lots. Only the nse contracts are quoted; a bse contract resolves but has no quote, so `last_price` raises `ServiceUnavailableError` there.

        Args:
            exchange: The str exchange the contract trades on, `nse` or `bse`.
            underlying_symbol: The str symbol of the pair the contract is written on, such as `USDINR`.
            expiry_date: The day the contract expires, as a datetime.date or a `YYYY-MM-DD` str.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            CurrencyFuturesError: UBI has no such contract, or the instrument it returned is not in the currency futures segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=CURRENCY_FUTURES_SEGMENT,
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.CurrencyFuturesError(
                f"UBI has no {exchange} currency futures contract on {underlying_symbol} expiring {expiry_date}"
            ) from error
        if self.segment != f"{self.exchange}_{CURRENCY_FUTURES_SEGMENT}":
            raise exceptions.CurrencyFuturesError(
                f"An instrument outside the {CURRENCY_FUTURES_SEGMENT} segment is not a CurrencyFutures: {self!r}"
            )

    @classmethod
    def expiries(
        cls,
        exchange: str,
        underlying_symbol: str,
        include_expired: bool = False,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> list[datetime.date]:
        """Lists the expiries a pair's futures contracts are listed for.

        A contract expiring today counts as live, because it can still be traded until the market closes.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the pair, such as `USDINR`.
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
            CURRENCY_FUTURES_SEGMENT,
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
        """Lists the futures contracts on currency pairs that are listed.

        The rows are identities rather than objects, because building an object looks each contract up in UBI and a long list would mean a request for every row. Build the ones you want from the rows.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the pair to keep, such as `USDINR`, or None to list every underlying.
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
            CURRENCY_FUTURES_SEGMENT,
            underlying_symbol,
            None,
            include_expired,
            unified_broker_interface,
        )


class CurrencyOption(instruments.TradeableInstrument):
    """One option on a currency pair, such as a USDINR call at a given strike and expiry."""

    def __init__(
        self,
        exchange: str,
        underlying_symbol: str,
        expiry_date: datetime.date | str,
        strike_price: float,
        option_type: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the option up in UBI's currency options segment and keeps its details.

        An order's quantity is counted in quotation units and must be a whole number of lots.

        Args:
            exchange: The str exchange the option trades on, `nse` or `bse`.
            underlying_symbol: The str symbol of the pair the option is written on, such as `USDINR`.
            expiry_date: The day the option expires, as a datetime.date or a `YYYY-MM-DD` str.
            strike_price: The float strike price of the option, quoted in the pair's own rate units.
            option_type: The str option type, `CE` for a call or `PE` for a put.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            CurrencyOptionError: UBI has no such option, or the instrument it returned is not in the currency options segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=CURRENCY_OPTIONS_SEGMENT,
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date,
                strike_price=strike_price,
                option_type=option_type,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.CurrencyOptionError(
                f"UBI has no {exchange} currency option on {underlying_symbol} expiring {expiry_date} at strike {strike_price} {option_type}"
            ) from error
        if self.segment != f"{self.exchange}_{CURRENCY_OPTIONS_SEGMENT}":
            raise exceptions.CurrencyOptionError(
                f"An instrument outside the {CURRENCY_OPTIONS_SEGMENT} segment is not a CurrencyOption: {self!r}"
            )

    @classmethod
    def expiries(
        cls,
        exchange: str,
        underlying_symbol: str,
        include_expired: bool = False,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> list[datetime.date]:
        """Lists the expiries a pair's options are listed for.

        A contract expiring today counts as live, because it can still be traded until the market closes.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the pair, such as `USDINR`.
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
            CURRENCY_OPTIONS_SEGMENT,
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
        """Lists the strike prices listed on one pair for one expiry.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the pair, such as `USDINR`.
            expiry_date: The expiry to list, as a datetime.date or a `YYYY-MM-DD` str.
            include_expired: A bool that is True to allow an expiry that has already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of float strike prices in the pair's own rate units, lowest first, which is empty when nothing is listed for that expiry.

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
        """Lists every option listed on one currency pair for one expiry.

        The rows are identities rather than objects, because building an object looks each contract up in UBI and a chain of hundreds of contracts would mean hundreds of requests. Build the few you want from the rows.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the pair, such as `USDINR`.
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
            CURRENCY_OPTIONS_SEGMENT,
            underlying_symbol,
            expiry_date,
            include_expired,
            unified_broker_interface,
        )


class CurrencyIndex(instruments.NonTradeableInstrument):
    """One currency index, which UBI carries none of yet."""

    def __init__(
        self,
        exchange: str,
        symbol: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the index up in UBI's currency indices segment and keeps its details.

        No broker UBI maps lists a currency index, so this segment is empty and every lookup raises CurrencyIndexError today. The class exists so that the family is complete and so that these instruments work the moment UBI gains a mapping for them.

        Args:
            exchange: The str exchange that publishes the index, `nse` or `bse`.
            symbol: The str symbol of the index.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            CurrencyIndexError: UBI has no such index, which is true of every symbol today, or the instrument it returned is not in the currency indices segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=CURRENCY_INDICES_SEGMENT,
                symbol=symbol,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.CurrencyIndexError(
                f"UBI has no {exchange} currency index for the symbol {symbol}"
            ) from error
        if self.segment != f"{self.exchange}_{CURRENCY_INDICES_SEGMENT}":
            raise exceptions.CurrencyIndexError(
                f"An instrument outside the {CURRENCY_INDICES_SEGMENT} segment is not a CurrencyIndex: {self!r}"
            )

    @classmethod
    def search(
        cls,
        exchange: str,
        term: str,
        limit: int = SEARCH_LIMIT,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> pd.DataFrame | None:
        """Finds currency indices whose symbol contains a term, of which there are none.

        Args:
            exchange: The str exchange to search, `nse` or `bse`.
            term: The str the symbol must contain, matched without regard to case.
            limit: The int most rows to return, which UBI caps at 200.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame of identities, or None, which is what it returns while UBI carries no currency index.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._search_catalogue(
            exchange,
            CURRENCY_INDICES_SEGMENT,
            term,
            limit,
            unified_broker_interface,
        )


class CurrencyIndexFutures(instruments.TradeableInstrument):
    """One futures contract on a currency index, which UBI carries none of yet."""

    def __init__(
        self,
        exchange: str,
        underlying_symbol: str,
        expiry_date: datetime.date | str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the contract up in UBI's currency index futures segment and keeps its details.

        No broker UBI maps lists a futures contract on a currency index, so this segment is empty and every lookup raises CurrencyIndexFuturesError today. The class exists so that the family is complete and so that these contracts work the moment UBI gains a mapping for them.

        Args:
            exchange: The str exchange the contract trades on, `nse` or `bse`.
            underlying_symbol: The str symbol of the index the contract is written on.
            expiry_date: The day the contract expires, as a datetime.date or a `YYYY-MM-DD` str.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            CurrencyIndexFuturesError: UBI has no such contract, which is true of every one today, or the instrument it returned is not in the currency index futures segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=CURRENCY_INDEX_FUTURES_SEGMENT,
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.CurrencyIndexFuturesError(
                f"UBI has no {exchange} currency index futures contract on {underlying_symbol} expiring {expiry_date}"
            ) from error
        if self.segment != f"{self.exchange}_{CURRENCY_INDEX_FUTURES_SEGMENT}":
            raise exceptions.CurrencyIndexFuturesError(
                f"An instrument outside the {CURRENCY_INDEX_FUTURES_SEGMENT} segment is not a CurrencyIndexFutures: {self!r}"
            )

    @classmethod
    def expiries(
        cls,
        exchange: str,
        underlying_symbol: str,
        include_expired: bool = False,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> list[datetime.date]:
        """Lists the expiries an index's futures contracts are listed for, which is nothing today.

        A contract expiring today counts as live, because it can still be traded until the market closes.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the index.
            include_expired: A bool that is True to include expiries that have already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of datetime.date, soonest first, which is empty while UBI carries no futures contract on a currency index.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._expiry_dates(
            exchange,
            CURRENCY_INDEX_FUTURES_SEGMENT,
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
        """Lists the futures contracts on currency indices that are listed, of which there are none.

        The rows are identities rather than objects, because building an object looks each contract up in UBI and a long list would mean a request for every row. Build the ones you want from the rows.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the index to keep, or None to list every underlying.
            include_expired: A bool that is True to include contracts whose expiry has already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame of identities, or None, which is what it returns while UBI carries no futures contract on a currency index.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._contracts_for(
            exchange,
            CURRENCY_INDEX_FUTURES_SEGMENT,
            underlying_symbol,
            None,
            include_expired,
            unified_broker_interface,
        )


class CurrencyIndexOption(instruments.TradeableInstrument):
    """One option on a currency index, which UBI carries none of yet."""

    def __init__(
        self,
        exchange: str,
        underlying_symbol: str,
        expiry_date: datetime.date | str,
        strike_price: float,
        option_type: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the option up in UBI's currency index options segment and keeps its details.

        No broker UBI maps lists an option on a currency index, so this segment is empty and every lookup raises CurrencyIndexOptionError today. The class exists so that the family is complete and so that these contracts work the moment UBI gains a mapping for them.

        Args:
            exchange: The str exchange the option trades on, `nse` or `bse`.
            underlying_symbol: The str symbol of the index the option is written on.
            expiry_date: The day the option expires, as a datetime.date or a `YYYY-MM-DD` str.
            strike_price: The float strike price of the option in the index's own units.
            option_type: The str option type, `CE` for a call or `PE` for a put.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            CurrencyIndexOptionError: UBI has no such option, which is true of every one today, or the instrument it returned is not in the currency index options segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=CURRENCY_INDEX_OPTIONS_SEGMENT,
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date,
                strike_price=strike_price,
                option_type=option_type,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.CurrencyIndexOptionError(
                f"UBI has no {exchange} currency index option on {underlying_symbol} expiring {expiry_date} at strike {strike_price} {option_type}"
            ) from error
        if self.segment != f"{self.exchange}_{CURRENCY_INDEX_OPTIONS_SEGMENT}":
            raise exceptions.CurrencyIndexOptionError(
                f"An instrument outside the {CURRENCY_INDEX_OPTIONS_SEGMENT} segment is not a CurrencyIndexOption: {self!r}"
            )

    @classmethod
    def expiries(
        cls,
        exchange: str,
        underlying_symbol: str,
        include_expired: bool = False,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> list[datetime.date]:
        """Lists the expiries an index's options are listed for, which is nothing today.

        A contract expiring today counts as live, because it can still be traded until the market closes.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the index.
            include_expired: A bool that is True to include expiries that have already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of datetime.date, soonest first, which is empty while UBI carries no option on a currency index.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._expiry_dates(
            exchange,
            CURRENCY_INDEX_OPTIONS_SEGMENT,
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
        """Lists the strike prices listed on one currency index for one expiry, which is nothing today.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the index.
            expiry_date: The expiry to list, as a datetime.date or a `YYYY-MM-DD` str.
            include_expired: A bool that is True to allow an expiry that has already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of float strike prices in the index's own units, lowest first, which is empty while UBI carries no option on a currency index.

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
        """Lists every option listed on one currency index for one expiry, which is none today.

        The rows are identities rather than objects, because building an object looks each contract up in UBI and a long chain would mean a request for every row. Build the few you want from the rows.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the index.
            expiry_date: The expiry to list, as a datetime.date or a `YYYY-MM-DD` str.
            include_expired: A bool that is True to allow an expiry that has already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame of identities, or None, which is what it returns while UBI carries no option on a currency index.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            ValueError: expiry_date is a str that is not a valid ISO date.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._contracts_for(
            exchange,
            CURRENCY_INDEX_OPTIONS_SEGMENT,
            underlying_symbol,
            expiry_date,
            include_expired,
            unified_broker_interface,
        )
