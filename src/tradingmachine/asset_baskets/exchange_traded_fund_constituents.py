"""What an exchange traded fund holds, linked to the fund itself.

An exchange traded fund is two things. The fund's units trade on the exchange at their own price, which `tradingmachine.assets.funds.ExchangeTradedFund` reads, and the fund holds a basket of other instruments, which this class describes. `ExchangeTradedFund.constituents` returns the stored basket, and the basket's `fund` is the fund again.

Comparing the two says how well the fund does its job. `tracking_difference` is the fund's return minus its holdings' return over a range, which is mostly its fees, and the inherited `tracking_error(benchmark=basket.fund)` is how unevenly it follows them. `premium_or_discount` compares the fund's price now with its indicative net asset value, which the exchange publishes as an index row such as `NIFTYBEES-NAV` when one is stored with the basket.

Typical usage example:

  fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
  holdings = fund.constituents
  gap = holdings.tracking_difference(days=365)
  premium = holdings.premium_or_discount
"""

import datetime

from tradingmachine.asset_baskets import asset_basket
from tradingmachine.asset_baskets import basket_member
from tradingmachine.assets import instruments
from tradingmachine.unified_broker_interface import client


class ExchangeTradedFundConstituents(asset_basket.AssetBasket):
    """The instruments an exchange traded fund holds, with their weights.

    Attributes:
        indicative_net_asset_value: The tradingmachine.assets.instruments.Instrument that carries the fund's indicative net asset value, such as the index row `NIFTYBEES-NAV`, or None when none is known.
    """

    KIND = "exchange_traded_fund_constituents"

    def __init__(
        self,
        name: str,
        members: list[basket_member.BasketMember],
        fund: instruments.Instrument | None = None,
        indicative_net_asset_value: instruments.Instrument | None = None,
        unmapped_weight: float = 0.0,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Initialises the fund's holdings.

        Args:
            name: The str name of the basket, usually the fund's symbol, such as `NIFTYBEES`.
            members: A list of basket_member.BasketMember, one per holding, each a different instrument, with a weight on every member or on none.
            fund: The tradingmachine.assets.instruments.Instrument of the fund itself, or None.
            indicative_net_asset_value: The tradingmachine.assets.instruments.Instrument carrying the fund's indicative net asset value, or None.
            unmapped_weight: The float share of the fund, between 0 and 1, held in things UBI cannot price, such as cash.
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through, or None to share the one every instrument uses.

        Raises:
            BasketMemberError: members is empty, names an instrument twice, or gives weights to only some members.
            ValueError: unmapped_weight is not between 0 and 1.
        """
        super().__init__(
            name=name,
            members=members,
            linked_instrument=fund,
            unmapped_weight=unmapped_weight,
            unified_broker_interface=unified_broker_interface,
        )
        self.indicative_net_asset_value = indicative_net_asset_value

    @property
    def fund(self) -> instruments.Instrument | None:
        """The tradingmachine.assets.instruments.Instrument of the fund these are the holdings of, or None when none is linked.

        Examples:
            Print the fund the holdings belong to and its price:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import exchange_traded_fund_constituents
            from tradingmachine.assets import equities
            from tradingmachine.assets import funds

            weights = {
                "HDFCBANK": 13.0,
                "ICICIBANK": 9.0,
                "RELIANCE": 8.5,
                "INFY": 5.0,
                "BHARTIARTL": 4.5,
            }
            members = []
            for symbol, weight in weights.items():
                share = equities.Equity(exchange="nse", symbol=symbol)
                members.append(basket_member.BasketMember(share, weight=weight))
            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            holdings = exchange_traded_fund_constituents.ExchangeTradedFundConstituents(
                name="NIFTYBEES",
                members=members,
                fund=fund,
            )
            print(holdings.fund.symbol, holdings.fund.last_price)
            ```

            See None when no fund is linked:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import exchange_traded_fund_constituents
            from tradingmachine.assets import equities
            from tradingmachine.assets import funds

            weights = {
                "HDFCBANK": 13.0,
                "ICICIBANK": 9.0,
                "RELIANCE": 8.5,
                "INFY": 5.0,
                "BHARTIARTL": 4.5,
            }
            members = []
            for symbol, weight in weights.items():
                share = equities.Equity(exchange="nse", symbol=symbol)
                members.append(basket_member.BasketMember(share, weight=weight))
            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            holdings = exchange_traded_fund_constituents.ExchangeTradedFundConstituents(
                name="NIFTYBEES",
                members=members,
                fund=fund,
            )
            unlinked = exchange_traded_fund_constituents.ExchangeTradedFundConstituents(
                name="unlinked", members=members
            )
            print(unlinked.fund)
            ```
        """
        return self.linked_instrument

    @property
    def premium_or_discount(self) -> float | None:
        """The float percent by which the fund's last price is above its indicative net asset value, negative for a discount, or None when the fund, the indicative value or either price is missing, read from UBI in one request on every access.

        Examples:
            See None when no indicative net asset value row is stored with the holdings, which is the case for every fund in UBI today:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import exchange_traded_fund_constituents
            from tradingmachine.assets import equities
            from tradingmachine.assets import funds

            weights = {
                "HDFCBANK": 13.0,
                "ICICIBANK": 9.0,
                "RELIANCE": 8.5,
                "INFY": 5.0,
                "BHARTIARTL": 4.5,
            }
            members = []
            for symbol, weight in weights.items():
                share = equities.Equity(exchange="nse", symbol=symbol)
                members.append(basket_member.BasketMember(share, weight=weight))
            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            holdings = exchange_traded_fund_constituents.ExchangeTradedFundConstituents(
                name="NIFTYBEES",
                members=members,
                fund=fund,
            )
            print(holdings.premium_or_discount)
            ```

            Print the premium only when an indicative value is known:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import exchange_traded_fund_constituents
            from tradingmachine.assets import equities
            from tradingmachine.assets import funds

            weights = {
                "HDFCBANK": 13.0,
                "ICICIBANK": 9.0,
                "RELIANCE": 8.5,
                "INFY": 5.0,
                "BHARTIARTL": 4.5,
            }
            members = []
            for symbol, weight in weights.items():
                share = equities.Equity(exchange="nse", symbol=symbol)
                members.append(basket_member.BasketMember(share, weight=weight))
            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            holdings = exchange_traded_fund_constituents.ExchangeTradedFundConstituents(
                name="NIFTYBEES",
                members=members,
                fund=fund,
            )
            premium = holdings.premium_or_discount
            if premium is None:
                print(f"No indicative value is known for {holdings.fund.symbol}.")
            else:
                print(f"{holdings.fund.symbol} trades at {premium:+.2f}% to its value")
            ```
        """
        if self.fund is None or self.indicative_net_asset_value is None:
            return None
        results = self._post_for_instruments(
            asset_basket.LAST_PRICE_PATH,
            [
                self.fund,
                self.indicative_net_asset_value,
            ],
        )
        fund_data = results[0].get("data") or {}
        value_data = results[1].get("data") or {}
        fund_price = fund_data.get("last_price")
        net_asset_value = value_data.get("last_price")
        if fund_price is None or not net_asset_value:
            return None
        return (float(fund_price) / float(net_asset_value) - 1) * 100

    def tracking_difference(
        self,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> float | None:
        """Calculates the fund's return minus its holdings' return over a range.

        A small negative number is normal, since the fund pays fees its holdings do not. The holdings' return is the return of today's weights held through the range, so it drifts from the fund's real history when the holdings changed during it.

        Args:
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The float difference of the two cumulative returns, such as -0.001 for a tenth of a percent behind, or None when no fund is linked or either has too few candles.

        Raises:
            BasketMemberError: UBI answered an error for one or more members.
            UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.

        Examples:
            Print the fund's return minus its holdings' over a year:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import exchange_traded_fund_constituents
            from tradingmachine.assets import equities
            from tradingmachine.assets import funds

            weights = {
                "HDFCBANK": 13.0,
                "ICICIBANK": 9.0,
                "RELIANCE": 8.5,
                "INFY": 5.0,
                "BHARTIARTL": 4.5,
            }
            members = []
            for symbol, weight in weights.items():
                share = equities.Equity(exchange="nse", symbol=symbol)
                members.append(basket_member.BasketMember(share, weight=weight))
            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            holdings = exchange_traded_fund_constituents.ExchangeTradedFundConstituents(
                name="NIFTYBEES",
                members=members,
                fund=fund,
            )
            difference = holdings.tracking_difference(days=365)
            print(f"Tracking difference: {difference:+.4f}")
            ```

            Compare the tracking difference over three months and one year:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import exchange_traded_fund_constituents
            from tradingmachine.assets import equities
            from tradingmachine.assets import funds

            weights = {
                "HDFCBANK": 13.0,
                "ICICIBANK": 9.0,
                "RELIANCE": 8.5,
                "INFY": 5.0,
                "BHARTIARTL": 4.5,
            }
            members = []
            for symbol, weight in weights.items():
                share = equities.Equity(exchange="nse", symbol=symbol)
                members.append(basket_member.BasketMember(share, weight=weight))
            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            holdings = exchange_traded_fund_constituents.ExchangeTradedFundConstituents(
                name="NIFTYBEES",
                members=members,
                fund=fund,
            )
            for days in [
                90,
                365,
            ]:
                print(days, holdings.tracking_difference(days=days))
            ```
        """
        if self.fund is None:
            return None
        fund_return = self.fund.cumulative_return(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        holdings_return = self.cumulative_return(
            interval=interval,
            from_date=from_date,
            to_date=to_date,
            days=days,
            adjusted=adjusted,
        )
        if fund_return is None or holdings_return is None:
            return None
        return fund_return - holdings_return

    def document(self, effective_date: datetime.date | str | None = None) -> dict:
        """Describes the fund's holdings as a dict for storing in MongoDB.

        Args:
            effective_date: The first day the holdings are in effect as a datetime.date or a `YYYY-MM-DD` str, or None for today.

        Returns:
            The dict AssetBasket.document gives, with `indicative_net_asset_value_instrument_id` added.

        Raises:
            Nothing.

        Examples:
            Print the stored form's link to the fund and its indicative value:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import exchange_traded_fund_constituents
            from tradingmachine.assets import equities
            from tradingmachine.assets import funds

            weights = {
                "HDFCBANK": 13.0,
                "ICICIBANK": 9.0,
                "RELIANCE": 8.5,
                "INFY": 5.0,
                "BHARTIARTL": 4.5,
            }
            members = []
            for symbol, weight in weights.items():
                share = equities.Equity(exchange="nse", symbol=symbol)
                members.append(basket_member.BasketMember(share, weight=weight))
            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            holdings = exchange_traded_fund_constituents.ExchangeTradedFundConstituents(
                name="NIFTYBEES",
                members=members,
                fund=fund,
            )
            document = holdings.document(effective_date="2026-09-01")
            print(document["kind"], document["linked_instrument_id"])
            print(document["indicative_net_asset_value_instrument_id"])
            ```

            Print the stored weight of each holding:

            ```python
            from tradingmachine.asset_baskets import basket_member
            from tradingmachine.asset_baskets import exchange_traded_fund_constituents
            from tradingmachine.assets import equities
            from tradingmachine.assets import funds

            weights = {
                "HDFCBANK": 13.0,
                "ICICIBANK": 9.0,
                "RELIANCE": 8.5,
                "INFY": 5.0,
                "BHARTIARTL": 4.5,
            }
            members = []
            for symbol, weight in weights.items():
                share = equities.Equity(exchange="nse", symbol=symbol)
                members.append(basket_member.BasketMember(share, weight=weight))
            fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
            holdings = exchange_traded_fund_constituents.ExchangeTradedFundConstituents(
                name="NIFTYBEES",
                members=members,
                fund=fund,
            )
            for member_document in holdings.document()["members"]:
                print(member_document["symbol"], member_document["weight"])
            ```
        """
        document = super().document(effective_date)
        if self.indicative_net_asset_value is None:
            document["indicative_net_asset_value_instrument_id"] = None
        else:
            document["indicative_net_asset_value_instrument_id"] = (
                self.indicative_net_asset_value.instrument_id
            )
        return document
