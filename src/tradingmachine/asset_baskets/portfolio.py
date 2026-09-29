"""A portfolio: a basket counted in units held, which can be valued, traded and rebalanced.

`Portfolio` gives every member a quantity, and optionally the average price it was bought at. It can be built by hand, or read from the account with `from_holdings` or `from_positions`, which build every member from one list request. Its weights are the members' shares of today's value, and its candles are what the same quantities would have been worth at each candle, so the inherited `sharpe_ratio` or `maximum_drawdown` describe the portfolio as it is held now.

`place_orders` sends one market order per member in a single `POST /api/orders/place` list request, which UBI's order engine places in parallel at whichever broker each order suits; it does not use UBI's `basket` synthetic order, which is capped at 25 legs and sends every leg to one broker. `rebalance_trades` works out the buys and sells that would move the portfolio to another basket's weights, and `rebalance` sends them. The quantities are floored to whole units and sent as computed, with no lot size or tick size check, because UBI checks orders itself.

Typical usage example:

  held = portfolio.Portfolio.from_holdings()
  value = held.value
  profit = held.unrealized_pnl
  trades = held.rebalance_trades(target=nifty_basket)
  results = held.rebalance(target=nifty_basket, product="cnc", dry_run=True)
"""

import math

import pandas as pd

from tradingmachine.asset_baskets import asset_basket
from tradingmachine.asset_baskets import basket_member
from tradingmachine.asset_baskets import exceptions
from tradingmachine.asset_baskets import member_resolver
from tradingmachine.unified_broker_interface import client

HOLDINGS_PATH = "/api/portfolio/holdings"

POSITIONS_PATH = "/api/portfolio/positions"

ORDER_PLACE_PATH = "/api/orders/place"

ORDER_LIST_TIMEOUT_SECONDS = 60

BUY = "buy"

SELL = "sell"

MARKET_ORDER_TYPE = "market"


