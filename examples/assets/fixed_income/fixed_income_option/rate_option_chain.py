"""Print the option chain on an interest rate underlying.

The program lists the option expiries on the 6.33 per cent government security of 2035, reads the chain for the soonest one, and prints how many calls and puts are listed and the range of strikes each covers.

Typical usage example:

  .venv/bin/python examples/assets/fixed_income/fixed_income_option/rate_option_chain.py
"""

from tradingmachine.assets import fixed_income


class RateOptionChain:
    """The option chain on one interest rate underlying for its soonest expiry.

    Attributes:
        underlying_symbol: The str rate code of the security, such as `633GS2035`.
    """

    def __init__(self, underlying_symbol: str = "633GS2035"):
        """Stores the security whose chain to print.

        Args:
            underlying_symbol: The str rate code of the security.

        Raises:
            Nothing.
        """
        self.underlying_symbol = underlying_symbol

    def run(self) -> None:
        """Reads the chain and prints one line per option type.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiries = fixed_income.FixedIncomeOption.expiries(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
        )
        if not expiries:
            print(f"No options are listed on {self.underlying_symbol}.")
            return
        listed = []
        for expiry in expiries:
            listed.append(expiry.isoformat())
        print(f"Option expiries on {self.underlying_symbol}: {', '.join(listed)}")
        chain = fixed_income.FixedIncomeOption.chain(
            exchange="nse",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiries[0],
        )
        if chain is None:
            print("The chain is empty.")
            return
        print(f"{len(chain)} options expiring {expiries[0]}")
        option_types = [
            "CE",
            "PE",
        ]
        for option_type in option_types:
            rows = chain[chain["option_type"] == option_type]
            if rows.empty:
                print(f"{option_type}: none listed")
                continue
            lowest = rows["strike_price"].min()
            highest = rows["strike_price"].max()
            print(f"{option_type}: {len(rows)} strikes from {lowest} to {highest}")


if __name__ == "__main__":
    RateOptionChain().run()
