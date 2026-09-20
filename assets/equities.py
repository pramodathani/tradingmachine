"""The equity family: shares, indices, and the futures and options written on each of them.

Each of the six classes fixes one of UBI's equity segments, so the kind of contract is the class rather than a segment name passed by hand, and each constructor asks for exactly the fields that identify one of its own contracts. `Equity` and `EquityIndex` are named by exchange and symbol, the futures classes by exchange, underlying symbol and expiry date, and the option classes by those three plus a strike price and an option type.

`EquityIndex` is built on `instruments.NonTradeableInstrument`, because an index cannot be traded. The other five are built on `instruments.TradeableInstrument`, so they carry the order-book values as well. All six inherit every analysis class through `instruments.Instrument`.

A derivative does not hold an object for its underlying. UBI links the two only by the underlying symbol matching a share's or an index's own symbol, with no key joining them, and that match is not guaranteed for every index, so the caller builds the underlying itself when it wants one.

Typical usage example:

  share = equities.Equity(exchange="nse", symbol="RELIANCE")
  frame = share.relative_strength_index(window=14, days=365)

  nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
  level = nifty.last_price()

  option = equities.EquityIndexOption(
      exchange="nse",
      underlying_symbol="NIFTY",
      expiry_date="2026-09-29",
      strike_price=25000,
      option_type="CE",
  )
  premium = option.last_price()
"""

import datetime

from assets import exceptions
from assets import instruments
from ubi_client import client

HOLDINGS_PATH = "/api/portfolio/holdings"

EQUITY_SEGMENT = "equities"

EQUITY_FUTURES_SEGMENT = "equity_futures"

EQUITY_OPTIONS_SEGMENT = "equity_options"

EQUITY_INDICES_SEGMENT = "equity_indices"

EQUITY_INDEX_FUTURES_SEGMENT = "equity_index_futures"

EQUITY_INDEX_OPTIONS_SEGMENT = "equity_index_options"


