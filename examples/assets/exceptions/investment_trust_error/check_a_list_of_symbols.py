"""Check a list of investment trust symbols and report every one UBI does not know.

The program builds a InvestmentTrust for each symbol in a list, as a program reading symbols from a file or a form would. It catches InstrumentError, the base class of every instrument error, so one handler covers InvestmentTrustError and anything else the lookup raises about the instrument, and it prints the chain of errors behind each symbol that was not found.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/investment_trust_error/check_a_list_of_symbols.py
"""

from tradingmachine.assets import funds
from tradingmachine.assets import exceptions


class SymbolListCheck:
    """A check of a list of investment trust symbols against UBI.

    Attributes:
        exchange: The str exchange the symbols are looked up on.
        symbols: The list of str symbols to check.
    """

    def __init__(self):
        """Creates the check with the symbols to look up.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.symbols = [
            "ANANTAM",
            "ANZEN",
            "NOTATRUST",
        ]

    def describe_error_chain(self, error: Exception) -> str:
        """Names an error and every error it was raised from.

        Args:
            error: The Exception to describe.

        Returns:
            A str such as `InvestmentTrustError <- InstrumentError <- NotFoundError`.

        Raises:
            Nothing.
        """
        names = [
            type(error).__name__,
        ]
        cause = error.__cause__
        while cause is not None:
            names.append(type(cause).__name__)
            cause = cause.__cause__
        return " <- ".join(names)

    def check_symbol(self, symbol: str) -> str:
        """Looks one symbol up and describes the outcome.

        Args:
            symbol: The str symbol to look up.

        Returns:
            A str line saying whether UBI knows the symbol, and why not when it does not.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the lookup for a reason other than an unknown symbol.
        """
        try:
            instrument = funds.InvestmentTrust(exchange=self.exchange, symbol=symbol)
        except exceptions.InstrumentError as error:
            chain = self.describe_error_chain(error)
            return f"{symbol}: not found ({chain}): {error}"
        return f"{symbol}: found in {instrument.segment} as {instrument.instrument_id}"

    def run(self) -> None:
        """Checks every symbol and prints one line for each, then a count.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a lookup.
        """
        found_count = 0
        for symbol in self.symbols:
            line = self.check_symbol(symbol)
            print(line)
            if ": found in " in line:
                found_count += 1
        print(f"UBI knows {found_count} of the {len(self.symbols)} symbols.")


if __name__ == "__main__":
    SymbolListCheck().run()
