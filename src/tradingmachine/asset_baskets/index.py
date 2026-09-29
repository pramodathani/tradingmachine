"""An index: a weighted basket whose level is followed over time, such as NIFTY or one of the caller's own.

`Index` weights its members in one of three ways. `stated` uses each member's own weight, as a published index's factsheet gives them. `equal` gives every member the same weight. `price` weights each member by its price, as a price-weighted index such as the Dow Jones does, which is the same as holding one unit of each. Its candles start from `base_value` at the first candle of whatever range is asked for, so two ranges start from the same number; `level` instead fixes the start at `base_date` and reports today's level from it.

An Index usually describes the contents of an official index that UBI quotes, such as NIFTY, and then `linked_instrument` is that index. Comparing the two, for instance with `tracking_error(benchmark=index.linked_instrument)`, shows how well the stored members and weights reproduce it. `to_portfolio` turns the index into whole units of each member for a sum of money, ready for `Portfolio.place_orders`.

Typical usage example:

  it_index = index.Index(name="my IT index", members=members, weighting="equal")
  frame = it_index.prices(days=365)
  holdings = it_index.to_portfolio(capital=100000)
"""

import datetime
import math

import pandas as pd

from tradingmachine.asset_baskets import asset_basket
from tradingmachine.asset_baskets import basket_member
from tradingmachine.asset_baskets import exceptions
from tradingmachine.asset_baskets import portfolio
from tradingmachine.assets import instruments
from tradingmachine.unified_broker_interface import client

STATED_WEIGHTING = "stated"

EQUAL_WEIGHTING = "equal"

PRICE_WEIGHTING = "price"

WEIGHTINGS = [
    STATED_WEIGHTING,
    EQUAL_WEIGHTING,
    PRICE_WEIGHTING,
]

BASE_DATE_SEARCH_DAYS = 10


