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
        """The tradingmachine.assets.instruments.Instrument of the fund these are the holdings of, or None when none is linked."""
        return self.linked_instrument

    @property
    def premium_or_discount(self) -> float | None:
        """The float percent by which the fund's last price is above its indicative net asset value, negative for a discount, or None when the fund, the indicative value or either price is missing, read from UBI in one request on every access."""
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
        """
        document = super().document(effective_date)
        if self.indicative_net_asset_value is None:
            document["indicative_net_asset_value_instrument_id"] = None
        else:
            document["indicative_net_asset_value_instrument_id"] = (
                self.indicative_net_asset_value.instrument_id
            )
        return document
