"""Print the Nifty options around the money with their premiums and deltas.

The program reads the Nifty option chain for the soonest expiry after today, keeps the five strikes nearest the index, and prints the call and the put at each with its last price, implied volatility and delta.

Typical usage example:

  .venv/bin/python examples/assets/equities/equity_index_option/nifty_option_chain_greeks.py
"""

import datetime

from tradingmachine.assets import equities


class NiftyOptionChainGreeks:
    """A slice of the Nifty option chain around the money, with greeks.

    Attributes:
        index: The tradingmachine.assets.equities.EquityIndex the options are written on.
        strike_count: The int number of strikes to show.
    """

    def __init__(self, strike_count: int = 5):
        """Looks the Nifty 50 up in UBI.

        Args:
            strike_count: The int number of strikes nearest the index to show.

        Raises:
            tradingmachine.assets.exceptions.EquityIndexError: UBI has no Nifty 50 index.
        """
        self.index = equities.EquityIndex(exchange="nse", symbol="NIFTY")
        self.strike_count = strike_count

    def next_expiry(self) -> datetime.date:
        """Chooses the soonest option expiry after today.

        Returns:
            The datetime.date of the expiry.

        Raises:
            ValueError: No options are listed on the index.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        expiries = equities.EquityIndexOption.expiries(
            exchange="nse",
            underlying_symbol="NIFTY",
        )
        if not expiries:
            raise ValueError("No options are listed on the Nifty")
        today = datetime.date.today()
        for expiry in expiries:
            if expiry > today:
                return expiry
        return expiries[0]

    def strikes_near_the_money(self, expiry_date: datetime.date) -> list[float]:
        """Keeps the listed strikes closest to the index's level.

        Args:
            expiry_date: The datetime.date of the expiry.

        Returns:
            A list of float strike prices, lowest first.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        level = self.index.last_price
        strikes = equities.EquityIndexOption.strikes(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=expiry_date,
        )
        by_distance = sorted(strikes, key=lambda strike: abs(strike - level))
        return sorted(by_distance[: self.strike_count])

    def run(self) -> None:
        """Builds each option near the money and prints its line.

        Returns:
            None.

        Raises:
            ValueError: No options are listed on the index.
            tradingmachine.assets.exceptions.EquityIndexOptionError: UBI has no such option.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiry_date = self.next_expiry()
        print(f"Nifty at {self.index.last_price}, options expiring {expiry_date}")
        option_types = [
            "CE",
            "PE",
        ]
        for strike_price in self.strikes_near_the_money(expiry_date):
            for option_type in option_types:
                option = equities.EquityIndexOption(
                    exchange="nse",
                    underlying_symbol="NIFTY",
                    expiry_date=expiry_date,
                    strike_price=strike_price,
                    option_type=option_type,
                    underlying=self.index,
                )
                greeks = option.greeks()
                if greeks is None:
                    print(f"{strike_price} {option_type}: no greeks")
                    continue
                print(
                    f"{strike_price} {option_type}: "
                    f"premium {option.last_price}, "
                    f"volatility {greeks['volatility']:.1%}, "
                    f"delta {greeks['delta']:.2f}"
                )


if __name__ == "__main__":
    NiftyOptionChainGreeks().run()