class Portfolio(asset_basket.AssetBasket):
    """A basket of instruments held in known quantities."""

    KIND = "portfolio"

    def __init__(
        self,
        name: str,
        members: list[basket_member.BasketMember],
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Initialises the portfolio and checks that every member has a quantity.

        Args:
            name: The str name of the portfolio.
            members: A list of basket_member.BasketMember, each with a quantity, negative for a short position, and each a different instrument.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share the one every instrument uses.

        Raises:
            BasketMemberError: members is empty, names an instrument twice, or has a member without a quantity.
        """
        super().__init__(
            name=name,
            members=members,
            unified_broker_interface=unified_broker_interface,
        )
        for member in self.members:
            if member.quantity is None:
                raise exceptions.BasketMemberError(
                    f"Every member of a Portfolio needs a quantity: {member.label}"
                )

    @classmethod
    def from_holdings(
        cls,
        name: str = "holdings",
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> "Portfolio":
        """Builds a portfolio of the account's long-term holdings, as UBI reports them now.

        Args:
            name: The str name to give the portfolio.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share the one every instrument uses.

        Returns:
            A Portfolio with one member per holding, carrying its quantity and average price.

        Raises:
            BasketMemberError: The account holds nothing, or UBI could not find a held instrument.
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Build a portfolio of the account's holdings and print each quantity:

            ```python
            from tradingmachine.asset_baskets import exceptions
            from tradingmachine.asset_baskets import portfolio

            try:
                held = portfolio.Portfolio.from_holdings()
            except exceptions.BasketMemberError as error:
                print(error)
            else:
                print(held.quantities)
            ```

            Value the holdings and their profit over what was paid:

            ```python
            from tradingmachine.asset_baskets import portfolio

            held = portfolio.Portfolio.from_holdings(name="demat holdings")
            print(f"{held.size} holdings worth {held.value}")
            print(f"Unrealised profit: {held.unrealized_pnl}")
            ```
        """
        resolver = member_resolver.MemberResolver(unified_broker_interface)
        answer = resolver.unified_broker_interface.get(HOLDINGS_PATH)
        rows = []
        for holding in answer["holdings"]:
            if not holding.get("quantity"):
                continue
            rows.append(
                {
                    "instrument_id": holding.get("instrument_id"),
                    "exchange": holding.get("exchange"),
                    "segment": holding.get("segment"),
                    "symbol": holding.get("symbol"),
                    "quantity": holding["quantity"],
                    "average_price": holding.get("average_price"),
                }
            )
        if not rows:
            raise exceptions.BasketMemberError("The account holds nothing")
        members = resolver.resolve(rows)
        return cls(
            name=name,
            members=members,
            unified_broker_interface=resolver.unified_broker_interface,
        )

    @classmethod
    def from_positions(
        cls,
        name: str = "positions",
        day: bool = False,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ) -> "Portfolio":
        """Builds a portfolio of the account's open positions, as UBI reports them now.

        An instrument held under more than one product, such as intraday and carry, becomes one member whose quantity is the total; its average price is then left unknown, because the products' prices cannot be added.

        Args:
            name: The str name to give the portfolio.
            day: A bool that is True for today's positions and False for the net positions.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share the one every instrument uses.

        Returns:
            A Portfolio with one member per instrument with a non-zero position.

        Raises:
            BasketMemberError: No position is open, or UBI could not find a position's instrument.
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Build a portfolio of the account's net positions, or say there are none:

            ```python
            from tradingmachine.asset_baskets import exceptions
            from tradingmachine.asset_baskets import portfolio

            try:
                positions = portfolio.Portfolio.from_positions()
            except exceptions.BasketMemberError as error:
                print(error)
            else:
                print(positions.quantities)
            ```

            Build a portfolio of today's positions only and print its value:

            ```python
            from tradingmachine.asset_baskets import exceptions
            from tradingmachine.asset_baskets import portfolio

            try:
                today = portfolio.Portfolio.from_positions(name="today", day=True)
            except exceptions.BasketMemberError as error:
                print(f"Nothing traded today: {error}")
            else:
                print(today.value)
            ```
        """
        resolver = member_resolver.MemberResolver(unified_broker_interface)
        answer = resolver.unified_broker_interface.get(POSITIONS_PATH)
        if day:
            positions = answer["day"]
        else:
            positions = answer["net"]
        rows_by_instrument_id = {}
        for position in positions:
            if not position.get("quantity"):
                continue
            instrument_id = position["instrument_id"]
            if instrument_id in rows_by_instrument_id:
                row = rows_by_instrument_id[instrument_id]
                row["quantity"] += position["quantity"]
                row["average_price"] = None
            else:
                rows_by_instrument_id[instrument_id] = {
                    "instrument_id": instrument_id,
                    "quantity": position["quantity"],
                    "average_price": position.get("average_price"),
                }
        rows = []
        for row in rows_by_instrument_id.values():
            if row["quantity"] != 0:
                rows.append(row)
        if not rows:
            raise exceptions.BasketMemberError("No position is open")
        members = resolver.resolve(rows)
        return cls(
            name=name,
            members=members,
            unified_broker_interface=resolver.unified_broker_interface,
        )

    @property
    def quantities(self) -> pd.Series:
        """A pandas.Series of each member's float quantity, indexed by member label.

        Examples:
            Print how many units of each member are held:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            quantities = {
                "IDEA": 100,
                "INFY": 5,
                "TCS": 2,
            }
            average_prices = {
                "IDEA": 12.5,
                "INFY": 1450.0,
                "TCS": 3100.0,
            }
            members = []
            for symbol in quantities:
                share = equities.Equity(exchange="nse", symbol=symbol)
                member = basket_member.BasketMember(
                    share,
                    quantity=quantities[symbol],
                    average_price=average_prices[symbol],
                )
                members.append(member)
            held = portfolio.Portfolio(name="long-term shares", members=members)
            print(held.quantities)
            ```

            See a short position as a negative quantity:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            members = [
                basket_member.BasketMember(
                    equities.Equity(exchange="nse", symbol="HDFCBANK"), quantity=10
                ),
                basket_member.BasketMember(
                    equities.Equity(exchange="nse", symbol="ICICIBANK"), quantity=-8
                ),
            ]
            held = portfolio.Portfolio(name="bank pair", members=members)
            print(held.quantities)
            ```
        """
        held = []
        for member in self.members:
            held.append(float(member.quantity))
        return pd.Series(held, index=self.labels, dtype=float)

    @property
    def values(self) -> pd.Series | None:
        """A pandas.Series of each member's float value in rupees at its last price, negative for a short position, indexed by member label, or None when any member has no last price; read from UBI in one request on every access.

        Examples:
            Print what each holding is worth at its last price:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            quantities = {
                "IDEA": 100,
                "INFY": 5,
                "TCS": 2,
            }
            average_prices = {
                "IDEA": 12.5,
                "INFY": 1450.0,
                "TCS": 3100.0,
            }
            members = []
            for symbol in quantities:
                share = equities.Equity(exchange="nse", symbol=symbol)
                member = basket_member.BasketMember(
                    share,
                    quantity=quantities[symbol],
                    average_price=average_prices[symbol],
                )
                members.append(member)
            held = portfolio.Portfolio(name="long-term shares", members=members)
            print(held.values.round(2))
            ```

            Print the value of each side of a long and short pair:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            members = [
                basket_member.BasketMember(
                    equities.Equity(exchange="nse", symbol="HDFCBANK"), quantity=10
                ),
                basket_member.BasketMember(
                    equities.Equity(exchange="nse", symbol="ICICIBANK"), quantity=-8
                ),
            ]
            held = portfolio.Portfolio(name="bank pair", members=members)
            values = held.values
            print(values.round(2))
            print(f"Net: {values.sum():.2f}")
            ```
        """
        frame = self.last_prices
        if frame["last_price"].isna().any():
            return None
        last_prices = pd.Series(
            frame["last_price"].to_numpy(dtype=float), index=self.labels
        )
        return self.quantities * last_prices

    @property
    def value(self) -> float | None:
        """The float value in rupees of the whole portfolio at last prices, or None when any member has no last price, read from UBI on every access.

        Examples:
            Print the whole portfolio's value at last prices:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            quantities = {
                "IDEA": 100,
                "INFY": 5,
                "TCS": 2,
            }
            average_prices = {
                "IDEA": 12.5,
                "INFY": 1450.0,
                "TCS": 3100.0,
            }
            members = []
            for symbol in quantities:
                share = equities.Equity(exchange="nse", symbol=symbol)
                member = basket_member.BasketMember(
                    share,
                    quantity=quantities[symbol],
                    average_price=average_prices[symbol],
                )
                members.append(member)
            held = portfolio.Portfolio(name="long-term shares", members=members)
            print(f"Portfolio value: Rs {held.value:,.2f}")
            ```

            Print the net value of a long and short pair, which can be small or negative:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            members = [
                basket_member.BasketMember(
                    equities.Equity(exchange="nse", symbol="HDFCBANK"), quantity=10
                ),
                basket_member.BasketMember(
                    equities.Equity(exchange="nse", symbol="ICICIBANK"), quantity=-8
                ),
            ]
            held = portfolio.Portfolio(name="bank pair", members=members)
            print(held.value)
            ```
        """
        values = self.values
        if values is None:
            return None
        return float(values.sum())

    @property
    def weights(self) -> pd.Series:
        """A pandas.Series of each member's float share of the portfolio's gross value at last prices, indexed by member label, where a short position has a negative weight and the absolute weights sum to 1.

        Raises:
            BasketMemberError: A member has no last price, so its share cannot be known.

        Examples:
            Print each holding's share of the portfolio's value:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            quantities = {
                "IDEA": 100,
                "INFY": 5,
                "TCS": 2,
            }
            average_prices = {
                "IDEA": 12.5,
                "INFY": 1450.0,
                "TCS": 3100.0,
            }
            members = []
            for symbol in quantities:
                share = equities.Equity(exchange="nse", symbol=symbol)
                member = basket_member.BasketMember(
                    share,
                    quantity=quantities[symbol],
                    average_price=average_prices[symbol],
                )
                members.append(member)
            held = portfolio.Portfolio(name="long-term shares", members=members)
            print(held.weights.round(3))
            ```

            See a short position's weight come out negative:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            members = [
                basket_member.BasketMember(
                    equities.Equity(exchange="nse", symbol="HDFCBANK"), quantity=10
                ),
                basket_member.BasketMember(
                    equities.Equity(exchange="nse", symbol="ICICIBANK"), quantity=-8
                ),
            ]
            held = portfolio.Portfolio(name="bank pair", members=members)
            weights = held.weights
            print(weights.round(3))
            print(f"Absolute weights add up to {weights.abs().sum()}")
            ```
        """
        values = self.values
        if values is None:
            raise exceptions.BasketMemberError(
                f"A member of {self.name!r} has no last price, so the weights cannot be known"
            )
        return values / values.abs().sum()

    @property
    def invested_value(self) -> float | None:
        """The float amount in rupees paid for the portfolio, the sum of quantity times average price, or None when any member's average price is unknown.

        Examples:
            Print what the holdings cost:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            quantities = {
                "IDEA": 100,
                "INFY": 5,
                "TCS": 2,
            }
            average_prices = {
                "IDEA": 12.5,
                "INFY": 1450.0,
                "TCS": 3100.0,
            }
            members = []
            for symbol in quantities:
                share = equities.Equity(exchange="nse", symbol=symbol)
                member = basket_member.BasketMember(
                    share,
                    quantity=quantities[symbol],
                    average_price=average_prices[symbol],
                )
                members.append(member)
            held = portfolio.Portfolio(name="long-term shares", members=members)
            print(f"Invested: Rs {held.invested_value:,.2f}")
            ```

            See it be None when a member's average price is unknown:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            members = [
                basket_member.BasketMember(
                    equities.Equity(exchange="nse", symbol="HDFCBANK"), quantity=10
                ),
                basket_member.BasketMember(
                    equities.Equity(exchange="nse", symbol="ICICIBANK"), quantity=-8
                ),
            ]
            held = portfolio.Portfolio(name="bank pair", members=members)
            print(held.invested_value)
            ```
        """
        total = 0.0
        for member in self.members:
            if member.average_price is None:
                return None
            total += float(member.quantity) * float(member.average_price)
        return total

    @property
    def unrealized_pnl(self) -> float | None:
        """The float profit in rupees of the portfolio's value over what was paid for it, or None when the value or any average price is unknown, read from UBI on every access.

        Examples:
            Print the profit of the holdings over what was paid for them:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            quantities = {
                "IDEA": 100,
                "INFY": 5,
                "TCS": 2,
            }
            average_prices = {
                "IDEA": 12.5,
                "INFY": 1450.0,
                "TCS": 3100.0,
            }
            members = []
            for symbol in quantities:
                share = equities.Equity(exchange="nse", symbol=symbol)
                member = basket_member.BasketMember(
                    share,
                    quantity=quantities[symbol],
                    average_price=average_prices[symbol],
                )
                members.append(member)
            held = portfolio.Portfolio(name="long-term shares", members=members)
            print(f"Unrealised profit: Rs {held.unrealized_pnl:,.2f}")
            ```

            Print the profit as a percentage of the amount invested:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            quantities = {
                "IDEA": 100,
                "INFY": 5,
                "TCS": 2,
            }
            average_prices = {
                "IDEA": 12.5,
                "INFY": 1450.0,
                "TCS": 3100.0,
            }
            members = []
            for symbol in quantities:
                share = equities.Equity(exchange="nse", symbol=symbol)
                member = basket_member.BasketMember(
                    share,
                    quantity=quantities[symbol],
                    average_price=average_prices[symbol],
                )
                members.append(member)
            held = portfolio.Portfolio(name="long-term shares", members=members)
            profit = held.unrealized_pnl
            percent = profit / held.invested_value * 100
            print(f"{percent:+.2f}%")
            ```
        """
        invested_value = self.invested_value
        if invested_value is None:
            return None
        value = self.value
        if value is None:
            return None
        return value - invested_value

    @property
    def day_pnl(self) -> float | None:
        """The float profit in rupees since the previous close, the sum of quantity times the change from the previous close to the last price, or None when any member has no quote, read from UBI on every access.

        Examples:
            Print today's profit or loss on the holdings:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            quantities = {
                "IDEA": 100,
                "INFY": 5,
                "TCS": 2,
            }
            average_prices = {
                "IDEA": 12.5,
                "INFY": 1450.0,
                "TCS": 3100.0,
            }
            members = []
            for symbol in quantities:
                share = equities.Equity(exchange="nse", symbol=symbol)
                member = basket_member.BasketMember(
                    share,
                    quantity=quantities[symbol],
                    average_price=average_prices[symbol],
                )
                members.append(member)
            held = portfolio.Portfolio(name="long-term shares", members=members)
            print(f"Today: Rs {held.day_pnl:+,.2f}")
            ```

            Print today's profit on a long and short pair, where the short gains when its share falls:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            members = [
                basket_member.BasketMember(
                    equities.Equity(exchange="nse", symbol="HDFCBANK"), quantity=10
                ),
                basket_member.BasketMember(
                    equities.Equity(exchange="nse", symbol="ICICIBANK"), quantity=-8
                ),
            ]
            held = portfolio.Portfolio(name="bank pair", members=members)
            print(held.day_pnl)
            ```
        """
        frame = self.ohlc
        if frame["last_price"].isna().any() or frame["previous_close"].isna().any():
            return None
        changes = frame["last_price"].to_numpy(dtype=float) - frame[
            "previous_close"
        ].to_numpy(dtype=float)
        return float((self.quantities.to_numpy() * changes).sum())

    @property
    def day_change_percent(self) -> float | None:
        """The float move of the portfolio's value since the previous close, in percent, or None when any member has no quote, read from UBI on every access.

        Examples:
            Print the portfolio's move since the previous close:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            quantities = {
                "IDEA": 100,
                "INFY": 5,
                "TCS": 2,
            }
            average_prices = {
                "IDEA": 12.5,
                "INFY": 1450.0,
                "TCS": 3100.0,
            }
            members = []
            for symbol in quantities:
                share = equities.Equity(exchange="nse", symbol=symbol)
                member = basket_member.BasketMember(
                    share,
                    quantity=quantities[symbol],
                    average_price=average_prices[symbol],
                )
                members.append(member)
            held = portfolio.Portfolio(name="long-term shares", members=members)
            print(f"{held.day_change_percent:+.2f}%")
            ```

            Compare the portfolio's move with each holding's:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            quantities = {
                "IDEA": 100,
                "INFY": 5,
                "TCS": 2,
            }
            average_prices = {
                "IDEA": 12.5,
                "INFY": 1450.0,
                "TCS": 3100.0,
            }
            members = []
            for symbol in quantities:
                share = equities.Equity(exchange="nse", symbol=symbol)
                member = basket_member.BasketMember(
                    share,
                    quantity=quantities[symbol],
                    average_price=average_prices[symbol],
                )
                members.append(member)
            held = portfolio.Portfolio(name="long-term shares", members=members)
            print(held.ohlc[["label", "change_percent"]])
            print(f"Portfolio: {held.day_change_percent:+.2f}%")
            ```
        """
        frame = self.ohlc
        if frame["last_price"].isna().any() or frame["previous_close"].isna().any():
            return None
        quantities = self.quantities.to_numpy()
        previous_value = (
            quantities * frame["previous_close"].to_numpy(dtype=float)
        ).sum()
        if previous_value == 0:
            return None
        last_value = (quantities * frame["last_price"].to_numpy(dtype=float)).sum()
        return float((last_value / previous_value - 1) * 100)

    def place_orders(
        self,
        product: str,
        transaction_type: str = BUY,
        validity: str = "day",
        tag: str | None = None,
        dry_run: bool = False,
    ) -> pd.DataFrame:
        """Sends one market order per member for its quantity, all in one list request.

        With `buy`, each member's quantity is bought, and a negative quantity is sold instead; with `sell`, the other way round. This buys a portfolio built by hand or by `Index.to_portfolio`, and sells one to close it. The orders are placed in parallel and not as one unit, so some can be accepted while others are refused, and each row of the answer says what happened to its order.

        Args:
            product: The str product every order is sent with, such as `cnc` for delivery or `mis` for intraday.
            transaction_type: The str side for a positive quantity, `buy` or `sell`.
            validity: The str validity of every order, such as `day`.
            tag: A str tag to put on every order, or None.
            dry_run: A bool that is True to have UBI build every order without sending it.

        Returns:
            A pandas.DataFrame with one row per order, holding `label`, `instrument_id`, `transaction_type`, `quantity`, the entry's HTTP `status`, the `broker` UBI chose, `outcome`, `order_id`, `parent_id`, `intent_id` and `error`.

        Raises:
            BadRequestError: UBI refused the whole list, such as one longer than its limit of 500 orders.
            ServiceUnavailableError: UBI's order engine is not running, so nothing was placed.
            UnifiedBrokerInterfaceError: Any other failure of the whole request.

        Examples:
            Have UBI build the market orders for a portfolio without sending them:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            quantities = {
                "IDEA": 100,
                "INFY": 5,
                "TCS": 2,
            }
            average_prices = {
                "IDEA": 12.5,
                "INFY": 1450.0,
                "TCS": 3100.0,
            }
            members = []
            for symbol in quantities:
                share = equities.Equity(exchange="nse", symbol=symbol)
                member = basket_member.BasketMember(
                    share,
                    quantity=quantities[symbol],
                    average_price=average_prices[symbol],
                )
                members.append(member)
            held = portfolio.Portfolio(name="long-term shares", members=members)
            results = held.place_orders(product="cnc", dry_run=True)
            print(results[["label", "transaction_type", "quantity", "status"]])
            ```

            Buy one IDEA share intraday with a market order and sell it straight back once it fills:

            ```python
            import time

            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            idea = equities.Equity(exchange="nse", symbol="IDEA")
            one_share = portfolio.Portfolio(
                name="one IDEA share",
                members=[
                    basket_member.BasketMember(idea, quantity=1),
                ],
            )
            bought = one_share.place_orders(product="mis", tag="basketexample")
            print(bought[["label", "transaction_type", "outcome", "order_id"]])
            order_id = str(bought.loc[0, "order_id"])
            status = None
            for attempt in range(15):
                time.sleep(2)
                orders = idea.orders
                if orders is None:
                    continue
                matching = orders[orders["order_id"].astype(str) == order_id]
                if matching.empty:
                    continue
                status = matching["status"].iloc[0]
                if status in ("COMPLETE", "REJECTED", "CANCELLED"):
                    break
            print(f"The buy order is {status}")
            if status == "COMPLETE":
                sold = one_share.place_orders(product="mis", transaction_type="sell")
                print(sold[["label", "transaction_type", "outcome", "error"]])
                if sold.loc[0, "outcome"] != "accepted":
                    closed = idea.reduce_position(quantity=1, product="mis")
                    print(f"Closed instead: {closed['outcome']}")
            elif status in ("OPEN", "PENDING"):
                print(idea.cancel_order(order_id)["outcome"])
            ```
        """
        planned = []
        for member in self.members:
            if member.quantity == 0:
                continue
            side = transaction_type
            if member.quantity < 0:
                side = self._opposite_side(transaction_type)
            planned.append(
                {
                    "label": member.label,
                    "instrument_id": member.instrument.instrument_id,
                    "transaction_type": side,
                    "quantity": abs(member.quantity),
                }
            )
        return self._send_orders(planned, product, validity, tag, dry_run)

    def rebalance_trades(
        self,
        target: asset_basket.AssetBasket,
        capital: float | None = None,
    ) -> pd.DataFrame:
        """Works out the buys and sells that would give the portfolio another basket's weights, without sending anything.

        Each target quantity is the capital times the target weight divided by the last price, floored to a whole unit. An instrument held but not in the target is sold entirely, and one in the target but not held is bought.

        Args:
            target: The AssetBasket whose weights to move to, such as an Index.
            capital: The float amount in rupees to spread across the target, or None to use the portfolio's value now.

        Returns:
            A pandas.DataFrame with one row per instrument that needs a trade, sells first, holding `label`, `instrument_id`, `last_price`, `current_quantity`, `target_quantity`, `trade_quantity`, which is negative for a sale, and `transaction_type`.

        Raises:
            BasketMemberError: An instrument in either basket has no last price.
            UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.

        Examples:
            Work out the trades that would move a portfolio to equal weights in two shares:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import index
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            quantities = {
                "IDEA": 100,
                "INFY": 5,
                "TCS": 2,
            }
            average_prices = {
                "IDEA": 12.5,
                "INFY": 1450.0,
                "TCS": 3100.0,
            }
            members = []
            for symbol in quantities:
                share = equities.Equity(exchange="nse", symbol=symbol)
                member = basket_member.BasketMember(
                    share,
                    quantity=quantities[symbol],
                    average_price=average_prices[symbol],
                )
                members.append(member)
            held = portfolio.Portfolio(name="long-term shares", members=members)

            target_members = []
            for symbol in [
                "INFY",
                "TCS",
            ]:
                share = equities.Equity(exchange="nse", symbol=symbol)
                target_members.append(basket_member.BasketMember(share))
            target = index.Index(
                name="IT equal",
                members=target_members,
                weighting="equal",
            )
            trades = held.rebalance_trades(target=target)
            print(trades[["label", "current_quantity", "target_quantity"]])
            ```

            Work out the trades for a fixed sum of money rather than the portfolio's value:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import index
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            quantities = {
                "IDEA": 100,
                "INFY": 5,
                "TCS": 2,
            }
            average_prices = {
                "IDEA": 12.5,
                "INFY": 1450.0,
                "TCS": 3100.0,
            }
            members = []
            for symbol in quantities:
                share = equities.Equity(exchange="nse", symbol=symbol)
                member = basket_member.BasketMember(
                    share,
                    quantity=quantities[symbol],
                    average_price=average_prices[symbol],
                )
                members.append(member)
            held = portfolio.Portfolio(name="long-term shares", members=members)

            target_members = []
            for symbol in [
                "INFY",
                "TCS",
            ]:
                share = equities.Equity(exchange="nse", symbol=symbol)
                target_members.append(basket_member.BasketMember(share))
            target = index.Index(
                name="IT equal",
                members=target_members,
                weighting="equal",
            )
            trades = held.rebalance_trades(target=target, capital=50000)
            print(trades[["label", "trade_quantity", "transaction_type"]])
            ```
        """
        target_weights = target._weights_by_instrument_id()
        instruments_by_id = {}
        for member in self.members:
            instruments_by_id[member.instrument.instrument_id] = member.instrument
        for instrument in target.instruments:
            if instrument.instrument_id not in instruments_by_id:
                instruments_by_id[instrument.instrument_id] = instrument
        all_instruments = list(instruments_by_id.values())
        last_prices = self._last_prices_by_instrument_id(all_instruments)
        current_quantities = {}
        for member in self.members:
            current_quantities[member.instrument.instrument_id] = float(member.quantity)
        if capital is None:
            capital = 0.0
            for instrument_id, quantity in current_quantities.items():
                capital += quantity * last_prices[instrument_id]
        rows = []
        for instrument in all_instruments:
            instrument_id = instrument.instrument_id
            last_price = last_prices[instrument_id]
            current_quantity = current_quantities.get(instrument_id, 0.0)
            target_quantity = self._whole_units(
                capital * target_weights.get(instrument_id, 0.0) / last_price
            )
            trade_quantity = target_quantity - current_quantity
            if trade_quantity == 0:
                continue
            if trade_quantity > 0:
                side = BUY
            else:
                side = SELL
            rows.append(
                {
                    "label": basket_member.BasketMember(instrument).label,
                    "instrument_id": instrument_id,
                    "last_price": last_price,
                    "current_quantity": current_quantity,
                    "target_quantity": target_quantity,
                    "trade_quantity": trade_quantity,
                    "transaction_type": side,
                }
            )
        columns = [
            "label",
            "instrument_id",
            "last_price",
            "current_quantity",
            "target_quantity",
            "trade_quantity",
            "transaction_type",
        ]
        frame = pd.DataFrame(rows, columns=columns)
        return frame.sort_values("trade_quantity").reset_index(drop=True)

    def rebalance(
        self,
        target: asset_basket.AssetBasket,
        product: str,
        capital: float | None = None,
        validity: str = "day",
        tag: str | None = None,
        dry_run: bool = False,
    ) -> pd.DataFrame:
        """Sends the market orders `rebalance_trades` works out, all in one list request.

        The sales and purchases are sent together and placed in parallel, so for a delivery account the purchases must be affordable without the money the sales will release.

        Args:
            target: The AssetBasket whose weights to move to, such as an Index.
            product: The str product every order is sent with, such as `cnc`.
            capital: The float amount in rupees to spread across the target, or None to use the portfolio's value now.
            validity: The str validity of every order, such as `day`.
            tag: A str tag to put on every order, or None.
            dry_run: A bool that is True to have UBI build every order without sending it.

        Returns:
            A pandas.DataFrame with one row per order, in the form `place_orders` returns, which is empty when no trade is needed.

        Raises:
            BasketMemberError: An instrument in either basket has no last price.
            ServiceUnavailableError: UBI's order engine is not running, so nothing was placed.
            UnifiedBrokerInterfaceError: Any other failure of a whole request.

        Examples:
            Have UBI build the rebalancing orders without sending them:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import index
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            quantities = {
                "IDEA": 100,
                "INFY": 5,
                "TCS": 2,
            }
            average_prices = {
                "IDEA": 12.5,
                "INFY": 1450.0,
                "TCS": 3100.0,
            }
            members = []
            for symbol in quantities:
                share = equities.Equity(exchange="nse", symbol=symbol)
                member = basket_member.BasketMember(
                    share,
                    quantity=quantities[symbol],
                    average_price=average_prices[symbol],
                )
                members.append(member)
            held = portfolio.Portfolio(name="long-term shares", members=members)

            target_members = []
            for symbol in [
                "INFY",
                "TCS",
            ]:
                share = equities.Equity(exchange="nse", symbol=symbol)
                target_members.append(basket_member.BasketMember(share))
            target = index.Index(
                name="IT equal",
                members=target_members,
                weighting="equal",
            )
            results = held.rebalance(target=target, product="cnc", dry_run=True)
            print(results[["label", "transaction_type", "quantity", "status"]])
            ```

            Build the orders for a fixed sum of money and a tag, still as a dry run:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import index
            from tradingmachine.asset_baskets import portfolio
            from tradingmachine.assets import equities

            quantities = {
                "IDEA": 100,
                "INFY": 5,
                "TCS": 2,
            }
            average_prices = {
                "IDEA": 12.5,
                "INFY": 1450.0,
                "TCS": 3100.0,
            }
            members = []
            for symbol in quantities:
                share = equities.Equity(exchange="nse", symbol=symbol)
                member = basket_member.BasketMember(
                    share,
                    quantity=quantities[symbol],
                    average_price=average_prices[symbol],
                )
                members.append(member)
            held = portfolio.Portfolio(name="long-term shares", members=members)

            target_members = []
            for symbol in [
                "INFY",
                "TCS",
            ]:
                share = equities.Equity(exchange="nse", symbol=symbol)
                target_members.append(basket_member.BasketMember(share))
            target = index.Index(
                name="IT equal",
                members=target_members,
                weighting="equal",
            )
            results = held.rebalance(
                target=target,
                product="cnc",
                capital=50000,
                tag="rebalance",
                dry_run=True,
            )
            print(results[["label", "quantity", "status", "error"]])
            ```
        """
        trades = self.rebalance_trades(target, capital)
        planned = []
        for trade in trades.itertuples(index=False):
            planned.append(
                {
                    "label": trade.label,
                    "instrument_id": trade.instrument_id,
                    "transaction_type": trade.transaction_type,
                    "quantity": abs(trade.trade_quantity),
                }
            )
        return self._send_orders(planned, product, validity, tag, dry_run)

    def _send_orders(
        self,
        planned: list[dict],
        product: str,
        validity: str,
        tag: str | None,
        dry_run: bool,
    ) -> pd.DataFrame:
        """Sends planned market orders in one list request and tabulates UBI's answer.

        Args:
            planned: A list of dicts, each with `label`, `instrument_id`, `transaction_type` and a positive `quantity`.
            product: The str product every order is sent with.
            validity: The str validity of every order.
            tag: A str tag to put on every order, or None.
            dry_run: A bool that is True to have UBI build every order without sending it.

        Returns:
            A pandas.DataFrame with one row per planned order, holding `label`, `instrument_id`, `transaction_type`, `quantity`, `status`, `broker`, `outcome`, `order_id`, `parent_id`, `intent_id` and `error`, which is empty when nothing was planned.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the whole list or could not be reached.
        """
        columns = [
            "label",
            "instrument_id",
            "transaction_type",
            "quantity",
            "status",
            "broker",
            "outcome",
            "order_id",
            "parent_id",
            "intent_id",
            "error",
        ]
        if not planned:
            return pd.DataFrame(columns=columns)
        orders = []
        for order in planned:
            body = {
                "instrument_id": order["instrument_id"],
                "transaction_type": order["transaction_type"],
                "order_type": MARKET_ORDER_TYPE,
                "product": product,
                "quantity": self._plain_number(order["quantity"]),
                "validity": validity,
                "after_market": False,
            }
            if tag is not None:
                body["tag"] = tag
            orders.append(body)
        response = self._unified_broker_interface.post(
            ORDER_PLACE_PATH,
            body={
                "orders": orders,
                "dry_run": bool(dry_run),
            },
            timeout_seconds=ORDER_LIST_TIMEOUT_SECONDS,
        )
        results = sorted(
            response["results"], key=lambda result: result["request_index"]
        )
        rows = []
        for order, result in zip(planned, results):
            answer = result.get("response") or {}
            rows.append(
                {
                    "label": order["label"],
                    "instrument_id": order["instrument_id"],
                    "transaction_type": order["transaction_type"],
                    "quantity": order["quantity"],
                    "status": result["status"],
                    "broker": answer.get("broker"),
                    "outcome": answer.get("outcome"),
                    "order_id": answer.get("order_id"),
                    "parent_id": answer.get("parent_id"),
                    "intent_id": result.get("intent_id"),
                    "error": answer.get("error"),
                }
            )
        return pd.DataFrame(rows, columns=columns)

    def _candle_quantities(self, first_closes: pd.Series) -> pd.Series:
        """Uses the quantities held for the portfolio's candles, so they show what the holdings were worth.

        Args:
            first_closes: A pandas.Series of each member's float close at the first shared candle, indexed by member label, which only fixes the order here.

        Returns:
            A pandas.Series of float quantities indexed by member label.

        Raises:
            Nothing.
        """
        return self.quantities.reindex(first_closes.index)

    @staticmethod
    def _opposite_side(transaction_type: str) -> str:
        """Gives the other side of a trade.

        Args:
            transaction_type: The str side, `buy` or `sell`.

        Returns:
            The str `sell` for `buy`, and `buy` for anything else.

        Raises:
            Nothing.
        """
        if transaction_type == BUY:
            return SELL
        return BUY

    @staticmethod
    def _whole_units(quantity: float) -> float:
        """Rounds a quantity towards zero to a whole number of units.

        Args:
            quantity: The float quantity, negative for a short position.

        Returns:
            The float whole quantity, with the same sign.

        Raises:
            Nothing.
        """
        if quantity < 0:
            return float(-math.floor(-quantity))
        return float(math.floor(quantity))

    @staticmethod
    def _plain_number(quantity: float) -> int | float:
        """Turns a whole float quantity into an int, so it reaches UBI as a whole number.

        Args:
            quantity: The int or float quantity.

        Returns:
            The int quantity when it is whole, or the float as given otherwise.

        Raises:
            Nothing.
        """
        if isinstance(quantity, float) and quantity.is_integer():
            return int(quantity)
        return quantity
