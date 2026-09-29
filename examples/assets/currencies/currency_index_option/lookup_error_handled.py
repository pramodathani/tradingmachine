"""Try to build a currency index option and handle the error UBI gives today.

UBI holds no rows in its currency index options segment, so every lookup fails with CurrencyIndexOptionError. The program borrows a real expiry and strike from the USDINR option chain, asks for a currency index option with them, catches the error, and prints it.

Typical usage example:

  .venv/bin/python examples/assets/currencies/currency_index_option/lookup_error_handled.py
"""

from tradingmachine.assets import currencies
from tradingmachine.assets import exceptions


class CurrencyIndexOptionLookup:
    """An attempt to build one currency index option.

    Attributes:
        underlying_symbol: The str symbol of the index, such as `USDINR`.
    """

    def __init__(self, underlying_symbol: str = "USDINR"):
        """Stores the index whose option to look for.

        Args:
            underlying_symbol: The str symbol of the index.

        Raises:
            Nothing.
        """
        self.underlying_symbol = underlying_symbol

    def run(self) -> None:
        """Tries to build the option and prints either the option or the error.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        pair_expiries = currencies.CurrencyOption.expiries(
            exchange="nse",
            underlying_symbol="USDINR",
        )
        if not pair_expiries:
            print("No USDINR options are listed to borrow an expiry from.")
            return
        strikes = currencies.CurrencyOption.strikes(
            exchange="nse",
            underlying_symbol="USDINR",
            expiry_date=pair_expiries[0],
        )
        strike_price = strikes[len(strikes) // 2]
        try:
            option = currencies.CurrencyIndexOption(
                exchange="nse",
                underlying_symbol=self.underlying_symbol,
                expiry_date=pair_expiries[0],
                strike_price=strike_price,
                option_type="CE",
            )
        except exceptions.CurrencyIndexOptionError as error:
            print(f"Not available today: {error}")
            return
        print(f"Found {option.underlying_symbol} {option.strike_price} CE")
        print(f"Premium: {option.last_price}")


if __name__ == "__main__":
    CurrencyIndexOptionLookup().run()
