"""Print the implied volatility smile of Bank Nifty options.

The implied volatility of an option is the volatility at which the pricing model reproduces its market price, and plotted across strikes it usually forms a smile or a skew, with out-of-the-money puts dearer than calls. The program builds the out-of-the-money option at each of nine strikes around the money on the next expiry, a put below the index and a call above it, and prints each strike's implied volatility.

Typical usage example:

  .venv/bin/python examples/assets/instruments/index_option/volatility_smile.py
"""

import datetime

from tradingmachine.assets import equities


class VolatilitySmile:
    """The implied volatility across strikes of one index's options.

    Attributes:
        underlying_symbol: The str symbol of the index.
        strikes_each_side: The int number of strikes to show on each side of the money.
    """

    def __init__(
        self, underlying_symbol: str = "BANKNIFTY", strikes_each_side: int = 4
    ):
        """Stores what to show.

        Args:
            underlying_symbol: The str symbol of an NSE index with options.
            strikes_each_side: The int number of strikes on each side of the money.

        Raises:
            Nothing.
        """
        self.underlying_symbol = underlying_symbol
        self.strikes_each_side = strikes_each_side

    def choose_expiry(self) -> datetime.date:
        """Chooses the first expiry after today.

        Returns:
            The datetime.date of the expiry.

        Raises:
            ValueError: No expiry after today is listed.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        today = datetime.date.today()
        expiries = equities.EquityIndexOption.expiries(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
        )
        for expiry_date in expiries:
            if expiry_date > today:
                return expiry_date
        raise ValueError(f"No expiry after today is listed: {self.underlying_symbol=}")

    def run(self) -> None:
        """Prints one line per strike, lowest first.

        Returns:
            None.

        Raises:
            ValueError: No expiry after today is listed.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        expiry_date = self.choose_expiry()
        index = equities.EquityIndex(exchange="nse", symbol=self.underlying_symbol)
        level = index.last_price
        strikes = equities.EquityIndexOption.strikes(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
        )
        nearest_index = 0
        for position in range(len(strikes)):
            if abs(strikes[position] - level) < abs(strikes[nearest_index] - level):
                nearest_index = position
        first = max(nearest_index - self.strikes_each_side, 0)
        last = nearest_index + self.strikes_each_side + 1
        print(f"{self.underlying_symbol} at {level}, expiry {expiry_date}")
        for strike in strikes[first:last]:
            option_type = "CE"
            if strike < level:
                option_type = "PE"
            option = equities.EquityIndexOption(
                exchange="nse",
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
                strike_price=strike,
                option_type=option_type,
                underlying=index,
            )
            volatility = option.implied_volatility()
            if volatility is None:
                print(f"  {strike:>9.0f} {option_type}  no implied volatility")
            else:
                print(f"  {strike:>9.0f} {option_type}  {volatility * 100:6.2f}%")


if __name__ == "__main__":
    VolatilitySmile().run()
