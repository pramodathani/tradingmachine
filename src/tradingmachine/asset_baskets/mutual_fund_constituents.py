"""What a mutual fund holds, linked to the fund itself.

UBI has no price of any kind for a mutual fund: no quote, no candles and no net asset value history, so `tradingmachine.assets.mutual_funds.MutualFund` cannot measure its own performance and its inherited `sharpe_ratio` returns None. Its holdings can be measured instead, because they are ordinary shares and bonds that UBI does price. `MutualFund.constituents` returns this basket, and every analysis and performance method works on it.

The basket is an estimate of the fund, not the fund. Its weights come from the fund's monthly portfolio disclosure, so they are up to a month old, and the fund's cash, fees and anything else UBI cannot price are left out; `unmapped_weight` records how much of the fund that is. `estimated_day_change_percent` scales the holdings' day move down by that share, which is the usual way to guess today's change in the net asset value before the fund publishes it.

Typical usage example:

  scheme = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")
  holdings = scheme.constituents
  guess = holdings.estimated_day_change_percent
  ratio = holdings.sharpe_ratio(risk_free_rate=0.065, days=365)
"""

from tradingmachine.asset_baskets import asset_basket
from tradingmachine.asset_baskets import basket_member
from tradingmachine.assets import instruments
from tradingmachine.unified_broker_interface import client


class MutualFundConstituents(asset_basket.AssetBasket):
    """The instruments a mutual fund holds, with their weights."""

    KIND = "mutual_fund_constituents"

    def __init__(
        self,
        name: str,
        members: list[basket_member.BasketMember],
        fund: instruments.Instrument | None = None,
        unmapped_weight: float = 0.0,
        unified_broker_interface: client.UnifiedBrokerInterface | None = None,
    ):
        """Initialises the fund's holdings.

        Args:
            name: The str name of the basket, usually the scheme's code, such as `ABSLFTTIDG`.
            members: A list of basket_member.BasketMember, one per holding, each a different instrument, with a weight on every member or on none.
            fund: The tradingmachine.assets.instruments.Instrument of the scheme itself, or None.
            unmapped_weight: The float share of the fund, between 0 and 1, held in things UBI cannot price, such as cash and money market instruments.
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

    @property
    def fund(self) -> instruments.Instrument | None:
        """The tradingmachine.assets.instruments.Instrument of the scheme these are the holdings of, or None when none is linked."""
        return self.linked_instrument

    @property
    def estimated_day_change_percent(self) -> float | None:
        """The float estimated move of the fund's net asset value today, in percent: the holdings' weighted move scaled down by the share UBI cannot price, or None when any holding has no quote, read from UBI on every access."""
        holdings_change = self.day_change_percent
        if holdings_change is None:
            return None
        return holdings_change * (1 - self.unmapped_weight)

    def estimated_net_asset_value(
        self, previous_net_asset_value: float
    ) -> float | None:
        """Estimates today's net asset value from the last published one and the holdings' moves.

        Args:
            previous_net_asset_value: The float net asset value in rupees the fund last published.

        Returns:
            The float estimated net asset value in rupees, or None when any holding has no quote.

        Raises:
            UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        change = self.estimated_day_change_percent
        if change is None:
            return None
        return previous_net_asset_value * (1 + change / 100)