class Index(asset_basket.AssetBasket):
    """A weighted basket of instruments that is followed as one level.

    Attributes:
        weighting: The str way the members are weighted: `stated`, `equal` or `price`.
        base_date: The datetime.date the level is measured from, when it equals base_value, or None when no base date is set.
    """

    KIND = "index"

    def __init__(
        self,
        name: str,
        members: list[basket_member.BasketMember],
        weighting: str = STATED_WEIGHTING,
        base_value: float = asset_basket.DEFAULT_BASE_VALUE,
        base_date: datetime.date | str | None = None,
        linked_instrument: instruments.Instrument | None = None,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Initialises the index and checks its weighting.

        Args:
            name: The str name of the index, such as `NIFTY`.
            members: A list of basket_member.BasketMember, each a different instrument, all with a weight when weighting is `stated`.
            weighting: The str way to weight the members: `stated`, `equal` or `price`.
            base_value: The float level the index starts from.
            base_date: The datetime.date or `YYYY-MM-DD` str the level starts from, or None when no level is followed.
            linked_instrument: The tradingmachine.assets.instruments.Instrument the index describes, such as the NIFTY index row UBI quotes, or None.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share the one every instrument uses.

        Raises:
            BasketMemberError: members is empty, names an instrument twice, or lacks weights when weighting is `stated`.
            ValueError: weighting is not one of `stated`, `equal` and `price`, or base_value is not positive.
        """
        if weighting not in WEIGHTINGS:
            raise ValueError(f"Not an index weighting: {weighting=}")
        if base_value <= 0:
            raise ValueError(f"The base value must be positive: {base_value=}")
        super().__init__(
            name=name,
            members=members,
            linked_instrument=linked_instrument,
            unified_broker_interface=unified_broker_interface,
        )
        if weighting == STATED_WEIGHTING and self.members[0].weight is None:
            raise exceptions.BasketMemberError(
                f"A stated weighting needs a weight on every member of {name!r}; use weighting='equal' otherwise"
            )
        self.weighting = weighting
        self.base_value = float(base_value)
        if isinstance(base_date, str):
            base_date = datetime.date.fromisoformat(base_date)
        self.base_date = base_date

    @property
    def weights(self) -> pd.Series:
        """A pandas.Series of float weights indexed by member label that sum to 1: the stated weights, equal weights, or for a price weighting each member's share of the sum of last prices, read from UBI on every access.

        Raises:
            BasketMemberError: The weighting is `price` and a member has no last price.

        Examples:
            Print the weights of an equal-weighted index:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import index
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HCLTECH",
                "WIPRO",
                "TECHM",
            ]
            members = []
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                members.append(basket_member.BasketMember(share))
            it_index = index.Index(name="IT", members=members, weighting="equal")
            print(it_index.weights)
            ```

            Print the weights of a price-weighted index, which follow the last prices:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import index
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HCLTECH",
                "WIPRO",
                "TECHM",
            ]
            members = []
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                members.append(basket_member.BasketMember(share))
            it_index = index.Index(name="IT", members=members, weighting="price")
            print(it_index.weights.round(3))
            ```
        """
        if self.weighting == EQUAL_WEIGHTING:
            return pd.Series(1 / self.size, index=self.labels, dtype=float)
        if self.weighting == PRICE_WEIGHTING:
            last_prices = self._last_prices_by_instrument_id(self.instruments)
            prices = []
            for member in self.members:
                prices.append(last_prices[member.instrument.instrument_id])
            price_series = pd.Series(prices, index=self.labels, dtype=float)
            return price_series / price_series.sum()
        return super().weights

    @property
    def level(self) -> float:
        """The float level of the index now: base_value at the closes of base_date, moved by the members' last prices since, read from UBI on every access.

        Raises:
            AssetBasketError: No base_date is set.
            BasketMemberError: A member has no candle on or just after base_date, or no last price.

        Examples:
            Print today's level of an index that started at 1000 on the first trading day of the year:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import index
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HCLTECH",
                "WIPRO",
                "TECHM",
            ]
            members = []
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                members.append(basket_member.BasketMember(share))
            it_index = index.Index(
                name="IT",
                members=members,
                weighting="equal",
                base_value=1000,
                base_date="2026-01-01",
            )
            print(f"{it_index.name}: {it_index.level:.2f}")
            ```

            See an index without a base date refuse to give a level:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import exceptions
            from tradingmachine.asset_baskets import index
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HCLTECH",
                "WIPRO",
                "TECHM",
            ]
            members = []
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                members.append(basket_member.BasketMember(share))

            it_index = index.Index(name="IT", members=members, weighting="equal")
            try:
                print(it_index.level)
            except exceptions.AssetBasketError as error:
                print(error)
            ```
        """
        if self.base_date is None:
            raise exceptions.AssetBasketError(
                f"The index {self.name!r} has no base_date, so it has no level; use prices() for a series starting at base_value"
            )
        closes = self.member_closes(
            from_date=self.base_date,
            to_date=self.base_date + datetime.timedelta(days=BASE_DATE_SEARCH_DAYS),
        )
        if closes is None:
            raise exceptions.BasketMemberError(
                f"Not every member of {self.name!r} has a candle within {BASE_DATE_SEARCH_DAYS} days of {self.base_date}"
            )
        quantities = self._candle_quantities(closes.iloc[0])
        last_prices = self._last_prices_by_instrument_id(self.instruments)
        level = 0.0
        for member in self.members:
            level += (
                quantities[member.label] * last_prices[member.instrument.instrument_id]
            )
        return float(level)

    def to_portfolio(
        self, capital: float, name: str | None = None
    ) -> portfolio.Portfolio:
        """Turns the index into whole units of each member for a sum of money, at last prices.

        Each quantity is the capital times the member's weight divided by its last price, floored to a whole unit, so a little of the capital is left over. A member whose share buys less than one unit is left out. Nothing is sent; pass the result to `Portfolio.place_orders` to buy it.

        Args:
            capital: The float amount in rupees to spread across the members.
            name: The str name to give the portfolio, or None to name it after the index.

        Returns:
            A portfolio.Portfolio of the members that get at least one unit.

        Raises:
            BasketMemberError: A member has no last price, or the capital buys no unit of any member.
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.

        Examples:
            Turn one lakh rupees into whole shares of each member:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import index
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HCLTECH",
                "WIPRO",
                "TECHM",
            ]
            members = []
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                members.append(basket_member.BasketMember(share))
            it_index = index.Index(name="IT", members=members, weighting="equal")
            holdings = it_index.to_portfolio(capital=100000)
            print(holdings.quantities)
            print(f"Worth Rs {holdings.value:,.2f} of the Rs 100,000")
            ```

            See a sum too small for one share of anything refused:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import exceptions
            from tradingmachine.asset_baskets import index
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HCLTECH",
                "WIPRO",
                "TECHM",
            ]
            members = []
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                members.append(basket_member.BasketMember(share))

            it_index = index.Index(name="IT", members=members, weighting="equal")
            try:
                it_index.to_portfolio(capital=500, name="too small")
            except exceptions.BasketMemberError as error:
                print(error)
            ```
        """
        weights = self.weights
        last_prices = self._last_prices_by_instrument_id(self.instruments)
        members = []
        for member in self.members:
            last_price = last_prices[member.instrument.instrument_id]
            quantity = math.floor(capital * float(weights[member.label]) / last_price)
            if quantity < 1:
                continue
            members.append(
                basket_member.BasketMember(member.instrument, quantity=quantity)
            )
        if not members:
            raise exceptions.BasketMemberError(
                f"{capital} rupees buys no whole unit of any member of {self.name!r}"
            )
        if name is None:
            name = f"{self.name} portfolio"
        return portfolio.Portfolio(
            name=name,
            members=members,
            unified_broker_interface=self._unified_broker_interface,
        )

    def document(self, effective_date: datetime.date | str | None = None) -> dict:
        """Describes the index as a dict for storing in MongoDB.

        Args:
            effective_date: The first day the index is in effect as a datetime.date or a `YYYY-MM-DD` str, or None for today.

        Returns:
            The dict AssetBasket.document gives, with `weighting` and `base_date` added.

        Raises:
            Nothing.

        Examples:
            Print the index settings a stored index keeps:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import index
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HCLTECH",
                "WIPRO",
                "TECHM",
            ]
            members = []
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                members.append(basket_member.BasketMember(share))
            it_index = index.Index(
                name="IT",
                members=members,
                weighting="equal",
                base_date="2026-01-01",
            )
            document = it_index.document(effective_date="2026-10-01")
            print(document["kind"], document["weighting"], document["base_date"])
            ```

            See that an index without a base date stores None for it:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import index
            from tradingmachine.assets import equities

            symbols = [
                "INFY",
                "TCS",
                "HCLTECH",
                "WIPRO",
                "TECHM",
            ]
            members = []
            for symbol in symbols:
                share = equities.Equity(exchange="nse", symbol=symbol)
                members.append(basket_member.BasketMember(share))
            it_index = index.Index(name="IT", members=members, weighting="price")
            print(it_index.document()["base_date"])
            ```
        """
        document = super().document(effective_date)
        document["weighting"] = self.weighting
        if self.base_date is None:
            document["base_date"] = None
        else:
            document["base_date"] = self.base_date.isoformat()
        return document

    def _candle_quantities(self, first_closes: pd.Series) -> pd.Series:
        """Works out the fixed quantity of each member the index's candles are built from.

        A price weighting holds the same quantity of every member, sized so the first close equals base_value. Any other weighting spreads base_value by weight, as AssetBasket does.

        Args:
            first_closes: A pandas.Series of each member's float close at the first shared candle, indexed by member label.

        Returns:
            A pandas.Series of float quantities indexed by member label.

        Raises:
            BasketMemberError: A stated or price weighting needs a last price that UBI does not have.
        """
        if self.weighting == PRICE_WEIGHTING:
            equal_quantity = self.base_value / first_closes.sum()
            return pd.Series(equal_quantity, index=first_closes.index, dtype=float)
        return super()._candle_quantities(first_closes)
