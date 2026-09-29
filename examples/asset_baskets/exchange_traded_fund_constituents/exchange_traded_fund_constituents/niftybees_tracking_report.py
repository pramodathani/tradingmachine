"""Measure how closely the NIFTYBEES fund follows its largest holdings.

The program describes NIFTYBEES by its ten largest holdings with approximate weights, links them to the fund itself, and prints over three months and a year the fund's return minus the holdings' return, the tracking error between the two, and today's moves of the fund and of the holdings side by side. The weights are an illustration rather than the fund's published portfolio, so the numbers show how the measures work rather than how good the fund is.

Typical usage example:

  .venv/bin/python examples/asset_baskets/exchange_traded_fund_constituents/exchange_traded_fund_constituents/niftybees_tracking_report.py
"""

from tradingmachine.asset_baskets import basket_member
from tradingmachine.asset_baskets import exchange_traded_fund_constituents
from tradingmachine.assets import equities
from tradingmachine.assets import funds

WEIGHTS = {
    "HDFCBANK": 13.0,
    "ICICIBANK": 9.0,
    "RELIANCE": 8.5,
    "INFY": 5.0,
    "BHARTIARTL": 4.5,
    "LT": 4.0,
    "ITC": 3.5,
    "TCS": 3.0,
    "SBIN": 3.0,
    "AXISBANK": 3.0,
}

RANGES_IN_DAYS = [
    90,
    365,
]


class NiftybeesTrackingReport:
    """A tracking report on NIFTYBEES against a basket of its largest holdings.

    Attributes:
        holdings: The tradingmachine.asset_baskets.exchange_traded_fund_constituents.ExchangeTradedFundConstituents linked to NIFTYBEES.
    """

    def __init__(self):
        """Looks the fund and its holdings up in UBI and builds the basket.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know one of the instruments.
        """
        members = []
        for symbol, weight in WEIGHTS.items():
            share = equities.Equity(exchange="nse", symbol=symbol)
            members.append(basket_member.BasketMember(share, weight=weight))
        fund = funds.ExchangeTradedFund(exchange="nse", symbol="NIFTYBEES")
        self.holdings = (
            exchange_traded_fund_constituents.ExchangeTradedFundConstituents(
                name="NIFTYBEES top ten",
                members=members,
                fund=fund,
            )
        )

    def run(self) -> None:
        """Prints the tracking measures for each range and today's moves.

        Returns:
            None.

        Raises:
            tradingmachine.asset_baskets.exceptions.BasketMemberError: UBI answered an error for a holding's candles.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        fund = self.holdings.fund
        print(f"{fund.symbol} against {self.holdings.size} holdings")
        for days in RANGES_IN_DAYS:
            difference = self.holdings.tracking_difference(days=days)
            error = fund.tracking_error(benchmark=self.holdings, days=days)
            print(
                f"{days} days: tracking difference {difference:+.2%}, tracking error {error:.2%}"
            )
        print(f"Fund's last price: {fund.last_price}")
        print(f"Holdings today: {self.holdings.day_change_percent:+.2f}%")
        print(f"Premium to indicative value: {self.holdings.premium_or_discount}")


if __name__ == "__main__":
    NiftybeesTrackingReport().run()
