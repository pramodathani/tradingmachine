"""Errors raised by the asset basket classes.

Every error here is an `AssetBasketError`, so a caller can catch the whole family or one specific failure. Failures reported by UBI itself still arrive as the client's own `UnifiedBrokerInterfaceError` classes.

Typical usage example:

  try:
      basket = basket_store.BasketStore().load("NIFTY")
  except exceptions.BasketNotFoundError as error:
      print(error)
"""


class AssetBasketError(Exception):
    """A failure in building, reading, storing or trading an asset basket."""


class BasketNotFoundError(AssetBasketError):
    """No stored basket has the requested name, or none is in effect on the requested date."""


class BasketMemberError(AssetBasketError):
    """A basket's members are unusable, such as an instrument UBI cannot find, an instrument named twice, or weights given for only some members."""


class BasketCsvImportError(AssetBasketError):
    """A CSV file could not be turned into a basket, such as one without a `symbol` column."""
