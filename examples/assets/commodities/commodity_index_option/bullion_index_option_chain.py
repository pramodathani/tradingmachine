"""Print the size and shape of the bullion index option chain on the mcx.

The program lists the MCXBULLDEX option expiries and, for each, counts the calls and puts listed and the range of strikes they cover.

Typical usage example:

  .venv/bin/python examples/assets/commodities/commodity_index_option/bullion_index_option_chain.py
"""

from tradingmachine.assets import commodities


class BullionIndexOptionChain:
    """The option chains on one commodity index, one line per expiry and type.

    Attributes:
        underlying_symbol: The str mcx symbol of the index, such as `MCXBULLDEX`.
    """

    def __init__(self, underlying_symbol: str = "MCXBULLDEX"):
        """Stores the index whose chains to describe.

        Args:
            underlying_symbol: The str mcx symbol of the index.

        Raises:
            Nothing.
        """
        self.underlying_symbol = underlying_symbol

    def run(self) -> None:
        """Reads each expiry's chain and prints its summary.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiries = commodities.CommodityIndexOption.expiries(
            exchange="mcx",
            underlying_symbol=self.underlying_symbol,
        )
        if not expiries:
            print(f"No options are listed on {self.underlying_symbol}.")
            return
        option_types = [
            "CE",
            "PE",
        ]
        for expiry_date in expiries:
            chain = commodities.CommodityIndexOption.chain(
                exchange="mcx",
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
            )
            if chain is None:
                print(f"{expiry_date}: empty")
                continue
            for option_type in option_types:
                rows = chain[chain["option_type"] == option_type]
                if rows.empty:
                    continue
                lowest = rows["strike_price"].min()
                highest = rows["strike_price"].max()
                print(
                    f"{expiry_date} {option_type}: {len(rows)} strikes "
                    f"from {lowest} to {highest}"
                )


if __name__ == "__main__":
    BullionIndexOptionChain().run()
