"""Ask an index basket with no base date for its level and handle the AssetBasketError.

An Index basket's level is its base value moved by its members' prices since its base date, so an index built without a base date has no level and raises AssetBasketError. The program builds an equally weighted index of three shares without a base date, catches the error, and prints the index's weights instead.

Typical usage example:

  .venv/bin/python examples/asset_baskets/exceptions/asset_basket_error/ask_an_index_without_a_base_date_for_its_level.py
"""

from tradingmachine.asset_baskets import basket_member
from tradingmachine.asset_baskets import exceptions
from tradingmachine.asset_baskets import index
from tradingmachine.assets import equities


class IndexLevelCheck:
    """An equally weighted index of three shares with no base date.

    Attributes:
        telecom_index: The tradingmachine.asset_baskets.index.Index of the three shares.
    """

    def __init__(self):
        """Builds the index from IDEA, BHARTIARTL and INDUSTOWER.

        Raises:
            tradingmachine.assets.exceptions.EquityError: UBI does not know one of the shares.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a lookup.
        """
        members = []
        for symbol in [
            "IDEA",
            "BHARTIARTL",
            "INDUSTOWER",
        ]:
            share = equities.Equity(exchange="nse", symbol=symbol)
            members.append(basket_member.BasketMember(share))
        self.telecom_index = index.Index(
            name="Telecom example",
            members=members,
            weighting="equal",
        )

    def run(self) -> None:
        """Asks for the level and prints the weights when there is none.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        try:
            level = self.telecom_index.level
        except exceptions.AssetBasketError as error:
            print(f"AssetBasketError: {error}")
            print("Weights:")
            print(self.telecom_index.weights.to_string())
            return
        print(f"Level: {level}")


if __name__ == "__main__":
    IndexLevelCheck().run()
