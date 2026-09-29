"""Load a basket as of a day before any version took effect, catching AssetBasketError.

Every stored basket version has an effective date, and a basket asked for as of an earlier day is not found. The program asks for the NIFTY basket as of 1 January 1990, catches the BasketNotFoundError through its base class AssetBasketError, and then reads the basket's version history, which is None when no version is stored at all.

Typical usage example:

  .venv/bin/python examples/asset_baskets/exceptions/basket_not_found_error/load_a_basket_before_it_took_effect.py
"""

from tradingmachine.asset_baskets import basket_store
from tradingmachine.asset_baskets import exceptions


class EarlyBasketLoad:
    """A load of a basket as of a day before it took effect.

    Attributes:
        store: The tradingmachine.asset_baskets.basket_store.BasketStore to load from.
        name: The str name of the basket.
        as_of: The str day to load the basket as of.
    """

    def __init__(self):
        """Creates the store and the load to try.

        Raises:
            ValueError: The shared client is not configured.
        """
        self.store = basket_store.BasketStore()
        self.name = "NIFTY"
        self.as_of = "1990-01-01"

    def run(self) -> None:
        """Loads the basket and prints its history when it is not found.

        Returns:
            None.

        Raises:
            pymongo.errors.PyMongoError: MongoDB could not be reached.
        """
        try:
            basket = self.store.load(self.name, as_of=self.as_of)
        except exceptions.AssetBasketError as error:
            print(f"{type(error).__name__}: {error}")
            history = self.store.history(self.name)
            if history is None:
                print(f"No version of {self.name!r} is stored at all.")
            else:
                print(history.to_string(index=False))
            return
        print(f"Loaded {basket!r}")


if __name__ == "__main__":
    EarlyBasketLoad().run()
