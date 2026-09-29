"""Report whether money is flowing into or out of a few shares.

The program reads three months of daily candles for Infosys, Reliance Industries and State Bank of India, and for each prints the last five sessions of the Chaikin accumulation distribution line and the Chaikin oscillator, with a verdict of buying or selling pressure from the oscillator's sign.

Typical usage example:

  .venv/bin/python examples/assets/analysis/volume_indicators/volume_indicators/accumulation_distribution_report.py
"""

from tradingmachine.assets import equities


class AccumulationDistributionReport:
    """A report of the Chaikin money flow measures of several shares.

    Attributes:
        shares: A list of tradingmachine.assets.equities.Equity objects to report on.
        days: The int number of days of candles to read.
    """

    def __init__(self, days: int = 90):
        """Creates the report over three NSE shares.

        Args:
            days: The int number of days of candles to read.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know one of the shares.
        """
        symbols = [
            "INFY",
            "RELIANCE",
            "SBIN",
        ]
        self.shares = []
        for symbol in symbols:
            self.shares.append(equities.Equity(exchange="nse", symbol=symbol))
        self.days = days

    def report_share(self, share: equities.Equity) -> None:
        """Prints one share's last five sessions and its verdict.

        Args:
            share: The tradingmachine.assets.equities.Equity to report on.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        line = share.chaikin_accumulation_distribution_line(days=self.days)
        oscillator = share.chaikin_accumulation_distribution_oscillator(days=self.days)
        if line is None or oscillator is None:
            print(f"{share.symbol}: no candles")
            return
        line["chaikin_adosc3_10"] = oscillator["chaikin_adosc3_10"]
        print(f"{share.symbol}:")
        print(
            line[["datetime", "close", "chaikin_ad", "chaikin_adosc3_10"]]
            .tail()
            .to_string(index=False)
        )
        if oscillator["chaikin_adosc3_10"].iloc[-1] > 0:
            print("Verdict: buying pressure")
        else:
            print("Verdict: selling pressure")
        print()

    def run(self) -> None:
        """Prints the report for every share.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        for share in self.shares:
            self.report_share(share)


if __name__ == "__main__":
    AccumulationDistributionReport().run()
