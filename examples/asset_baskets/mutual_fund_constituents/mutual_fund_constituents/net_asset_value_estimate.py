"""Estimate a mutual fund's net asset value today from its holdings' moves.

The program describes a scheme by a few of its disclosed equity holdings with illustrative weights and 20% of the fund in cash and bonds that UBI cannot price, then estimates today's move and today's net asset value from the last published value, and prints what a holding of 2,500 units is worth on that estimate.

Typical usage example:

  .venv/bin/python examples/asset_baskets/mutual_fund_constituents/mutual_fund_constituents/net_asset_value_estimate.py
"""

from tradingmachine.asset_baskets import basket_member
from tradingmachine.asset_baskets import mutual_fund_constituents
from tradingmachine.assets import equities
from tradingmachine.assets import mutual_funds

WEIGHTS = {
    "HDFCBANK": 9.0,
    "ICICIBANK": 7.5,
    "INFY": 6.0,
    "RELIANCE": 5.5,
    "LT": 4.0,
    "ITC": 3.5,
}

UNMAPPED_WEIGHT = 0.2

PREVIOUS_NET_ASSET_VALUE = 45.62

UNITS_HELD = 2500


class NetAssetValueEstimate:
    """An estimate of one scheme's net asset value from its holdings.

    Attributes:
        holdings: The tradingmachine.asset_baskets.mutual_fund_constituents.MutualFundConstituents of the scheme.
    """

    def __init__(self):
        """Looks the scheme and its holdings up in UBI and builds the basket.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know one of the instruments.
        """
        members = []
        for symbol, weight in WEIGHTS.items():
            share = equities.Equity(exchange="nse", symbol=symbol)
            members.append(basket_member.BasketMember(share, weight=weight))
        scheme = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")
        self.holdings = mutual_fund_constituents.MutualFundConstituents(
            name="ABSLFTTIDG",
            members=members,
            fund=scheme,
            unmapped_weight=UNMAPPED_WEIGHT,
        )

    def run(self) -> None:
        """Prints the holdings' move, the estimated move and value, and the units' worth.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        print(
            f"Scheme {self.holdings.fund.symbol}, {self.holdings.size} priced holdings"
        )
        holdings_change = self.holdings.day_change_percent
        estimated_change = self.holdings.estimated_day_change_percent
        if holdings_change is None or estimated_change is None:
            print("A holding has no quote, so no estimate can be made.")
            return
        print(f"Holdings' move today: {holdings_change:+.3f}%")
        print(
            f"Estimated move after {UNMAPPED_WEIGHT:.0%} unpriced: {estimated_change:+.3f}%"
        )
        estimate = self.holdings.estimated_net_asset_value(PREVIOUS_NET_ASSET_VALUE)
        print(
            f"Net asset value: last published {PREVIOUS_NET_ASSET_VALUE}, estimated {estimate:.4f}"
        )
        print(f"{UNITS_HELD:,} units: about Rs {estimate * UNITS_HELD:,.2f}")


if __name__ == "__main__":
    NetAssetValueEstimate().run()
