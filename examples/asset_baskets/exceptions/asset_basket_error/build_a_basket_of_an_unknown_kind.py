"""Build a basket from a document naming a kind the store does not know, and handle the AssetBasketError.

BasketStore.build turns a stored document into the basket class its `kind` names, such as `index` or `watchlist`. The program gives it a document whose kind is `collection`, catches the AssetBasketError, and builds the same members as a watchlist instead. Nothing is saved to MongoDB.

Typical usage example:

  .venv/bin/python examples/asset_baskets/exceptions/asset_basket_error/build_a_basket_of_an_unknown_kind.py
"""

from tradingmachine.asset_baskets import asset_basket
from tradingmachine.asset_baskets import basket_store
from tradingmachine.asset_baskets import exceptions


class UnknownKindBuild:
    """A basket document whose kind the store does not know.

    Attributes:
        store: The tradingmachine.asset_baskets.basket_store.BasketStore that builds the basket.
        document: The dict basket document to build.
    """

    def __init__(self):
        """Creates the store and the document.

        Raises:
            ValueError: The shared client is not configured.
        """
        self.store = basket_store.BasketStore()
        self.document = {
            "name": "Telecom example",
            "kind": "collection",
            "members": [
                {
                    "exchange": "nse",
                    "segment": "equities",
                    "symbol": "IDEA",
                },
                {
                    "exchange": "nse",
                    "segment": "equities",
                    "symbol": "BHARTIARTL",
                },
            ],
        }

    def build(self) -> asset_basket.AssetBasket:
        """Builds the document, falling back to a watchlist when its kind is unknown.

        Returns:
            The tradingmachine.asset_baskets.asset_basket.AssetBasket built.

        Raises:
            tradingmachine.asset_baskets.exceptions.BasketMemberError: UBI could not find one of the members.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        try:
            return self.store.build(self.document)
        except exceptions.AssetBasketError as error:
            print(f"AssetBasketError: {error}")
        self.document["kind"] = "watchlist"
        return self.store.build(self.document)

    def run(self) -> None:
        """Builds the basket and prints its class and members.

        Returns:
            None.

        Raises:
            tradingmachine.asset_baskets.exceptions.BasketMemberError: UBI could not find one of the members.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        basket = self.build()
        print(f"Built {basket!r}")
        for label in basket.labels:
            print(f"  {label}")


if __name__ == "__main__":
    UnknownKindBuild().run()
