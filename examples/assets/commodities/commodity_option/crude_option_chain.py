"""Print the crude oil option chain around the price of the future it settles into.

The program lists the CRUDEOIL option expiries on the mcx, reads the chain for the soonest one, finds the future the options are priced off, and prints the calls and puts at the five strikes nearest that future's price with their last prices.

Typical usage example:

  .venv/bin/python examples/assets/commodities/commodity_option/crude_option_chain.py
"""

from tradingmachine.assets import commodities
from tradingmachine.unified_broker_interface import exceptions


class CrudeOptionChain:
    """A slice of one commodity's option chain around the money.

    Attributes:
        underlying_symbol: The str mcx symbol of the commodity, such as `CRUDEOIL`.
        strike_count: The int number of strikes nearest the money to show.
    """

    def __init__(self, underlying_symbol: str = "CRUDEOIL", strike_count: int = 5):
        """Stores the commodity and how many strikes to show.

        Args:
            underlying_symbol: The str mcx symbol of the commodity.
            strike_count: The int number of strikes to show.

        Raises:
            Nothing.
        """
        self.underlying_symbol = underlying_symbol
        self.strike_count = strike_count

    def run(self) -> None:
        """Reads the chain and prints the options nearest the money.

        Returns:
            None.

        Raises:
            tradingmachine.assets.exceptions.CommodityOptionError: A listed option could not be built.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiries = commodities.CommodityOption.expiries(
            exchange="mcx",
            underlying_symbol=self.underlying_symbol,
        )
        if not expiries:
            print(f"No options are listed on {self.underlying_symbol}.")
            return
        expiry_date = expiries[0]
        strikes = commodities.CommodityOption.strikes(
            exchange="mcx",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
        )
        probe = commodities.CommodityOption(
            exchange="mcx",
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
            strike_price=strikes[0],
            option_type="CE",
        )
        future_price = probe.underlying_price
        print(f"{self.underlying_symbol} options expiring {expiry_date}")
        print(f"{len(strikes)} strikes, future at {future_price}")
        by_distance = sorted(strikes, key=lambda strike: abs(strike - future_price))
        option_types = [
            "CE",
            "PE",
        ]
        for strike_price in sorted(by_distance[: self.strike_count]):
            prices = []
            for option_type in option_types:
                option = commodities.CommodityOption(
                    exchange="mcx",
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
    CrudeOptionChain().run()
