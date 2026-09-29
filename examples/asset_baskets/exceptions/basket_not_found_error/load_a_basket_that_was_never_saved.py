"""Load a basket that was never saved and handle the BasketNotFoundError.

The program asks the basket store in MongoDB for a basket name nobody has saved, catches BasketNotFoundError, and prints the names that are stored instead.

Typical usage example:

  .venv/bin/python examples/asset_baskets/exceptions/basket_not_found_error/load_a_basket_that_was_never_saved.py
"""

from tradingmachine.asset_baskets import basket_store
from tradingmachine.asset_baskets import exceptions


class MissingBasketLoad:
    """A load of a basket name that was never saved.

    Attributes:
        store: The tradingmachine.asset_baskets.basket_store.BasketStore to load from.
        name: The str basket name, which nobody has saved.
    """

    def __init__(self):
        """Creates the store and the name to load.

        Raises:
            ValueError: The shared client is not configured.
        """
        self.store = basket_store.BasketStore()
        self.name = "Never saved example basket"

    def run(self) -> None:
        """Loads the basket and prints the stored names when it is not found.

        Returns:
            None.

        Raises:
            pymongo.errors.PyMongoError: MongoDB could not be reached.
            tradingmachine.asset_baskets.exceptions.AssetBasketError: The stored basket could not be rebuilt.
        """
        try:
            basket = self.store.load(self.name)
        except exceptions.BasketNotFoundError as error:
            print(f"BasketNotFoundError: {error}")
            stored_names = self.store.names()
            if not stored_names:
                print("No basket is stored at all.")
            else:
                print(f"Stored baskets: {stored_names}")
            return
        print(f"Loaded {basket!r}")


if __name__ == "__main__":
    MissingBasketLoad().run()
