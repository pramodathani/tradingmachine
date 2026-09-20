"""The fixed income family: bonds, rate indices, and the futures and options written on each of them.

Each of the six classes fixes one of UBI's fixed income segments, so the kind of contract is the class rather than a segment name passed by hand, and each constructor asks for exactly the fields that identify one of its own contracts. `FixedIncome` and `FixedIncomeIndex` are named by exchange and symbol, the futures classes by exchange, underlying symbol and expiry date, and the option classes by those three plus a strike price and an option type.

A bond is named by its ISIN rather than by a ticker, such as `IN000126C010`, because a one-off corporate bond or non-convertible debenture has no ticker that reconciles across brokers. The exception is a small set of interest rate underlyings on the nse, named by a rate code such as `633GS2035`, which are the instruments the futures and options are written on. Sovereign gold bonds live in this family too, rather than with commodities.

`FixedIncomeIndex` is built on `instruments.NonTradeableInstrument`, because an index cannot be traded. The other five are built on `instruments.TradeableInstrument`, so they carry the order-book values as well. All six inherit every analysis class through `instruments.Instrument`.

Two limits of UBI's coverage are worth knowing before reaching for these classes, because they are not obvious and they are not faults in this module. No broker that serves quotes carries a cash bond or a rate index, so `quote`, `last_price`, `ohlc` and the order-book values raise `ServiceUnavailableError` for `FixedIncome` and `FixedIncomeIndex`, while the three derivative classes are quoted normally. And UBI stores no candles for any fixed income segment at all, so `prices` returns None everywhere here and the analysis methods have nothing to work on.

A derivative does not hold an object for its underlying, as in `assets.equities`, even though the symbols do match in this family.

Typical usage example:

  bond = fixed_income.FixedIncome(exchange="nse", symbol="IN000126C010")
  row = bond.holdings

  contract = fixed_income.FixedIncomeFutures(
      exchange="nse",
      underlying_symbol="633GS2035",
      expiry_date="2026-09-24",
  )
  price = contract.last_price()

  expiries = fixed_income.FixedIncomeOption.expiries(
      exchange="nse",
      underlying_symbol="633GS2035",
  )
  chain = fixed_income.FixedIncomeOption.chain(
      exchange="nse",
      underlying_symbol="633GS2035",
      expiry_date=expiries[0],
  )
"""

import datetime

import pandas as pd

from assets import exceptions
from assets import instruments
from ubi_client import client

HOLDINGS_PATH = "/api/portfolio/holdings"

HOLDINGS_ORDER_PRODUCT = "cnc"

SEARCH_LIMIT = 50

FIXED_INCOME_SEGMENT = "fixed_income"

FIXED_INCOME_FUTURES_SEGMENT = "fixed_income_futures"

FIXED_INCOME_OPTIONS_SEGMENT = "fixed_income_options"

FIXED_INCOME_INDICES_SEGMENT = "fixed_income_indices"

FIXED_INCOME_INDEX_FUTURES_SEGMENT = "fixed_income_index_futures"

FIXED_INCOME_INDEX_OPTIONS_SEGMENT = "fixed_income_index_options"


