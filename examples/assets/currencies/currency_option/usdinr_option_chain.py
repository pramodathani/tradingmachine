"""Print the dollar-rupee option chain around the money.

The program reads the USDINR option chain on the nse for the soonest expiry after today, finds the future the options are priced off, and prints the calls and puts at the five strikes nearest that future's rate with their last prices.

Typical usage example:

  .venv/bin/python examples/assets/currencies/currency_option/usdinr_option_chain.py
"""

import datetime

from tradingmachine.assets import currencies
from tradingmachine.unified_broker_interface import exceptions


class DollarRupeeOptionChain:
    """A slice of one currency pair's option chain around the money.

    Attributes:
        underlying_symbol: The str symbol of the pair, such as `USDINR`.
        strike_count: The int number of strikes nearest the money to show.
    """

    def __init__(self, underlying_symbol: str = "USDINR", strike_count: int = 5):
        """Stores the pair and how many strikes to show.

        Args:
            underlying_symbol: The str symbol of the pair.
            strike_count: The int number of strikes to show.

        Raises:
            Nothing.
        """
        self.underlying_symbol = underlying_symbol
        self.strike_count = strike_count

    def next_expiry(self) -> datetime.date | None:
        """Chooses the soonest option expiry after today.

        Returns:
            The datetime.date of the expiry, or None when no option is listed.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        expiries = currencies.CurrencyOption.expiries(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
        )
        if not expiries:
            return None
        today = datetime.date.today()
        for expiry in expiries:
            if expiry > today:
                return expiry
        return expiries[0]

    def run(self) -> None:
        """Reads the chain and prints the options nearest the money.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.CurrencyOptionError: A listed option could not be built.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiry_date = self.next_expiry()
        if expiry_date is None:
            print(f"No options are listed on {self.underlying_symbol}.")
            return
        strikes = currencies.CurrencyOption.strikes(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
        )
        probe = currencies.CurrencyOption(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
            strike_price=strikes[0],
            option_type="CE",
        )
        future_rate = probe.underlying_price
        print(f"{self.underlying_symbol} options expiring {expiry_date}")
        print(f"{len(strikes)} strikes, future at {future_rate}")
        by_distance = sorted(strikes, key=lambda strike: abs(strike - future_rate))
        option_types = [
            "CE",
            "PE",
        ]
        for strike_price in sorted(by_distance[: self.strike_count]):
            prices = []
            for option_type in option_types:
                option = currencies.CurrencyOption(
                    exchange="nse",
                    underlying_symbol=self.underlying_symbol,
                    expiry_date=expiry_date,
                    strike_price=strike_price,
                    option_type=option_type,
                )
                try:
                    prices.append(f"{option_type} {option.last_price}")
                except exceptions.ServiceUnavailableError:
                    prices.append(f"{option_type} no quote")
            print(f"{strike_price}: {', '.join(prices)}")


if __name__ == "__main__":
    DollarRupeeOptionChain().run()
