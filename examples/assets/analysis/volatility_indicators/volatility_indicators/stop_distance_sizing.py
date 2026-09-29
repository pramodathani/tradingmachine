"""Size a hypothetical position so that a stop two average true ranges away risks a fixed amount.

The program reads each share's 14-day average true range, sets a stop two average true ranges below the latest close, rounded to the share's 0.01 rupee tick, and works out how many shares a trader could buy so that being stopped out loses no more than the chosen amount. It only calculates and places no orders.

Typical usage example:

  .venv/bin/python examples/assets/analysis/volatility_indicators/volatility_indicators/stop_distance_sizing.py
"""

import math

from tradingmachine.assets import equities


class StopDistanceSizing:
    """A position size calculator driven by the average true range.

    Attributes:
        symbols: A list of str NSE symbols of the shares that are sized.
        risk_amount: The float rupees the trader accepts losing if the stop is hit.
        multiple: The float number of average true ranges between the close and the stop.
    """

    def __init__(self, risk_amount: float = 5000.0, multiple: float = 2.0):
        """Creates the calculator over three NSE shares.

        Args:
            risk_amount: The float rupees the trader accepts losing if the stop is hit.
            multiple: The float number of average true ranges between the close and the stop.

        Raises:
            Nothing.
        """
        self.symbols = [
            "IDEA",
            "INFY",
            "RELIANCE",
        ]
        self.risk_amount = risk_amount
        self.multiple = multiple

    def size(self, symbol: str) -> str:
        """Works out the stop and the position size for one share.

        Args:
            symbol: The str NSE symbol of the share.

        Returns:
            A str line with the close, the average true range, the stop level and the number of shares.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know the share.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        share = equities.Equity(exchange="nse", symbol=symbol)
        frame = share.average_true_range(window=14, days=90)
        if frame is None:
            return f"{symbol}: no candles"
        close = frame["close"].iloc[-1]
        average_true_range = frame["atr_14"].iloc[-1]
        stop_level = round(close - self.multiple * average_true_range, 2)
        risk_per_share = close - stop_level
        quantity = math.floor(self.risk_amount / risk_per_share)
        return (
            f"{symbol:<10} close {close:>9.2f}  ATR {average_true_range:>7.2f}  "
            f"stop {stop_level:>9.2f}  buy {quantity} shares"
        )

    def run(self) -> None:
        """Prints the stop and the position size for every share.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know one of the shares.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        print(
            f"Risking Rs {self.risk_amount:.0f} with a stop {self.multiple} ATRs below the close:"
        )
        for symbol in self.symbols:
            print(self.size(symbol))


if __name__ == "__main__":
    StopDistanceSizing().run()
