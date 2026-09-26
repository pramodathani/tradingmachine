"""The equity family: shares, indices, and the futures and options written on each of them.

Each of the six classes fixes one of UBI's equity segments, so the kind of contract is the class rather than a segment name passed by hand, and each constructor asks for exactly the fields that identify one of its own contracts. `Equity` and `EquityIndex` are named by exchange and symbol, the futures classes by exchange, underlying symbol and expiry date, and the option classes by those three plus a strike price and an option type.

`EquityIndex` is built on `instruments.NonTradeableInstrument`, because an index cannot be traded. The other five are built on `instruments.TradeableInstrument`, so they carry the order-book values as well. All six inherit every analysis class through `instruments.Instrument`.

A derivative does not hold an object for its underlying. UBI links the two only by the underlying symbol matching a share's or an index's own symbol, with no key joining them, and that match is not guaranteed for every index, so the caller builds the underlying itself when it wants one.

Typical usage example:

  share = equities.Equity(exchange="nse", symbol="RELIANCE")
  frame = share.relative_strength_index(window=14, days=365)

  nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")
  level = nifty.last_price

  option = equities.EquityIndexOption(
      exchange="nse",
      underlying_symbol="NIFTY",
      expiry_date="2026-09-29",
      strike_price=25000,
      option_type="CE",
  )
  premium = option.last_price
"""

import datetime

import pandas as pd

from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments
from tradingmachine.unified_broker_interface import client

HOLDINGS_PATH = "/api/portfolio/holdings"

HOLDINGS_ORDER_PRODUCT = "cnc"

