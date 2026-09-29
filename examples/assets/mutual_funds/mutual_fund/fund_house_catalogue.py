"""Count the mutual fund schemes UBI carries for several fund houses, and check which of them this account holds.

A scheme's symbol is its exchange code, which starts with a prefix naming the fund house, such as `ABSL`. The program searches for each of a few prefixes, prints how many schemes each returns and the first few codes, and then builds every scheme of the first fund house to see whether this account holds any of it.

Typical usage example:

  .venv/bin/python examples/assets/mutual_funds/mutual_fund/fund_house_catalogue.py
"""

from tradingmachine.assets import mutual_funds


class FundHouseCatalogue:
    """A count of schemes by fund house prefix.

    Attributes:
        prefixes: The list of str fund house prefixes to search for.
        shown_codes: The int number of scheme codes printed for each prefix.
    """

    def __init__(self):
        """Sets the prefixes to search for.

        Raises:
            Nothing.
        """
        self.prefixes = [
            "ABSL",
            "HDFC",
            "SBI",
            "ICICI",
            "AXIS",
            "KOTAK",
        ]
        self.shown_codes = 4

    def run(self) -> None:
        """Prints the count and first codes for each prefix, then the first house's holdings.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        total = 0
        for prefix in self.prefixes:
            matches = mutual_funds.MutualFund.search(
                exchange="nse",
                term=prefix,
                limit=200,
            )
            if matches is None:
                print(f"{prefix:6s} no schemes")
                continue
            total += len(matches)
            first_codes = matches["symbol"].tolist()[: self.shown_codes]
            print(f"{prefix:6s} {len(matches):3d} schemes, such as {first_codes}")
        print(f"Schemes found across these prefixes: {total}")
        self._print_held_schemes(self.prefixes[0])

    def _print_held_schemes(self, prefix: str) -> None:
        """Builds every scheme of one fund house and prints the ones this account holds.

        Args:
            prefix: The str fund house prefix to check.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        matches = mutual_funds.MutualFund.search(
            exchange="nse",
            term=prefix,
            limit=200,
        )
        if matches is None:
            return
        held_count = 0
        for symbol in matches["symbol"]:
            fund = mutual_funds.MutualFund(exchange="nse", symbol=symbol)
            row = fund.holdings
            if row is not None:
                held_count += 1
                print(f"Held: {symbol}, {row['quantity']} units")
        print(f"{held_count} of the {len(matches)} {prefix} schemes are held.")


if __name__ == "__main__":
    FundHouseCatalogue().run()
