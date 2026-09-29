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

from typing import TYPE_CHECKING

import pandas as pd

from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments
from tradingmachine.unified_broker_interface import client

if TYPE_CHECKING:
    from tradingmachine.asset_baskets import asset_basket

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
    def constituents(self) -> "asset_basket.AssetBasket | None":
        """The stored basket of what the fund holds, a tradingmachine.asset_baskets.exchange_traded_fund_constituents.ExchangeTradedFundConstituents, or None when none is stored for today, read from MongoDB and UBI on every access.

        This is the fund's own portfolio, which is different from `holdings`, the units of the fund this account holds. UBI stores no fund holdings, so a basket exists only when one was saved with this fund as its linked instrument.

        Raises:
            BasketMemberError: UBI could not find one or more of the stored members.
            pymongo.errors.PyMongoError: MongoDB could not be reached.

        Examples:
            Print the stored contents of NIFTYBEES, or None when no basket is stored for it:

            ```python
            from tradingmachine.assets import funds

            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            print(fund.constituents)
            ```

            Store a small two-member basket linked to NIFTYBEES, read it back through the fund, and delete it again:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import basket_store
            from tradingmachine.asset_baskets import exchange_traded_fund_constituents
            from tradingmachine.assets import equities
            from tradingmachine.assets import funds

            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            members = [
                basket_member.BasketMember(
                    instrument=equities.Equity(exchange="nse", symbol="RELIANCE"),
                    weight=0.6,
                ),
                basket_member.BasketMember(
                    instrument=equities.Equity(exchange="nse", symbol="HDFCBANK"),
                    weight=0.4,
                ),
            ]
            basket = exchange_traded_fund_constituents.ExchangeTradedFundConstituents(
                name="EXAMPLE_NIFTYBEES_CONTENTS",
                members=members,
                fund=fund,
            )
            store = basket_store.BasketStore()
            saved = store.save(basket)
            try:
                contents = fund.constituents
                print(contents)
                print(contents.weights)
            finally:
                store.delete("EXAMPLE_NIFTYBEES_CONTENTS", saved["effective_date"])
            ```
        """
        from tradingmachine.asset_baskets import basket_store

        store = basket_store.BasketStore(
            unified_broker_interface=self._unified_broker_interface,
        )
        return store.load_for_instrument(self)

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

        Examples:
            Print this account's holding of NIFTYBEES, or None when no broker holds it:

            ```python
            from tradingmachine.assets import funds

            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            print(fund.holdings)
            ```

            Report how many units are held and what they cost on average:

            ```python
            from tradingmachine.assets import funds

            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            row = fund.holdings
            if row is None:
                print("No NIFTYBEES units are held.")
            else:
                print(f"{row['quantity']} units at an average of {row['average_price']}")
            ```

            Work out how many units of GOLDBEES are free to sell, which excludes any pledged as collateral:

            ```python
            from tradingmachine.assets import funds

            fund = funds.ExchangeTradedFund(exchange="nse", symbol="GOLDBEES")
            row = fund.holdings
            if row is None:
                print("No GOLDBEES units are held, so none are free to sell.")
            else:
                free_quantity = row["quantity"] - row["collateral_quantity"]
                print(f"{free_quantity} of {row['quantity']} units are free to sell")
            ```
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

        Examples:
            Print what the NIFTYBEES units held are worth, or None when none are held:

            ```python
            from tradingmachine.assets import funds

            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            print(fund.holdings_value)
            ```

            Compare the holding's value today with what was paid for it:

            ```python
            from tradingmachine.assets import funds

            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            row = fund.holdings
            if row is None:
                print("No NIFTYBEES units are held.")
            else:
                value = fund.holdings_value
                print(f"Worth {value:.2f} against {row['invested_value']:.2f} paid")
            ```

            Add up the value held across three funds, counting one that is not held as nothing:

            ```python
            from tradingmachine.assets import funds

            total_value = 0.0
            for symbol in [
                "NIFTYBEES",
                "GOLDBEES",
                "BANKBEES",
            ]:
                fund = funds.ExchangeTradedFund(exchange="nse", symbol=symbol)
                value = fund.holdings_value
                if value is None:
                    print(f"{symbol}: not held")
                else:
                    print(f"{symbol}: {value:.2f}")
                    total_value += value
            print(f"Total: {total_value:.2f}")
            ```
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

        Examples:
            Print what the NIFTYBEES units held have made or lost, or None when none are held:

            ```python
            from tradingmachine.assets import funds

            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            print(fund.holdings_pnl)
            ```

            Print the holding's move since the previous close in per cent:

            ```python
            from tradingmachine.assets import funds

            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            pnl = fund.holdings_pnl
            if pnl is None:
                print("No NIFTYBEES units are held.")
            else:
                print(f"Today: {pnl['day_change_percentage']:.2f} per cent")
            ```

            List the unrealised profit or loss of each of three funds:

            ```python
            from tradingmachine.assets import funds

            for symbol in [
                "NIFTYBEES",
                "GOLDBEES",
                "BANKBEES",
            ]:
                fund = funds.ExchangeTradedFund(exchange="nse", symbol=symbol)
                pnl = fund.holdings_pnl
                if pnl is None:
                    print(f"{symbol}: not held")
                else:
                    print(f"{symbol}: {pnl['unrealized']:.2f} unrealised")
            ```
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

        Examples:
            Bid for one unit of NIFTYBEES at a limit 3 per cent below the last price, which the order engine holds, and cancel it at once:

            ```python
            from tradingmachine.assets import funds

            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            limit_price = round(fund.last_price * 0.97, 2)
            answer = fund.add_to_holdings(quantity=1, price=limit_price)
            try:
                print(answer)
            finally:
                print(fund.cancel_parent(answer["parent_id"]))
            ```

            Bid for one unit of GOLDBEES with a tag, find the held order among the fund's parents, and cancel it:

            ```python
            from tradingmachine.assets import funds

            fund = funds.ExchangeTradedFund(exchange="nse", symbol="GOLDBEES")
            limit_price = round(fund.last_price * 0.97, 2)
            answer = fund.add_to_holdings(
                quantity=1,
                price=limit_price,
                tag="examplebid",
            )
            try:
                parents = fund.parents
                print(parents[["parent_order_id", "synthetic_type", "state"]])
            finally:
                print(fund.cancel_parent(answer["parent_id"]))
            ```
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

        Examples:
            Offer one held unit of NIFTYBEES at a limit 3 per cent above the last price, and cancel the held order at once:

            ```python
            from tradingmachine.assets import funds

            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            if fund.holdings is None:
                print("No NIFTYBEES units are held, so there is nothing to reduce.")
            else:
                limit_price = round(fund.last_price * 1.03, 2)
                answer = fund.reduce_holdings(quantity=1, price=limit_price)
                try:
                    print(answer)
                finally:
                    print(fund.cancel_parent(answer["parent_id"]))
            ```

            Ask to sell far more units than are free, and handle the refusal, which comes before any order is sent:

            ```python
            from tradingmachine.assets import exceptions
            from tradingmachine.assets import funds

            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            limit_price = round(fund.last_price * 1.03, 2)
            try:
                fund.reduce_holdings(quantity=10000000, price=limit_price)
            except exceptions.HoldingError as error:
                print(f"Refused: {error}")
            ```
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

        Examples:
            Offer every free unit of NIFTYBEES at a limit 3 per cent above the last price, and cancel the held order at once:

            ```python
            from tradingmachine.assets import funds

            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            if fund.holdings is None:
                print("No NIFTYBEES units are held, so there is nothing to sell.")
            else:
                limit_price = round(fund.last_price * 1.03, 2)
                answer = fund.liquidate_holdings(price=limit_price)
                try:
                    print(answer)
                finally:
                    print(fund.cancel_parent(answer["parent_id"]))
            ```

            Try to empty a holding of GOLDBEES and handle the refusal when none is held or every unit is pledged:

            ```python
            from tradingmachine.assets import exceptions
            from tradingmachine.assets import funds

            fund = funds.ExchangeTradedFund(exchange="nse", symbol="GOLDBEES")
            limit_price = round(fund.last_price * 1.03, 2)
            try:
                answer = fund.liquidate_holdings(price=limit_price)
            except exceptions.HoldingError as error:
                print(f"Nothing to sell: {error}")
            else:
                try:
                    print(answer)
                finally:
                    print(fund.cancel_parent(answer["parent_id"]))
            ```
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

        Examples:
            Find funds on the nse whose symbol contains `NIFTYBEE`:

            ```python
            from tradingmachine.assets import funds

            matches = funds.ExchangeTradedFund.search(exchange="nse", term="NIFTYBEE")
            print(matches[["symbol", "exchange", "segment"]])
            ```

            List up to ten gold funds on the bse:

            ```python
            from tradingmachine.assets import funds

            matches = funds.ExchangeTradedFund.search(
                exchange="bse",
                term="GOLD",
                limit=10,
            )
            if matches is None:
                print("No gold fund was found on the bse.")
            else:
                print(matches["symbol"].tolist())
            ```

            Build the best match for a partial name and print its last price:

            ```python
            from tradingmachine.assets import funds

            matches = funds.ExchangeTradedFund.search(exchange="nse", term="BANKBEE")
            first_symbol = matches.iloc[0]["symbol"]
            fund = funds.ExchangeTradedFund(exchange="nse", symbol=first_symbol)
            print(f"{fund.symbol}: {fund.last_price}")
            ```
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

        Examples:
            Print this account's holding of EMBASSY, or None when no broker holds it:

            ```python
            from tradingmachine.assets import funds

            trust = funds.InvestmentTrust(exchange="nse", symbol="EMBASSY")
            print(trust.holdings)
            ```

            Report how many units are held and what they cost on average:

            ```python
            from tradingmachine.assets import funds

            trust = funds.InvestmentTrust(exchange="nse", symbol="EMBASSY")
            row = trust.holdings
            if row is None:
                print("No EMBASSY units are held.")
            else:
                print(f"{row['quantity']} units at an average of {row['average_price']}")
            ```

            Work out how many units of PGINVIT are free to sell, which excludes any pledged as collateral:

            ```python
            from tradingmachine.assets import funds

            trust = funds.InvestmentTrust(exchange="nse", symbol="PGINVIT")
            row = trust.holdings
            if row is None:
                print("No PGINVIT units are held, so none are free to sell.")
            else:
                free_quantity = row["quantity"] - row["collateral_quantity"]
                print(f"{free_quantity} of {row['quantity']} units are free to sell")
            ```
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

        Examples:
            Print what the EMBASSY units held are worth, or None when none are held:

            ```python
            from tradingmachine.assets import funds

            trust = funds.InvestmentTrust(exchange="nse", symbol="EMBASSY")
            print(trust.holdings_value)
            ```

            Compare the holding's value today with what was paid for it:

            ```python
            from tradingmachine.assets import funds

            trust = funds.InvestmentTrust(exchange="nse", symbol="EMBASSY")
            row = trust.holdings
            if row is None:
                print("No EMBASSY units are held.")
            else:
                value = trust.holdings_value
                print(f"Worth {value:.2f} against {row['invested_value']:.2f} paid")
            ```

            Add up the value held across three trusts, counting one that is not held as nothing:

            ```python
            from tradingmachine.assets import funds

            total_value = 0.0
            for symbol in [
                "EMBASSY",
                "PGINVIT",
                "IRBINVIT",
            ]:
                trust = funds.InvestmentTrust(exchange="nse", symbol=symbol)
                value = trust.holdings_value
                if value is None:
                    print(f"{symbol}: not held")
                else:
                    print(f"{symbol}: {value:.2f}")
                    total_value += value
            print(f"Total: {total_value:.2f}")
            ```
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

        Examples:
            Print what the EMBASSY units held have made or lost, or None when none are held:

            ```python
            from tradingmachine.assets import funds

            trust = funds.InvestmentTrust(exchange="nse", symbol="EMBASSY")
            print(trust.holdings_pnl)
            ```

            Print the holding's move since the previous close in per cent:

            ```python
            from tradingmachine.assets import funds

            trust = funds.InvestmentTrust(exchange="nse", symbol="EMBASSY")
            pnl = trust.holdings_pnl
            if pnl is None:
                print("No EMBASSY units are held.")
            else:
                print(f"Today: {pnl['day_change_percentage']:.2f} per cent")
            ```

            List the unrealised profit or loss of each of three trusts:

            ```python
            from tradingmachine.assets import funds

            for symbol in [
                "EMBASSY",
                "PGINVIT",
                "IRBINVIT",
            ]:
                trust = funds.InvestmentTrust(exchange="nse", symbol=symbol)
                pnl = trust.holdings_pnl
                if pnl is None:
                    print(f"{symbol}: not held")
                else:
                    print(f"{symbol}: {pnl['unrealized']:.2f} unrealised")
            ```
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

        Examples:
            Bid for one unit of EMBASSY at a limit 3 per cent below the last price, which the order engine holds, and cancel it at once:

            ```python
            from tradingmachine.assets import funds

            trust = funds.InvestmentTrust(exchange="nse", symbol="EMBASSY")
            limit_price = round(trust.last_price * 0.97, 2)
            answer = trust.add_to_holdings(quantity=1, price=limit_price)
            try:
                print(answer)
            finally:
                print(trust.cancel_parent(answer["parent_id"]))
            ```

            Bid for one unit of PGINVIT with a tag, find the held order among the trust's parents, and cancel it:

            ```python
            from tradingmachine.assets import funds

            trust = funds.InvestmentTrust(exchange="nse", symbol="PGINVIT")
            limit_price = round(trust.last_price * 0.97, 2)
            answer = trust.add_to_holdings(
                quantity=1,
                price=limit_price,
                tag="examplebid",
            )
            try:
                parents = trust.parents
                print(parents[["parent_order_id", "synthetic_type", "state"]])
            finally:
                print(trust.cancel_parent(answer["parent_id"]))
            ```
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

        Examples:
            Offer one held unit of EMBASSY at a limit 3 per cent above the last price, and cancel the held order at once:

            ```python
            from tradingmachine.assets import funds

            trust = funds.InvestmentTrust(exchange="nse", symbol="EMBASSY")
            if trust.holdings is None:
                print("No EMBASSY units are held, so there is nothing to reduce.")
            else:
                limit_price = round(trust.last_price * 1.03, 2)
                answer = trust.reduce_holdings(quantity=1, price=limit_price)
                try:
                    print(answer)
                finally:
                    print(trust.cancel_parent(answer["parent_id"]))
            ```

            Ask to sell far more units than are free, and handle the refusal, which comes before any order is sent:

            ```python
            from tradingmachine.assets import exceptions
            from tradingmachine.assets import funds

            trust = funds.InvestmentTrust(exchange="nse", symbol="EMBASSY")
            limit_price = round(trust.last_price * 1.03, 2)
            try:
                trust.reduce_holdings(quantity=10000000, price=limit_price)
            except exceptions.HoldingError as error:
                print(f"Refused: {error}")
            ```
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

        Examples:
            Offer every free unit of EMBASSY at a limit 3 per cent above the last price, and cancel the held order at once:

            ```python
            from tradingmachine.assets import funds

            trust = funds.InvestmentTrust(exchange="nse", symbol="EMBASSY")
            if trust.holdings is None:
                print("No EMBASSY units are held, so there is nothing to sell.")
            else:
                limit_price = round(trust.last_price * 1.03, 2)
                answer = trust.liquidate_holdings(price=limit_price)
                try:
                    print(answer)
                finally:
                    print(trust.cancel_parent(answer["parent_id"]))
            ```

            Try to empty a holding of PGINVIT and handle the refusal when none is held or every unit is pledged:

            ```python
            from tradingmachine.assets import exceptions
            from tradingmachine.assets import funds

            trust = funds.InvestmentTrust(exchange="nse", symbol="PGINVIT")
            limit_price = round(trust.last_price * 1.03, 2)
            try:
                answer = trust.liquidate_holdings(price=limit_price)
            except exceptions.HoldingError as error:
                print(f"Nothing to sell: {error}")
            else:
                try:
                    print(answer)
                finally:
                    print(trust.cancel_parent(answer["parent_id"]))
            ```
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

        Examples:
            Find trusts on the nse whose symbol contains `EMBAS`:

            ```python
            from tradingmachine.assets import funds

            matches = funds.InvestmentTrust.search(exchange="nse", term="EMBAS")
            print(matches[["symbol", "exchange", "segment"]])
            ```

            Count the infrastructure investment trusts on the nse, whose symbols mostly contain `INVIT`:

            ```python
            from tradingmachine.assets import funds

            matches = funds.InvestmentTrust.search(exchange="nse", term="INVIT")
            if matches is None:
                print("No trust matched.")
            else:
                print(f"{len(matches)} trusts: {matches['symbol'].tolist()}")
            ```

            Build the best match for a partial name and print its last price:

            ```python
            from tradingmachine.assets import funds

            matches = funds.InvestmentTrust.search(exchange="nse", term="PGINV")
            first_symbol = matches.iloc[0]["symbol"]
            trust = funds.InvestmentTrust(exchange="nse", symbol=first_symbol)
            print(f"{trust.symbol}: {trust.last_price}")
            ```
        """
        return cls._search_catalogue(
            exchange,
            INVESTMENT_TRUSTS_SEGMENT,
            term,
            limit,
            unified_broker_interface,
        )