SEARCH_LIMIT = 50

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

    @property
    def holdings_value(self) -> float | None:
        """What the shares held are worth at the moment.

        UBI prices a holding itself, so this reads the figure rather than working it out, which is the opposite of `instruments.TradeableInstrument.positions_value`. It counts every share held, including any pledged as collateral, because a pledged share is still owned.

        Returns:
            The float value in rupees of the whole holding, or None when this share is not held.

        Raises:
            ServiceUnavailableError: UBI's holdings document is missing or too old to serve.
            BrokerError: No broker's holdings could be read.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        row = self.holdings
        if row is None:
            return None
        return row["current_value"]

    @property
    def holdings_pnl(self) -> dict | None:
        """What the shares held have made or lost.

        The dict is not shaped like a position's. A holding reports `day_change`, `day_change_percentage` and `unrealized`, while a position reports `realized`, `unrealized` and `total`, so only `unrealized` means the same thing in both. There is no realised figure, because selling a share removes it from the holding rather than booking a profit against it.

        Returns:
            A dict with `day_change` and `day_change_percentage` in rupees and per cent since the previous close, and `unrealized` in rupees against what was paid, or None when this share is not held.

        Raises:
            ServiceUnavailableError: UBI's holdings document is missing or too old to serve.
            BrokerError: No broker's holdings could be read.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        row = self.holdings
        if row is None:
            return None
        return row["pnl"]

    def add_to_holdings(
        self,
        quantity: int,
        price: float | None = None,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Buys more of this share to keep.

        The order is always sent as `cnc`, which is the product that puts shares in the demat account. Nothing is read first, because a share can be bought whether or not it is already held, and UBI checks funds no more than a broker's order endpoint does.

        Args:
            quantity: The int number of shares to buy.
            price: The float limit price in rupees, or None to send a market order.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            UnifiedBrokerInterfaceError: Any failure reported by, or on the way to, UBI.
        """
        if price is None:
            return self.buy_at_market_price(
                quantity=quantity,
                product=HOLDINGS_ORDER_PRODUCT,
                validity=validity,
                after_market=after_market,
                tag=tag,
            )
        return self.buy_at_limit_price(
            price=price,
            quantity=quantity,
            product=HOLDINGS_ORDER_PRODUCT,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def reduce_holdings(
        self,
        quantity: int,
        price: float | None = None,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Sells some of the shares held, without selling more than are free.

        Shares pledged as collateral cannot be sold until they are released at the broker, so the quantity asked for is measured against the free shares rather than the whole holding.

        Args:
            quantity: The int number of shares to sell.
            price: The float limit price in rupees, or None to send a market order.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            HoldingError: This share is not held, or the quantity is more than the free shares.
            UnifiedBrokerInterfaceError: Any failure reported by, or on the way to, UBI.
        """
        row = self._held_row()
        free_quantity = self._free_quantity(row)
        if quantity > free_quantity:
            raise exceptions.HoldingError(
                f"{free_quantity} of the {int(row['quantity'])} {self.symbol} shares held are free to sell, because {int(row['collateral_quantity'])} are pledged as collateral, so {quantity} cannot be sold"
            )
        return self._sell_from_holdings(
            quantity=quantity,
            price=price,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def liquidate_holdings(
        self,
        price: float | None = None,
        validity: str | None = None,
        after_market: bool = False,
        tag: str | None = None,
    ) -> dict:
        """Sells every share held that is free to sell.

        Shares pledged as collateral are left alone, because they cannot be sold until they are released at the broker, so this empties the holding only when nothing is pledged.

        Args:
            price: The float limit price in rupees, or None to send a market order.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            HoldingError: This share is not held, or every share held is pledged as collateral.
            UnifiedBrokerInterfaceError: Any failure reported by, or on the way to, UBI.
        """
        row = self._held_row()
        free_quantity = self._free_quantity(row)
        if free_quantity <= 0:
            raise exceptions.HoldingError(
                f"All {int(row['quantity'])} {self.symbol} shares held are pledged as collateral, so none can be sold"
            )
        return self._sell_from_holdings(
            quantity=free_quantity,
            price=price,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def _held_row(self) -> dict:
        """Reads this share's holding once, refusing when it is not held.

        Returns:
            The dict holdings row for this share.

        Raises:
            HoldingError: No broker holds this share.
            UnifiedBrokerInterfaceError: Any failure reported by, or on the way to, UBI.
        """
        row = self.holdings
        if row is None:
            raise exceptions.HoldingError(
                f"No {self.symbol} shares are held, so there is nothing to sell: {self!r}"
            )
        return row

    @staticmethod
    def _free_quantity(row: dict) -> int:
        """Works out how many of the shares held can be sold.

        Args:
            row: The dict holdings row, with `quantity` and `collateral_quantity`.

        Returns:
            The int number of shares that are not pledged as collateral.

        Raises:
            Nothing.
        """
        return int(row["quantity"] - row["collateral_quantity"])

    def _sell_from_holdings(
        self,
        quantity: int,
        price: float | None,
        validity: str | None,
        after_market: bool,
        tag: str | None,
    ) -> dict:
        """Sends the sell order that reduces the holding.

        Args:
            quantity: The int number of shares to sell.
            price: The float limit price in rupees, or None to send a market order.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns.

        Raises:
            UnifiedBrokerInterfaceError: Any failure reported by, or on the way to, UBI.
        """
        if price is None:
            return self.sell_at_market_price(
                quantity=quantity,
                product=HOLDINGS_ORDER_PRODUCT,
                validity=validity,
                after_market=after_market,
                tag=tag,
            )
        return self.sell_at_limit_price(
            price=price,
            quantity=quantity,
            product=HOLDINGS_ORDER_PRODUCT,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    @classmethod
    def search(
        cls,
        exchange: str,
        term: str,
        limit: int = SEARCH_LIMIT,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> pd.DataFrame | None:
        """Finds listed shares whose symbol contains a term.

        UBI puts an exact match first, then symbols starting with the term, then symbols containing it, so a partial name such as `RELI` finds RELIANCE near the top.

        Args:
            exchange: The str exchange to search, such as `nse`.
            term: The str the symbol must contain, matched without regard to case.
            limit: The int most rows to return, which UBI caps at 200.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame with `instrument_id`, `exchange`, `segment`, `shape`, `symbol` and the derivative fields left empty, or None when no share matches.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._search_catalogue(
            exchange,
            EQUITY_SEGMENT,
            term,
            limit,
            unified_broker_interface,
        )


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

    @classmethod
    def expiries(
        cls,
        exchange: str,
        underlying_symbol: str,
        include_expired: bool = False,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> list[datetime.date]:
        """Lists the expiries a share's futures contracts are listed for.

        A contract expiring today counts as live, because it can still be traded until the market closes.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the share, such as `RELIANCE`.
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
            EQUITY_FUTURES_SEGMENT,
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
        """Lists the futures contracts on shares that are listed.

        The rows are identities rather than objects, because building an object looks each contract up in UBI and a long list would mean a request for every row. Build the ones you want from the rows.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the share to keep, such as `RELIANCE`, or None to list every underlying.
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
            EQUITY_FUTURES_SEGMENT,
            underlying_symbol,
            None,
            include_expired,
            unified_broker_interface,
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

    @classmethod
    def expiries(
        cls,
        exchange: str,
        underlying_symbol: str,
        include_expired: bool = False,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> list[datetime.date]:
        """Lists the expiries a share's options are listed for.

        A contract expiring today counts as live, because it can still be traded until the market closes.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the share, such as `RELIANCE`.
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
            EQUITY_OPTIONS_SEGMENT,
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
        """Lists the strike prices listed on one share for one expiry.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the share, such as `RELIANCE`.
            expiry_date: The expiry to list, as a datetime.date or a `YYYY-MM-DD` str.
            include_expired: A bool that is True to allow an expiry that has already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of float strike prices in rupees, lowest first, which is empty when nothing is listed for that expiry.

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
        """Lists every option listed on one share for one expiry.

        The rows are identities rather than objects, because building an object looks each contract up in UBI and a chain of two hundred contracts would mean two hundred requests. Build the few you want from the rows.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the share, such as `RELIANCE`.
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
            EQUITY_OPTIONS_SEGMENT,
            underlying_symbol,
            expiry_date,
            include_expired,
            unified_broker_interface,
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

    @classmethod
    def search(
        cls,
        exchange: str,
        term: str,
        limit: int = SEARCH_LIMIT,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> pd.DataFrame | None:
        """Finds equity indices whose symbol contains a term.

        UBI puts an exact match first, then symbols starting with the term, then symbols containing it, so a partial name such as `BANK` finds BANKNIFTY near the top.

        Args:
            exchange: The str exchange to search, such as `nse`.
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
            EQUITY_INDICES_SEGMENT,
            term,
            limit,
            unified_broker_interface,
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
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the index, such as `NIFTY`.
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
            EQUITY_INDEX_FUTURES_SEGMENT,
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
        """Lists the futures contracts on indices that are listed.

        The rows are identities rather than objects, because building an object looks each contract up in UBI and a long list would mean a request for every row. Build the ones you want from the rows.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the index to keep, such as `NIFTY`, or None to list every underlying.
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
            EQUITY_INDEX_FUTURES_SEGMENT,
            underlying_symbol,
            None,
            include_expired,
            unified_broker_interface,
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
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the index, such as `NIFTY`.
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
            EQUITY_INDEX_OPTIONS_SEGMENT,
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
        """Lists the strike prices listed on one index for one expiry.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the index, such as `NIFTY`.
            expiry_date: The expiry to list, as a datetime.date or a `YYYY-MM-DD` str.
            include_expired: A bool that is True to allow an expiry that has already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of float strike prices in index points, lowest first, which is empty when nothing is listed for that expiry.

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
        """Lists every index option listed on one index for one expiry.

        The rows are identities rather than objects, because building an object looks each contract up in UBI and a chain of two hundred contracts would mean two hundred requests. Build the few you want from the rows.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the index, such as `NIFTY`.
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
            EQUITY_INDEX_OPTIONS_SEGMENT,
            underlying_symbol,
            expiry_date,
            include_expired,
            unified_broker_interface,
        )
