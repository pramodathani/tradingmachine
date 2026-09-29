"""Print what UBI can and cannot say about one mutual fund scheme.

The program builds the ABSLFTTIDG scheme and prints its identity, then tries each kind of market data in turn: the live price, which raises `ServiceUnavailableError` because no broker that serves quotes carries mutual funds, the candles, which are None because UBI stores none, and the Sharpe ratio, which is None for the same reason. It ends with this account's holding of the scheme, which is what a mutual fund in UBI is for. It places no order.

Typical usage example:

  .venv/bin/python examples/assets/mutual_funds/mutual_fund/scheme_profile.py
"""

from tradingmachine.assets import mutual_funds
from tradingmachine.unified_broker_interface import exceptions


class SchemeProfile:
    """A profile of one mutual fund scheme.

    Attributes:
        fund: The mutual_funds.MutualFund the profile describes.
    """

    def __init__(self):
        """Looks ABSLFTTIDG up in UBI.

        Raises:
            tradingmachine.assets.exceptions.MutualFundError: UBI has no such scheme.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        self.fund = mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG")

    def run(self) -> None:
        """Prints the identity, the market data checks and the holding.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        print(repr(self.fund))
        print(f"Instrument id: {self.fund.instrument_id}")
        print(f"Segment: {self.fund.segment}")
        print(f"Lot size {self.fund.lot_size}, tick size {self.fund.tick_size}")
        print(f"Carried by: {self.fund.carried_by}")
        print(
            f"First seen {self.fund.first_seen_date}, last seen {self.fund.last_seen_date}"
        )
        self._print_live_price()
        candles = self.fund.prices(days=30)
        print(f"Candles for the last thirty days: {candles}")
        print(f"Sharpe ratio over a year: {self.fund.sharpe_ratio(days=365)}")
        self._print_holding()

    def _print_live_price(self) -> None:
        """Tries to read the scheme's last price and reports why there is none.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI failed in a way other than having no quote.
        """
        try:
            print(f"Last price: {self.fund.last_price}")
        except exceptions.ServiceUnavailableError as error:
            print(f"No live price, as expected for a mutual fund: {error}")

    def _print_holding(self) -> None:
        """Prints this account's holding of the scheme, if any.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        row = self.fund.holdings
        if row is None:
            print("This account holds no units of the scheme.")
            return
        print(f"Held: {row['quantity']} units at an average of {row['average_price']}")
        print(
            f"Worth {self.fund.holdings_value}, profit or loss {self.fund.holdings_pnl}"
        )


if __name__ == "__main__":
    SchemeProfile().run()
