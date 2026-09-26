"""The exchange-traded fund family: funds and investment trusts that trade like shares.

`ExchangeTradedFund` and `InvestmentTrust` each fix one of UBI's segments, so the kind of instrument is the class rather than a segment name passed by hand. Both are named by exchange and symbol, because a fund and a trust have no expiry, strike or option type, and UBI has no futures or options written on either, so this family is two classes rather than the six an asset class with derivatives gets.

Both trade on the `nse` and the `bse` exactly as a share does. They are quoted, they can be ordered with the ordinary market and limit wrappers, and they can be held in the demat account, so both carry the same holdings members `tradingmachine.assets.equities.Equity` does. An order's quantity is a plain count of units, as for a share, rather than the whole number of lots a commodity or currency order needs.

Symbols are readable tickers, such as `NIFTYBEES` for a fund and `EMBASSY` for a trust. A mutual fund is a different thing and lives in `tradingmachine.assets.mutual_funds`, because it is subscribed to at its net asset value rather than traded.

The one difference between the two classes is what UBI stores. A fund's candles are adjusted for splits and bonuses and carry a `price_factor` column, as a share's do. A trust's are not stored at all yet, so `prices` returns None for an `InvestmentTrust` and the analysis methods have nothing to work on there.

Typical usage example:

  fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
  price = fund.last_price
  frame = fund.relative_strength_index(window=14, days=90)
  row = fund.holdings

  trust = funds.InvestmentTrust(exchange="nse", symbol="EMBASSY")
  level = trust.last_price
"""

import pandas as pd

from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments
from tradingmachine.unified_broker_interface import client

HOLDINGS_PATH = "/api/portfolio/holdings"

HOLDINGS_ORDER_PRODUCT = "cnc"

SEARCH_LIMIT = 50

EXCHANGE_TRADED_FUNDS_SEGMENT = "exchange_traded_funds"

INVESTMENT_TRUSTS_SEGMENT = "investment_trusts"


