"""Measure a mutual fund's risk through its holdings, since the fund itself has no prices in UBI.

The program shows that the scheme has no candles of its own, then describes it by a few of its disclosed holdings with illustrative weights and prints the holdings' performance summary over a year against the NIFTY index, and the correlation between the holdings.

Typical usage example:

  .venv/bin/python examples/asset_baskets/mutual_fund_constituents/mutual_fund_constituents/holdings_risk_report.py
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
}

DAYS = 365

RISK_FREE_RATE = 0.065


class HoldingsRiskReport:
    """A year's risk report on a scheme, measured through its holdings.

    Attributes:
        holdings: The tradingmachine.asset_baskets.mutual_fund_constituents.MutualFundConstituents of the scheme.
        nifty: The tradingmachine.assets.equities.EquityIndex for NIFTY, the benchmark.
    """

    def __init__(self):
        """Looks the scheme, its holdings and the benchmark up in UBI.

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
            unmapped_weight=0.1,
        )
        self.nifty = equities.EquityIndex(exchange="nse", symbol="NIFTY")

    def run(self) -> None:
        """Prints the scheme's own lack of candles and the holdings' measures.

        Returns:
            None.

        Raises:
            tradingmachine.asset_baskets.exceptions.BasketMemberError: UBI answered an error for a holding's candles.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        print(f"The scheme's own candles: {self.holdings.fund.prices(days=DAYS)}")
        summary = self.holdings.performance_summary(
            benchmark=self.nifty,
            risk_free_rate=RISK_FREE_RATE,
            days=DAYS,
        )
        print("The holdings over a year against NIFTY:")
        print(summary.round(4))
        print()
        print(self.holdings.correlation_matrix(days=DAYS).round(2))


if __name__ == "__main__":
    HoldingsRiskReport().run()
