"""Print the greeks of the Nifty options nearest the money.

The program finds the at-the-money strike of the next Nifty option expiry, builds the call and the put at that strike and two strikes either side of it, and prints each option's premium, moneyness, implied volatility, delta, theta and vega.

Typical usage example:

  .venv/bin/python examples/assets/instruments/option/option_chain_greeks.py
"""

import datetime

from tradingmachine.assets import equities


class OptionChainGreeks:
    """A table of greeks for the strikes around the money on one expiry.

    Attributes:
        underlying_symbol: The str symbol of the index.
        strikes_each_side: The int number of strikes to show on each side of the money.
        expiry_date: The datetime.date of the expiry shown, chosen when the program runs.
    """

    def __init__(self, underlying_symbol: str = "NIFTY", strikes_each_side: int = 2):
        """Stores what to show.

        Args:
            underlying_symbol: The str symbol of an NSE index with options.
            strikes_each_side: The int number of strikes to show on each side of the money.

        Raises:
            Nothing.
        """
        self.underlying_symbol = underlying_symbol
        self.strikes_each_side = strikes_each_side
        self.expiry_date = None

    def choose_expiry(self) -> datetime.date:
        """Chooses the first expiry after today, so the options still have time left.

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

    def strikes_around_the_money(self, level: float) -> list[float]:
        """Picks the strikes nearest the index level.

        Args:
            level: The float level of the index.

        Returns:
            A list of float strikes, lowest first.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused the request or could not be reached.
        """
        strikes = equities.EquityIndexOption.strikes(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
            expiry_date=self.expiry_date,
        )
        nearest_index = 0
        for index in range(len(strikes)):
            if abs(strikes[index] - level) < abs(strikes[nearest_index] - level):
                nearest_index = index
        first = max(nearest_index - self.strikes_each_side, 0)
        last = nearest_index + self.strikes_each_side + 1
        return strikes[first:last]

    def print_option(self, option: equities.EquityIndexOption) -> None:
        """Prints one line of the table for one option.

        Args:
            option: The tradingmachine.assets.equities.EquityIndexOption to describe.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        greeks = option.greeks()
        if greeks is None:
            print(f"{option.strike_price:>9.0f} {option.option_type}  no greeks")
            return
        print(
            f"{option.strike_price:>9.0f} {option.option_type} "
            f"{option.last_price:>9.2f} {option.moneyness_percent:>+8.2f}% "
            f"{greeks['volatility'] * 100:>7.2f}% {greeks['delta']:>7.3f} "
            f"{greeks['theta']:>8.2f} {greeks['vega']:>7.2f}"
        )

    def run(self) -> None:
        """Prints the table.

        Returns:
            None.

        Raises:
            ValueError: No expiry after today is listed.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI refused a request or could not be reached.
        """
        self.expiry_date = self.choose_expiry()
        index = equities.EquityIndex(exchange="nse", symbol=self.underlying_symbol)
        level = index.last_price
        print(f"{self.underlying_symbol} at {level}, expiry {self.expiry_date}")
        print(
            f"{'Strike':>9} {'Type':<3} {'Premium':>8} {'Money':>9} "
            f"{'IV':>8} {'Delta':>7} {'Theta':>8} {'Vega':>7}"
        )
        for strike in self.strikes_around_the_money(level):
            for option_type in [
                "CE",
                "PE",
            ]:
                option = equities.EquityIndexOption(
                    exchange="nse",
                    underlying_symbol=self.underlying_symbol,
                    expiry_date=self.expiry_date,
                    strike_price=strike,
                    option_type=option_type,
                    underlying=index,
                )
                self.print_option(option)


if __name__ == "__main__":
    OptionChainGreeks().run()