class ExchangeTradedFund(instruments.TradeableInstrument):
    """One exchange-traded fund, such as NIFTYBEES on the nse."""

    def __init__(
        self,
        exchange: str,
        symbol: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the fund up in UBI's exchange traded funds segment and keeps its details.

        Args:
            exchange: The str exchange the fund is listed on, `nse` or `bse`.
            symbol: The str symbol of the fund, such as `NIFTYBEES`.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            ExchangeTradedFundError: UBI has no fund with that symbol on that exchange, or the instrument it returned is not in the exchange traded funds segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=EXCHANGE_TRADED_FUNDS_SEGMENT,
                symbol=symbol,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.ExchangeTradedFundError(
                f"UBI has no {exchange} exchange traded fund for the symbol {symbol}"
            ) from error
        if self.segment != f"{self.exchange}_{EXCHANGE_TRADED_FUNDS_SEGMENT}":
            raise exceptions.ExchangeTradedFundError(
                f"An instrument outside the {EXCHANGE_TRADED_FUNDS_SEGMENT} segment is not an ExchangeTradedFund: {self!r}"
            )

    @property
    def holdings(self) -> dict | None:
        """The long-term holding of this fund, merged across every broker.

        Reading this sends one request to UBI every time, because UBI serves the whole account's holdings and has no endpoint for a single instrument.

        Returns:
            A dict with `instrument_id`, `isin`, `symbol`, `exchange`, `segment`, `quantity`, `average_price`, `invested_value`, `last_price`, `current_value`, `pnl` and `collateral_quantity`, or None when no broker holds this fund.

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
        """What the units held are worth at the moment.

        UBI prices a holding itself, so this reads the figure rather than working it out. It counts every unit held, including any pledged as collateral, because a pledged unit is still owned.

        Returns:
            The float value in rupees of the whole holding, or None when this fund is not held.

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
        """What the units held have made or lost.

        The dict is not shaped like a position's. A holding reports `day_change`, `day_change_percentage` and `unrealized`, while a position reports `realized`, `unrealized` and `total`, so only `unrealized` means the same thing in both.

        Returns:
            A dict with `day_change` and `day_change_percentage` in rupees and per cent since the previous close, and `unrealized` in rupees against what was paid, or None when this fund is not held.

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
        """Buys more of this fund to keep.

        The order is always sent as `cnc`, which is the product that puts units in the demat account. Nothing is read first, because a fund can be bought whether or not it is already held.

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
        """Sells some of the units held, without selling more than are free.

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
            HoldingError: This fund is not held, or the quantity is more than the free units.
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
            HoldingError: This fund is not held, or every unit held is pledged as collateral.
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
        """Reads this fund's holding once, refusing when it is not held.

        Returns:
            The dict holdings row for this fund.

        Raises:
            HoldingError: No broker holds this fund.
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
        """Finds exchange traded funds whose symbol contains a term.

        UBI puts an exact match first, then symbols starting with the term, then symbols containing it, so a partial name such as `NIFTYBEE` finds NIFTYBEES near the top.

        Args:
            exchange: The str exchange to search, `nse` or `bse`.
            term: The str the symbol must contain, matched without regard to case.
            limit: The int most rows to return, which UBI caps at 200.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame with `instrument_id`, `exchange`, `segment`, `shape`, `symbol` and the derivative fields left empty, or None when no fund matches.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._search_catalogue(
            exchange,
            EXCHANGE_TRADED_FUNDS_SEGMENT,
            term,
            limit,
            unified_broker_interface,
        )


class InvestmentTrust(instruments.TradeableInstrument):
    """One listed investment trust, such as the real estate trust EMBASSY on the nse."""

    def __init__(
        self,
        exchange: str,
        symbol: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the trust up in UBI's investment trusts segment and keeps its details.

        UBI stores no candles for a trust, so `prices` returns None and the inherited analysis methods have nothing to work on, although the trust is quoted and traded normally.

        Args:
            exchange: The str exchange the trust is listed on, `nse` or `bse`.
            symbol: The str symbol of the trust, such as `EMBASSY`.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            InvestmentTrustError: UBI has no trust with that symbol on that exchange, or the instrument it returned is not in the investment trusts segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=INVESTMENT_TRUSTS_SEGMENT,
                symbol=symbol,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.InvestmentTrustError(
                f"UBI has no {exchange} investment trust for the symbol {symbol}"
            ) from error
        if self.segment != f"{self.exchange}_{INVESTMENT_TRUSTS_SEGMENT}":
            raise exceptions.InvestmentTrustError(
                f"An instrument outside the {INVESTMENT_TRUSTS_SEGMENT} segment is not an InvestmentTrust: {self!r}"
            )

    @property
    def holdings(self) -> dict | None:
        """The long-term holding of this trust, merged across every broker.

        Reading this sends one request to UBI every time, because UBI serves the whole account's holdings and has no endpoint for a single instrument.

        Returns:
            A dict with `instrument_id`, `isin`, `symbol`, `exchange`, `segment`, `quantity`, `average_price`, `invested_value`, `last_price`, `current_value`, `pnl` and `collateral_quantity`, or None when no broker holds this trust.

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
        """What the units held are worth at the moment.

        UBI prices a holding itself, so this reads the figure rather than working it out. It counts every unit held, including any pledged as collateral, because a pledged unit is still owned.

        Returns:
            The float value in rupees of the whole holding, or None when this trust is not held.

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
        """What the units held have made or lost.

        The dict is not shaped like a position's. A holding reports `day_change`, `day_change_percentage` and `unrealized`, while a position reports `realized`, `unrealized` and `total`, so only `unrealized` means the same thing in both.

        Returns:
            A dict with `day_change` and `day_change_percentage` in rupees and per cent since the previous close, and `unrealized` in rupees against what was paid, or None when this trust is not held.

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
        """Buys more of this trust to keep.

        The order is always sent as `cnc`, which is the product that puts units in the demat account. Nothing is read first, because a trust can be bought whether or not it is already held.

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
        """Sells some of the units held, without selling more than are free.

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
            HoldingError: This trust is not held, or the quantity is more than the free units.
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
            HoldingError: This trust is not held, or every unit held is pledged as collateral.
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
        """Reads this trust's holding once, refusing when it is not held.

        Returns:
            The dict holdings row for this trust.

        Raises:
            HoldingError: No broker holds this trust.
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
        """Finds investment trusts whose symbol contains a term.

        UBI puts an exact match first, then symbols starting with the term, then symbols containing it, so a partial name such as `EMBAS` finds EMBASSY near the top. UBI carries only twenty-seven trusts on each exchange, so a short term may return most of them.

        Args:
            exchange: The str exchange to search, `nse` or `bse`.
            term: The str the symbol must contain, matched without regard to case.
            limit: The int most rows to return, which UBI caps at 200.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame with `instrument_id`, `exchange`, `segment`, `shape`, `symbol` and the derivative fields left empty, or None when no trust matches.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return cls._search_catalogue(
            exchange,
            INVESTMENT_TRUSTS_SEGMENT,
            term,
            limit,
            unified_broker_interface,
        )
