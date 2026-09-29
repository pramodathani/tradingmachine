"""Print today's move of every nse sector index whose name matches a word.

The program searches the nse's equity indices for a word, builds each index it finds, and prints its level and its change since the previous close, largest rise first.

Typical usage example:

  .venv/bin/python examples/assets/equities/equity_index/sector_index_levels.py
"""

from tradingmachine.assets import equities


class SectorIndexLevels:
    """Today's moves of the indices whose symbols contain one word.

    Attributes:
        term: The str the index symbols must contain, such as `BANK`.
    """

    def __init__(self, term: str = "BANK"):
        """Stores the word to search for.

        Args:
            term: The str the index symbols must contain.

        Raises:
            Nothing.
        """
        self.term = term

    def run(self) -> None:
        """Searches, reads each index's quote and prints the moves in order.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.EquityIndexError: A matching index could not be built.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        matches = equities.EquityIndex.search(exchange="nse", term=self.term)
        if matches is None:
            print(f"No nse index contains {self.term}.")
            return
        moves = []
        for symbol in matches["symbol"]:
            index = equities.EquityIndex(exchange="nse", symbol=symbol)
            quote = index.quote
            moves.append((quote["change_percent"], symbol, quote["last_price"]))
        moves.sort(reverse=True)
        for change_percent, symbol, level in moves:
            print(f"{symbol:<20} {level:>12} {change_percent:>7}%")


if __name__ == "__main__":
    SectorIndexLevels().run()