class Equity(instruments.TradeableInstrument):
    """One listed share, such as RELIANCE on the nse."""

    def __init__(
        self,
        exchange: str,
        symbol: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the share up in UBI's equities segment and keeps its details.

        Args:
            exchange: The str exchange the share is listed on, such as `nse`.
            symbol: The str symbol of the share, such as `RELIANCE`.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            EquityError: UBI has no share with that symbol on that exchange, or the instrument it returned is not in the equities segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=EQUITY_SEGMENT,
                symbol=symbol,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.EquityError(
                f"UBI has no {exchange} share for the symbol {symbol}"
            ) from error
        if self.segment != f"{self.exchange}_{EQUITY_SEGMENT}":
            raise exceptions.EquityError(
                f"An instrument outside the {EQUITY_SEGMENT} segment is not an Equity: {self!r}"
            )

    @property
    def holdings(self) -> dict | None:
        """The long-term holding of this share, merged across every broker.

        A share is the only thing in this module that can be held. A derivative is a position rather than a holding, and an index cannot be held at all.

        Reading this sends one request to UBI every time, because UBI serves the whole account's holdings and has no endpoint for a single instrument.

        Returns:
            A dict with `instrument_id`, `isin`, `symbol`, `exchange`, `segment`, `quantity`, `average_price`, `invested_value`, `last_price`, `current_value`, `pnl` and `collateral_quantity`, or None when no broker holds this share.

        Raises:
            ServiceUnavailableError: UBI's holdings document is missing or too old to serve.
            BrokerError: No broker's holdings could be read.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        rows = self._unified_broker_interface.get(HOLDINGS_PATH)["holdings"]
        for row in rows:
            if row["instrument_id"] == self.instrument_id:
                return row
        for row in rows:
            if row["symbol"] == self.symbol:
                return row
        return None


class EquityFutures(instruments.TradeableInstrument):
    """One futures contract on a share, such as RELIANCE expiring in September."""

    def __init__(
        self,
        exchange: str,
        underlying_symbol: str,
        expiry_date: datetime.date | str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the contract up in UBI's equity futures segment and keeps its details.

        Args:
            exchange: The str exchange the contract trades on, such as `nse`.
            underlying_symbol: The str symbol of the share the contract is written on, such as `RELIANCE`.
            expiry_date: The day the contract expires, as a datetime.date or a `YYYY-MM-DD` str.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            EquityFuturesError: UBI has no such contract, or the instrument it returned is not in the equity futures segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=EQUITY_FUTURES_SEGMENT,
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.EquityFuturesError(
                f"UBI has no {exchange} share futures contract on {underlying_symbol} expiring {expiry_date}"
            ) from error
        if self.segment != f"{self.exchange}_{EQUITY_FUTURES_SEGMENT}":
            raise exceptions.EquityFuturesError(
                f"An instrument outside the {EQUITY_FUTURES_SEGMENT} segment is not an EquityFutures: {self!r}"
            )


class EquityOption(instruments.TradeableInstrument):
    """One option on a share, such as a RELIANCE call at a given strike and expiry."""

    def __init__(
        self,
        exchange: str,
        underlying_symbol: str,
        expiry_date: datetime.date | str,
        strike_price: float,
        option_type: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the option up in UBI's equity options segment and keeps its details.

        Args:
            exchange: The str exchange the option trades on, such as `nse`.
            underlying_symbol: The str symbol of the share the option is written on, such as `RELIANCE`.
            expiry_date: The day the option expires, as a datetime.date or a `YYYY-MM-DD` str.
            strike_price: The float strike price of the option in rupees.
            option_type: The str option type, `CE` for a call or `PE` for a put.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            EquityOptionError: UBI has no such option, or the instrument it returned is not in the equity options segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=EQUITY_OPTIONS_SEGMENT,
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date,
                strike_price=strike_price,
                option_type=option_type,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.EquityOptionError(
                f"UBI has no {exchange} share option on {underlying_symbol} expiring {expiry_date} at strike {strike_price} {option_type}"
            ) from error
        if self.segment != f"{self.exchange}_{EQUITY_OPTIONS_SEGMENT}":
            raise exceptions.EquityOptionError(
                f"An instrument outside the {EQUITY_OPTIONS_SEGMENT} segment is not an EquityOption: {self!r}"
            )


class EquityIndex(instruments.NonTradeableInstrument):
    """One equity index, such as NIFTY on the nse, which is followed rather than traded."""

    def __init__(
        self,
        exchange: str,
        symbol: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the index up in UBI's equity indices segment and keeps its details.

        Args:
            exchange: The str exchange that publishes the index, such as `nse`.
            symbol: The str symbol of the index, such as `NIFTY` or `BANKNIFTY`.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            EquityIndexError: UBI has no index with that symbol on that exchange, or the instrument it returned is not in the equity indices segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=EQUITY_INDICES_SEGMENT,
                symbol=symbol,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.EquityIndexError(
                f"UBI has no {exchange} equity index for the symbol {symbol}"
            ) from error
        if self.segment != f"{self.exchange}_{EQUITY_INDICES_SEGMENT}":
            raise exceptions.EquityIndexError(
                f"An instrument outside the {EQUITY_INDICES_SEGMENT} segment is not an EquityIndex: {self!r}"
            )


class EquityIndexFutures(instruments.TradeableInstrument):
    """One futures contract on an equity index, such as NIFTY expiring in September."""

    def __init__(
        self,
        exchange: str,
        underlying_symbol: str,
        expiry_date: datetime.date | str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the contract up in UBI's equity index futures segment and keeps its details.

        Args:
            exchange: The str exchange the contract trades on, such as `nse`.
            underlying_symbol: The str symbol of the index the contract is written on, such as `NIFTY`.
            expiry_date: The day the contract expires, as a datetime.date or a `YYYY-MM-DD` str.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            EquityIndexFuturesError: UBI has no such contract, or the instrument it returned is not in the equity index futures segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=EQUITY_INDEX_FUTURES_SEGMENT,
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.EquityIndexFuturesError(
                f"UBI has no {exchange} equity index futures contract on {underlying_symbol} expiring {expiry_date}"
            ) from error
        if self.segment != f"{self.exchange}_{EQUITY_INDEX_FUTURES_SEGMENT}":
            raise exceptions.EquityIndexFuturesError(
                f"An instrument outside the {EQUITY_INDEX_FUTURES_SEGMENT} segment is not an EquityIndexFutures: {self!r}"
            )


class EquityIndexOption(instruments.TradeableInstrument):
    """One option on an equity index, such as a NIFTY call at a given strike and expiry."""

    def __init__(
        self,
        exchange: str,
        underlying_symbol: str,
        expiry_date: datetime.date | str,
        strike_price: float,
        option_type: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the option up in UBI's equity index options segment and keeps its details.

        Args:
            exchange: The str exchange the option trades on, such as `nse`.
            underlying_symbol: The str symbol of the index the option is written on, such as `NIFTY`.
            expiry_date: The day the option expires, as a datetime.date or a `YYYY-MM-DD` str.
            strike_price: The float strike price of the option in index points.
            option_type: The str option type, `CE` for a call or `PE` for a put.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            EquityIndexOptionError: UBI has no such option, or the instrument it returned is not in the equity index options segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=EQUITY_INDEX_OPTIONS_SEGMENT,
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date,
                strike_price=strike_price,
                option_type=option_type,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.EquityIndexOptionError(
                f"UBI has no {exchange} equity index option on {underlying_symbol} expiring {expiry_date} at strike {strike_price} {option_type}"
            ) from error
        if self.segment != f"{self.exchange}_{EQUITY_INDEX_OPTIONS_SEGMENT}":
            raise exceptions.EquityIndexOptionError(
                f"An instrument outside the {EQUITY_INDEX_OPTIONS_SEGMENT} segment is not an EquityIndexOption: {self!r}"
            )
