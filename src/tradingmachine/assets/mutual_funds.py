"""Mutual funds, which are held rather than traded.

`MutualFund` fixes UBI's `mutual_funds` segment, so the kind of instrument is the class rather than a segment name passed by hand. A fund is named by exchange and symbol, where the symbol is the scheme's exchange code such as `ABSLFTTIDG`. UBI carries them on the `nse` only, and it has no futures or options written on a mutual fund, so this module is one class.

A mutual fund is unlike everything else in `assets`. It is subscribed to and redeemed at the day's net asset value rather than bought and sold in a continuous market, and UBI has no quote for one: only a single broker carries the segment, and no broker that serves quotes does, so `quote`, `last_price`, `ohlc` and every order-book value raise `ServiceUnavailableError`. UBI stores no candles either, so `prices` returns None and the inherited analysis methods have nothing to work on.

What does work is holding. `mutual_funds` is one of UBI's cash segments, so a fund is reported in the account's holdings exactly as a share is, and `MutualFund` carries the same six holdings members `tradingmachine.assets.equities.Equity` does. The user chose on 2026-09-20 to give it the full surface, including `add_to_holdings`, `reduce_holdings` and `liquidate_holdings`, rather than the read-only version the old project used, so that no class in this family is an exception a caller has to remember.

Those three methods send ordinary `cnc` orders, which is what UBI accepts for this segment. Whether a broker will treat such an order as a subscription is a question for the broker, and the practical obstacle comes first: with no quote there is no price to send a market order against, so a limit price is the only sensible form. Nothing here checks that, in keeping with the rule that orders reach UBI as given.

Typical usage example:

  fund = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")
  row = fund.holdings
  value = fund.holdings_value

  matches = mutual_funds.MutualFund.search(exchange="nse", term="ABSL")
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

MUTUAL_FUNDS_SEGMENT = "mutual_funds"


class MutualFund(instruments.TradeableInstrument):
    """One mutual fund scheme, such as ABSLFTTIDG on the nse."""

    def __init__(
        self,
        exchange: str,
        symbol: str,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Looks the scheme up in UBI's mutual funds segment and keeps its details.

        A mutual fund has no quote, because no broker that serves quotes carries the segment, so `last_price`, `quote`, `ohlc` and the order-book values raise `ServiceUnavailableError`. UBI stores no candles for one either, so `prices` returns None. What works is the holdings members below.

        Args:
            exchange: The str exchange the scheme is listed on, which UBI only has as `nse`.
            symbol: The str exchange code of the scheme, such as `ABSLFTTIDG`.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share one client among all instruments.

        Raises:
            MutualFundError: UBI has no scheme with that symbol on that exchange, or the instrument it returned is not in the mutual funds segment.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        try:
            super().__init__(
                exchange=exchange,
                segment=MUTUAL_FUNDS_SEGMENT,
                symbol=symbol,
                unified_broker_interface=unified_broker_interface,
            )
        except exceptions.InstrumentError as error:
            raise exceptions.MutualFundError(
                f"UBI has no {exchange} mutual fund for the symbol {symbol}"
            ) from error
        if self.segment != f"{self.exchange}_{MUTUAL_FUNDS_SEGMENT}":
            raise exceptions.MutualFundError(
                f"An instrument outside the {MUTUAL_FUNDS_SEGMENT} segment is not a MutualFund: {self!r}"
            )

    @property
    def constituents(self) -> "asset_basket.AssetBasket | None":
        """The stored basket of what the scheme holds, a tradingmachine.asset_baskets.mutual_fund_constituents.MutualFundConstituents, or None when none is stored for today, read from MongoDB and UBI on every access.

        This is the scheme's own portfolio, which is different from `holdings`, the units of the scheme this account holds. UBI has no price for a mutual fund, so this is the only way to measure one: the scheme's own `sharpe_ratio` and the other performance methods return None, while the basket's work. UBI stores no fund holdings, so a basket exists only when one was saved with this scheme as its linked instrument.

        Raises:
            BasketMemberError: UBI could not find one or more of the stored members.
            pymongo.errors.PyMongoError: MongoDB could not be reached.

        Examples:
            Print the stored portfolio of the ABSLFTTIDG scheme, or None when no basket is stored for it:

            ```python
            from tradingmachine.assets import mutual_funds

            fund = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")
            print(fund.constituents)
            ```

            Store a small two-member portfolio linked to the scheme, estimate the scheme's move today from it, and delete it again:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import basket_store
            from tradingmachine.asset_baskets import mutual_fund_constituents
            from tradingmachine.assets import equities
            from tradingmachine.assets import mutual_funds

            fund = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")
            members = [
                basket_member.BasketMember(
                    instrument=equities.Equity(exchange="nse", symbol="INFY"),
                    weight=0.5,
                ),
                basket_member.BasketMember(
                    instrument=equities.Equity(exchange="nse", symbol="TCS"),
                    weight=0.5,
                ),
            ]
            basket = mutual_fund_constituents.MutualFundConstituents(
                name="EXAMPLE_ABSLFTTIDG_CONTENTS",
                members=members,
                fund=fund,
            )
            store = basket_store.BasketStore()
            saved = store.save(basket)
            try:
                contents = fund.constituents
                print(contents)
                print(f"Estimated move today: {contents.estimated_day_change_percent}")
            finally:
                store.delete("EXAMPLE_ABSLFTTIDG_CONTENTS", saved["effective_date"])
            ```
        """
        from tradingmachine.asset_baskets import basket_store

        store = basket_store.BasketStore(
            unified_broker_interface=self._unified_broker_interface,
        )
        return store.load_for_instrument(self)

    @property
    def holdings(self) -> dict | None:
        """The holding of this scheme, merged across every broker.

        Reading this sends one request to UBI every time, because UBI serves the whole account's holdings and has no endpoint for a single instrument.

        Returns:
            A dict with `instrument_id`, `isin`, `symbol`, `exchange`, `segment`, `quantity`, `average_price`, `invested_value`, `last_price`, `current_value`, `pnl` and `collateral_quantity`, or None when no broker holds this scheme.

        Raises:
            ServiceUnavailableError: UBI's holdings document is missing or too old to serve.
            BrokerError: No broker's holdings could be read.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.

        Examples:
            Print this account's holding of the ABSLFTTIDG scheme, or None when no broker holds it:

            ```python
            from tradingmachine.assets import mutual_funds

            fund = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")
            print(fund.holdings)
            ```

            Report the units held and the net asset value the broker last reported for them:

            ```python
            from tradingmachine.assets import mutual_funds

            fund = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")
            row = fund.holdings
            if row is None:
                print("No ABSLFTTIDG units are held.")
            else:
                print(f"{row['quantity']} units, last valued at {row['last_price']}")
            ```

            Check which of two plans of the same scheme, growth and dividend, this account holds:

            ```python
            from tradingmachine.assets import mutual_funds

            for symbol in [
                "ABSLFTTIDG",
                "ABSLFTTIDN",
            ]:
                fund = mutual_funds.MutualFund(exchange="nse", symbol=symbol)
                if fund.holdings is None:
                    print(f"{symbol}: not held")
                else:
                    print(f"{symbol}: {fund.holdings['quantity']} units")
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

        UBI prices a holding itself, so this reads the figure rather than working it out. A mutual fund has no quote of its own, so the figure rests on whatever last price the broker reported for the holding.

        Returns:
            The float value in rupees of the whole holding, or None when this scheme is not held.

        Raises:
            ServiceUnavailableError: UBI's holdings document is missing or too old to serve.
            BrokerError: No broker's holdings could be read.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.

        Examples:
            Print what the ABSLFTTIDG units held are worth, or None when none are held:

            ```python
            from tradingmachine.assets import mutual_funds

            fund = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")
            print(fund.holdings_value)
            ```

            Compare the holding's value with what was invested in it:

            ```python
            from tradingmachine.assets import mutual_funds

            fund = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")
            row = fund.holdings
            if row is None:
                print("No ABSLFTTIDG units are held.")
            else:
                value = fund.holdings_value
                print(f"Worth {value:.2f} against {row['invested_value']:.2f} invested")
            ```

            Add up the value held across three schemes, counting one that is not held as nothing:

            ```python
            from tradingmachine.assets import mutual_funds

            total_value = 0.0
            for symbol in [
                "ABSLFTTIDG",
                "ABSLFTTIDN",
                "ABSLFTTIRG",
            ]:
                fund = mutual_funds.MutualFund(exchange="nse", symbol=symbol)
                value = fund.holdings_value
                if value is not None:
                    total_value += value
                print(f"{symbol}: {value}")
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
            A dict with `day_change` and `day_change_percentage` in rupees and per cent since the previous close, and `unrealized` in rupees against what was paid, or None when this scheme is not held.

        Raises:
            ServiceUnavailableError: UBI's holdings document is missing or too old to serve.
            BrokerError: No broker's holdings could be read.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.

        Examples:
            Print what the ABSLFTTIDG units held have made or lost, or None when none are held:

            ```python
            from tradingmachine.assets import mutual_funds

            fund = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")
            print(fund.holdings_pnl)
            ```

            Print the unrealised profit or loss and the move since the previous valuation:

            ```python
            from tradingmachine.assets import mutual_funds

            fund = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")
            pnl = fund.holdings_pnl
            if pnl is None:
                print("No ABSLFTTIDG units are held.")
            else:
                print(f"Unrealised: {pnl['unrealized']:.2f}")
                print(f"Today: {pnl['day_change_percentage']:.2f} per cent")
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
        """Buys more units of this scheme to keep.

        The order is sent as `cnc`, which is what UBI accepts for this segment. Give a price: a mutual fund has no quote, so there is nothing for a market order to be priced against, and leaving price as None sends one anyway rather than second-guessing UBI.

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
            Send a limit order for one unit of ABSLFTTIDG, which goes to the broker at once, and cancel it as soon as it shows as open; a broker may instead allot the unit at the day's net asset value, so run this only if that is acceptable:

            ```python
            import time

            from tradingmachine.assets import mutual_funds

            fund = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")
            answer = fund.add_to_holdings(quantity=1, price=10.0)
            print(answer)
            order_id = answer["order_id"]
            for attempt in range(30):
                open_orders = fund.open_orders
                if open_orders is not None:
                    if order_id in open_orders["order_id"].tolist():
                        print(fund.cancel_order(order_id))
                        break
                time.sleep(1)
            print(fund.orders)
            ```

            Send the same order with a tag, then find it again among today's orders by its tag and cancel it if it is still open:

            ```python
            import time

            from tradingmachine.assets import mutual_funds

            fund = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")
            answer = fund.add_to_holdings(quantity=1, price=10.0, tag="examplefund")
            order_id = answer["order_id"]
            time.sleep(10)
            open_orders = fund.open_orders
            if open_orders is not None:
                if order_id in open_orders["order_id"].tolist():
                    print(fund.cancel_order(order_id))
            orders = fund.orders
            print(orders[orders["order_id"] == order_id])
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
            hold=False,
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
            HoldingError: This scheme is not held, or the quantity is more than the free units.
            UnifiedBrokerInterfaceError: Any failure reported by, or on the way to, UBI.

        Examples:
            Offer one held unit of ABSLFTTIDG at 3 per cent above its last valuation, and cancel the order as soon as it shows as open:

            ```python
            import time

            from tradingmachine.assets import mutual_funds

            fund = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")
            row = fund.holdings
            if row is None:
                print("No ABSLFTTIDG units are held, so there is nothing to reduce.")
            else:
                limit_price = round(row["last_price"] * 1.03, 2)
                answer = fund.reduce_holdings(quantity=1, price=limit_price)
                print(answer)
                order_id = answer["order_id"]
                for attempt in range(30):
                    open_orders = fund.open_orders
                    if open_orders is not None:
                        if order_id in open_orders["order_id"].tolist():
                            print(fund.cancel_order(order_id))
                            break
                    time.sleep(1)
            ```

            Ask to redeem far more units than are free, and handle the refusal, which comes before any order is sent:

            ```python
            from tradingmachine.assets import exceptions
            from tradingmachine.assets import mutual_funds

            fund = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")
            try:
                fund.reduce_holdings(quantity=10000000, price=10.0)
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
            HoldingError: This scheme is not held, or every unit held is pledged as collateral.
            UnifiedBrokerInterfaceError: Any failure reported by, or on the way to, UBI.

        Examples:
            Offer every free unit of ABSLFTTIDG at 3 per cent above its last valuation, and cancel the order as soon as it shows as open:

            ```python
            import time

            from tradingmachine.assets import mutual_funds

            fund = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")
            row = fund.holdings
            if row is None:
                print("No ABSLFTTIDG units are held, so there is nothing to sell.")
            else:
                limit_price = round(row["last_price"] * 1.03, 2)
                answer = fund.liquidate_holdings(price=limit_price)
                print(answer)
                order_id = answer["order_id"]
                for attempt in range(30):
                    open_orders = fund.open_orders
                    if open_orders is not None:
                        if order_id in open_orders["order_id"].tolist():
                            print(fund.cancel_order(order_id))
                            break
                    time.sleep(1)
            ```

            Try to redeem a whole holding and handle the refusal when none is held or every unit is pledged:

            ```python
            from tradingmachine.assets import exceptions
            from tradingmachine.assets import mutual_funds

            fund = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDN")
            try:
                answer = fund.liquidate_holdings(price=10.0)
            except exceptions.HoldingError as error:
                print(f"Nothing to redeem: {error}")
            else:
                print(answer)
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
        """Reads this scheme's holding once, refusing when it is not held.

        Returns:
            The dict holdings row for this scheme.

        Raises:
            HoldingError: No broker holds this scheme.
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
            hold=False,
        )

    @classmethod
    def search(
        cls,
        exchange: str,
        term: str,
        limit: int = SEARCH_LIMIT,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> pd.DataFrame | None:
        """Finds mutual fund schemes whose symbol contains a term.

        UBI puts an exact match first, then symbols starting with the term, then symbols containing it. A scheme's symbol is its exchange code rather than its published name, so a useful term is the fund house's prefix, such as `ABSL`, rather than words from the scheme's title.

        Args:
            exchange: The str exchange to search, which UBI only has as `nse`.
            term: The str the symbol must contain, matched without regard to case.
            limit: The int most rows to return, which UBI caps at 200.
            unified_broker_interface: The client.UnifiedBrokerInterface to send the request through, or None to share one client among all instruments.

        Returns:
            A pandas.DataFrame with `instrument_id`, `exchange`, `segment`, `shape`, `symbol` and the derivative fields left empty, or None when no scheme matches.

        Raises:
            BadRequestError: The exchange is not one UBI knows.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.

        Examples:
            Find the schemes whose exchange code starts with the fund house prefix `ABSL`:

            ```python
            from tradingmachine.assets import mutual_funds

            matches = mutual_funds.MutualFund.search(exchange="nse", term="ABSL")
            print(matches["symbol"].tolist())
            ```

            Count the schemes carried for a few fund house prefixes, at most two hundred each:

            ```python
            from tradingmachine.assets import mutual_funds

            for prefix in [
                "ABSL",
                "HDFC",
                "SBI",
                "ICICI",
            ]:
                matches = mutual_funds.MutualFund.search(
                    exchange="nse",
                    term=prefix,
                    limit=200,
                )
                if matches is None:
                    print(f"{prefix}: none")
                else:
                    print(f"{prefix}: {len(matches)} schemes")
            ```

            Build the first match as a scheme and print its identity:

            ```python
            from tradingmachine.assets import mutual_funds

            matches = mutual_funds.MutualFund.search(exchange="nse", term="ABSLFT")
            first_symbol = matches.iloc[0]["symbol"]
            fund = mutual_funds.MutualFund(exchange="nse", symbol=first_symbol)
            print(repr(fund))
            print(f"Lot size {fund.lot_size}, tick size {fund.tick_size}")
            ```
        """
        return cls._search_catalogue(
            exchange,
            MUTUAL_FUNDS_SEGMENT,
            term,
            limit,
            unified_broker_interface,
        )