class FixedIncome(instruments.TradeableInstrument):
    """One listed fixed income security, such as a government bond or a treasury bill on the nse."""

    def __init__(
        self,
        exchange: str,
        symbol: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the bond up in UBI's fixed income segment and keeps its details.

        Args:
            exchange: The str exchange the bond is listed on, such as `nse`.
            symbol: The str symbol of the bond, which is its ISIN, such as `IN000126C010`, or a rate code such as `633GS2035` for an interest rate underlying.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            FixedIncomeError: UBI has no bond with that symbol on that exchange, or the instrument it returned is not in the fixed income segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=FIXED_INCOME_SEGMENT,
                symbol=symbol,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.FixedIncomeError(
                f"UBI has no {exchange} bond for the symbol {symbol}"
            ) from error
        if self.segment != f"{self.exchange}_{FIXED_INCOME_SEGMENT}":
            raise exceptions.FixedIncomeError(
                f"An instrument outside the {FIXED_INCOME_SEGMENT} segment is not a FixedIncome: {self!r}"
            )

    @property
    def holdings(self) -> dict | None:
        """The long-term holding of this bond, merged across every broker.

        A bond is the only thing in this module that can be held. A derivative is a position rather than a holding, and an index cannot be held at all.

        Reading this sends one request to UBI every time, because UBI serves the whole account's holdings and has no endpoint for a single instrument.

        The row's `symbol` and `isin` hold the same string for a bond, unlike a share, because a bond is named by its ISIN. A bond held only at Groww is not reported at all, because UBI matches a Groww holding by the ticker the broker sends rather than by an ISIN.

        Returns:
            A dict with `instrument_id`, `isin`, `symbol`, `exchange`, `segment`, `quantity`, `average_price`, `invested_value`, `last_price`, `current_value`, `pnl` and `collateral_quantity`, or None when no broker holds this bond.

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
        """What the bonds held are worth at the moment.

        UBI prices a holding itself, so this reads the figure rather than working it out, which is the opposite of `instruments.TradeableInstrument.positions_value`. It counts every unit held, including any pledged as collateral, because a pledged bond is still owned.

        Returns:
            The float value in rupees of the whole holding, or None when this bond is not held.

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
        """What the bonds held have made or lost.

        The dict is not shaped like a position's. A holding reports `day_change`, `day_change_percentage` and `unrealized`, while a position reports `realized`, `unrealized` and `total`, so only `unrealized` means the same thing in both. There is no realised figure, because selling a bond removes it from the holding rather than booking a profit against it.

        Returns:
            A dict with `day_change` and `day_change_percentage` in rupees and per cent since the previous close, and `unrealized` in rupees against what was paid, or None when this bond is not held.

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
        """Buys more of this bond to keep.

        The order is always sent as `cnc`, which is the product that puts a holding in the demat account. Nothing is read first, because a bond can be bought whether or not it is already held, and UBI checks funds no more than a broker's order endpoint does.

        Args:
            quantity: The int number of units to buy.
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
        """Sells some of the bonds held, without selling more than are free.

        Units pledged as collateral cannot be sold until they are released at the broker, so the quantity asked for is measured against the free units rather than the whole holding.

        Args:
            quantity: The int number of units to sell.
            price: The float limit price in rupees, or None to send a market order.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            HoldingError: This bond is not held, or the quantity is more than the free units.
            UnifiedBrokerInterfaceError: Any failure reported by, or on the way to, UBI.
        """
        row = self._held_row()
        free_quantity = self._free_quantity(row)
        if quantity > free_quantity:
            raise exceptions.HoldingError(
                f"{free_quantity} of the {int(row['quantity'])} {self.symbol} units held are free to sell, because {int(row['collateral_quantity'])} are pledged as collateral, so {quantity} cannot be sold"
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
        """Sells every unit held that is free to sell.

        Units pledged as collateral are left alone, because they cannot be sold until they are released at the broker, so this empties the holding only when nothing is pledged.

        Args:
            price: The float limit price in rupees, or None to send a market order.
            validity: The str validity, `day` or `ioc`, or None to let UBI use `day`.
            after_market: A bool that is True to send the order as an after-market order.
            tag: A str of up to twenty letters and digits to label the order with, or None.

        Returns:
            The dict `place_order` returns, holding `broker`, `order_id`, `outcome` and the rest.

        Raises:
            HoldingError: This bond is not held, or every unit held is pledged as collateral.
            UnifiedBrokerInterfaceError: Any failure reported by, or on the way to, UBI.
        """
        row = self._held_row()
        free_quantity = self._free_quantity(row)
        if free_quantity <= 0:
            raise exceptions.HoldingError(
                f"All {int(row['quantity'])} {self.symbol} units held are pledged as collateral, so none can be sold"
            )
        return self._sell_from_holdings(
            quantity=free_quantity,
            price=price,
            validity=validity,
            after_market=after_market,
            tag=tag,
        )

    def _held_row(self) -> dict:
        """Reads this bond's holding once, refusing when it is not held.

        Returns:
            The dict holdings row for this bond.

        Raises:
            HoldingError: No broker holds this bond.
            UnifiedBrokerInterfaceError: Any failure reported by, or on the way to, UBI.
        """
        row = self.holdings
        if row is None:
            raise exceptions.HoldingError(
                f"No {self.symbol} units are held, so there is nothing to sell: {self!r}"
            )
        return row

    @staticmethod
    def _free_quantity(row: dict) -> int:
        """Works out how many of the units held can be sold.

        Args:
            row: The dict holdings row, with `quantity` and `collateral_quantity`.

        Returns:
            The int number of units that are not pledged as collateral.

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
            quantity: The int number of units to sell.
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
        """Finds listed bonds whose symbol contains a term.

        UBI puts an exact match first, then symbols starting with the term, then symbols containing it. Because a bond is named by its ISIN, a useful term is an ISIN or the start of one, such as `IN0001`; a rate underlying is found by its rate code, such as `GS2035`.

        Args:
            exchange: The str exchange to search, such as `nse`.
            term: The str the symbol must contain, matched without regard to case.
            limit: The int most rows to return, which UBI caps at 200.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame with `instrument_id`, `exchange`, `segment`, `shape`, `symbol` and the derivative fields left empty, or None when no bond matches.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._search_catalogue(
            exchange,
            FIXED_INCOME_SEGMENT,
            term,
            limit,
            unified_broker_interface,
        )


class FixedIncomeFutures(instruments.TradeableInstrument):
    """One futures contract on a bond, such as 633GS2035 expiring in September."""

    def __init__(
        self,
        exchange: str,
        underlying_symbol: str,
        expiry_date: datetime.date | str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the contract up in UBI's fixed income futures segment and keeps its details.

        Args:
            exchange: The str exchange the contract trades on, such as `nse`.
            underlying_symbol: The str rate code of the bond the contract is written on, such as `633GS2035`.
            expiry_date: The day the contract expires, as a datetime.date or a `YYYY-MM-DD` str.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            FixedIncomeFuturesError: UBI has no such contract, or the instrument it returned is not in the fixed income futures segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=FIXED_INCOME_FUTURES_SEGMENT,
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.FixedIncomeFuturesError(
                f"UBI has no {exchange} bond futures contract on {underlying_symbol} expiring {expiry_date}"
            ) from error
        if self.segment != f"{self.exchange}_{FIXED_INCOME_FUTURES_SEGMENT}":
            raise exceptions.FixedIncomeFuturesError(
                f"An instrument outside the {FIXED_INCOME_FUTURES_SEGMENT} segment is not a FixedIncomeFutures: {self!r}"
            )

    @classmethod
    def expiries(
        cls,
        exchange: str,
        underlying_symbol: str,
        include_expired: bool = False,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> list[datetime.date]:
        """Lists the expiries a bond's futures contracts are listed for.

        A contract expiring today counts as live, because it can still be traded until the market closes.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str rate code of the bond, such as `633GS2035`.
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
            FIXED_INCOME_FUTURES_SEGMENT,
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
        """Lists the futures contracts on bonds that are listed.

        The rows are identities rather than objects, because building an object looks each contract up in UBI and a long list would mean a request for every row. Build the ones you want from the rows.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str rate code of the bond to keep, such as `633GS2035`, or None to list every underlying.
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
            FIXED_INCOME_FUTURES_SEGMENT,
            underlying_symbol,
            None,
            include_expired,
            unified_broker_interface,
        )


class FixedIncomeOption(instruments.TradeableInstrument):
    """One option on a bond, such as a 633GS2035 call at a given strike and expiry."""

    def __init__(
        self,
        exchange: str,
        underlying_symbol: str,
        expiry_date: datetime.date | str,
        strike_price: float,
        option_type: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the option up in UBI's fixed income options segment and keeps its details.

        Args:
            exchange: The str exchange the option trades on, such as `nse`.
            underlying_symbol: The str rate code of the bond the option is written on, such as `633GS2035`.
            expiry_date: The day the option expires, as a datetime.date or a `YYYY-MM-DD` str.
            strike_price: The float strike price of the option, quoted as a bond price rather than in rupees.
            option_type: The str option type, `CE` for a call or `PE` for a put.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            FixedIncomeOptionError: UBI has no such option, or the instrument it returned is not in the fixed income options segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=FIXED_INCOME_OPTIONS_SEGMENT,
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date,
                strike_price=strike_price,
                option_type=option_type,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.FixedIncomeOptionError(
                f"UBI has no {exchange} bond option on {underlying_symbol} expiring {expiry_date} at strike {strike_price} {option_type}"
            ) from error
        if self.segment != f"{self.exchange}_{FIXED_INCOME_OPTIONS_SEGMENT}":
            raise exceptions.FixedIncomeOptionError(
                f"An instrument outside the {FIXED_INCOME_OPTIONS_SEGMENT} segment is not a FixedIncomeOption: {self!r}"
            )

    @classmethod
    def expiries(
        cls,
        exchange: str,
        underlying_symbol: str,
        include_expired: bool = False,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> list[datetime.date]:
        """Lists the expiries a bond's options are listed for.

        A contract expiring today counts as live, because it can still be traded until the market closes.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str rate code of the bond, such as `633GS2035`.
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
            FIXED_INCOME_OPTIONS_SEGMENT,
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
        """Lists the strike prices listed on one bond for one expiry.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str rate code of the bond, such as `633GS2035`.
            expiry_date: The expiry to list, as a datetime.date or a `YYYY-MM-DD` str.
            include_expired: A bool that is True to allow an expiry that has already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of float strike prices quoted as bond prices, lowest first, which is empty when nothing is listed for that expiry.

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
        """Lists every option listed on one bond for one expiry.

        The rows are identities rather than objects, because building an object looks each contract up in UBI and a chain of hundreds of contracts would mean hundreds of requests. Build the few you want from the rows.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str rate code of the bond, such as `633GS2035`.
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
            FIXED_INCOME_OPTIONS_SEGMENT,
            underlying_symbol,
            expiry_date,
            include_expired,
            unified_broker_interface,
        )


class FixedIncomeIndex(instruments.NonTradeableInstrument):
    """One fixed income index, such as ONMIBOR on the nse, which is followed rather than traded."""

    def __init__(
        self,
        exchange: str,
        symbol: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the index up in UBI's fixed income indices segment and keeps its details.

        Args:
            exchange: The str exchange that publishes the index, such as `nse`.
            symbol: The str symbol of the index, such as `ONMIBOR` or `10YGS7`.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            FixedIncomeIndexError: UBI has no index with that symbol on that exchange, or the instrument it returned is not in the fixed income indices segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=FIXED_INCOME_INDICES_SEGMENT,
                symbol=symbol,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.FixedIncomeIndexError(
                f"UBI has no {exchange} fixed income index for the symbol {symbol}"
            ) from error
        if self.segment != f"{self.exchange}_{FIXED_INCOME_INDICES_SEGMENT}":
            raise exceptions.FixedIncomeIndexError(
                f"An instrument outside the {FIXED_INCOME_INDICES_SEGMENT} segment is not a FixedIncomeIndex: {self!r}"
            )

    @classmethod
    def search(
        cls,
        exchange: str,
        term: str,
        limit: int = SEARCH_LIMIT,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> pd.DataFrame | None:
        """Finds fixed income indices whose symbol contains a term.

        UBI puts an exact match first, then symbols starting with the term, then symbols containing it, so a partial name such as `MIBOR` finds ONMIBOR near the top. UBI carries very few of these indices, so an empty term-like search may still return everything there is.

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
            FIXED_INCOME_INDICES_SEGMENT,
            term,
            limit,
            unified_broker_interface,
        )


class FixedIncomeIndexFutures(instruments.TradeableInstrument):
    """One futures contract on a fixed income index, such as ONMIBOR expiring in September."""

    def __init__(
        self,
        exchange: str,
        underlying_symbol: str,
        expiry_date: datetime.date | str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the contract up in UBI's fixed income index futures segment and keeps its details.

        Args:
            exchange: The str exchange the contract trades on, such as `nse`.
            underlying_symbol: The str symbol of the index the contract is written on, such as `ONMIBOR`.
            expiry_date: The day the contract expires, as a datetime.date or a `YYYY-MM-DD` str.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            FixedIncomeIndexFuturesError: UBI has no such contract, or the instrument it returned is not in the fixed income index futures segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=FIXED_INCOME_INDEX_FUTURES_SEGMENT,
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.FixedIncomeIndexFuturesError(
                f"UBI has no {exchange} fixed income index futures contract on {underlying_symbol} expiring {expiry_date}"
            ) from error
        if self.segment != f"{self.exchange}_{FIXED_INCOME_INDEX_FUTURES_SEGMENT}":
            raise exceptions.FixedIncomeIndexFuturesError(
                f"An instrument outside the {FIXED_INCOME_INDEX_FUTURES_SEGMENT} segment is not a FixedIncomeIndexFutures: {self!r}"
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
            underlying_symbol: The str symbol of the index, such as `ONMIBOR`.
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
            FIXED_INCOME_INDEX_FUTURES_SEGMENT,
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
        """Lists the futures contracts on fixed income indices that are listed.

        The rows are identities rather than objects, because building an object looks each contract up in UBI and a long list would mean a request for every row. Build the ones you want from the rows.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the index to keep, such as `ONMIBOR`, or None to list every underlying.
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
            FIXED_INCOME_INDEX_FUTURES_SEGMENT,
            underlying_symbol,
            None,
            include_expired,
            unified_broker_interface,
        )


class FixedIncomeIndexOption(instruments.TradeableInstrument):
    """One option on a fixed income index, which UBI carries none of yet."""

    def __init__(
        self,
        exchange: str,
        underlying_symbol: str,
        expiry_date: datetime.date | str,
        strike_price: float,
        option_type: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the option up in UBI's fixed income index options segment and keeps its details.

        No broker UBI maps lists an option on a fixed income index, so this segment is empty and every lookup raises FixedIncomeIndexOptionError today. The class exists so that the family is complete and so that these contracts work the moment UBI gains a mapping for them.

        Args:
            exchange: The str exchange the option trades on, such as `nse`.
            underlying_symbol: The str symbol of the index the option is written on, such as `ONMIBOR`.
            expiry_date: The day the option expires, as a datetime.date or a `YYYY-MM-DD` str.
            strike_price: The float strike price of the option, quoted in the index's own units.
            option_type: The str option type, `CE` for a call or `PE` for a put.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            FixedIncomeIndexOptionError: UBI has no such option, which is true of every option today, or the instrument it returned is not in the fixed income index options segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=FIXED_INCOME_INDEX_OPTIONS_SEGMENT,
                underlying_symbol=underlying_symbol,
                expiry_date=expiry_date,
                strike_price=strike_price,
                option_type=option_type,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.FixedIncomeIndexOptionError(
                f"UBI has no {exchange} fixed income index option on {underlying_symbol} expiring {expiry_date} at strike {strike_price} {option_type}"
            ) from error
        if self.segment != f"{self.exchange}_{FIXED_INCOME_INDEX_OPTIONS_SEGMENT}":
            raise exceptions.FixedIncomeIndexOptionError(
                f"An instrument outside the {FIXED_INCOME_INDEX_OPTIONS_SEGMENT} segment is not a FixedIncomeIndexOption: {self!r}"
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
            underlying_symbol: The str symbol of the index, such as `ONMIBOR`.
            include_expired: A bool that is True to include expiries that have already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of datetime.date, soonest first, which is empty while UBI carries no option on a fixed income index.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._expiry_dates(
            exchange,
            FIXED_INCOME_INDEX_OPTIONS_SEGMENT,
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
        """Lists the strike prices listed on one index for one expiry, which is nothing today.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the index, such as `ONMIBOR`.
            expiry_date: The expiry to list, as a datetime.date or a `YYYY-MM-DD` str.
            include_expired: A bool that is True to allow an expiry that has already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A list of float strike prices in the index's own units, lowest first, which is empty while UBI carries no option on a fixed income index.

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
        """Lists every option listed on one fixed income index for one expiry, which is none today.

        The rows are identities rather than objects, because building an object looks each contract up in UBI and a long chain would mean a request for every row. Build the few you want from the rows.

        Args:
            exchange: The str exchange, such as `nse`.
            underlying_symbol: The str symbol of the index, such as `ONMIBOR`.
            expiry_date: The expiry to list, as a datetime.date or a `YYYY-MM-DD` str.
            include_expired: A bool that is True to allow an expiry that has already passed.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame with `instrument_id`, `exchange`, `segment`, `shape`, `underlying_symbol`, `expiry_date`, `strike_price` and `option_type`, or None, which is what it returns while UBI carries no option on a fixed income index.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            ValueError: expiry_date is a str that is not a valid ISO date.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._contracts_for(
            exchange,
            FIXED_INCOME_INDEX_OPTIONS_SEGMENT,
            underlying_symbol,
            expiry_date,
            include_expired,
            unified_broker_interface,
        )
