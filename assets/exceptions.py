"""Errors raised by the instrument classes in `assets.instruments` and `assets.equities`.

These describe problems with an instrument itself, such as one UBI does not know, an index used as something tradeable, or an order asked for at a price the order book cannot supply. Failures of the request to UBI stay as the classes in `ubi_client.exceptions`, chained onto these where one caused the other.

Typical usage example:

  try:
      infosys = instruments.TradeableInstrument(exchange="nse", segment="equities", symbol="INFY")
  except exceptions.InstrumentError as error:
      print(error)
"""


class InstrumentError(Exception):
    """An instrument UBI does not know, or one that cannot be used as asked."""


class TradeableInstrumentError(InstrumentError):
    """An instrument asked for as tradeable that cannot be traded, such as an index."""


class NonTradeableInstrumentError(InstrumentError):
    """An instrument asked for as non-tradeable that can in fact be traded."""


class OrderError(InstrumentError):
    """An order that cannot be priced, because the value it asks for is not there."""


class PositionError(InstrumentError):
    """A position that cannot be changed as asked, or one that is not held at all."""


class EquityError(InstrumentError):
    """An equity share UBI does not know, or one that is not in the equities segment."""


class EquityFuturesError(InstrumentError):
    """An equity futures contract UBI does not know, or one that is not in the equity futures segment."""


class EquityOptionError(InstrumentError):
    """An equity option UBI does not know, or one that is not in the equity options segment."""


class EquityIndexError(InstrumentError):
    """An equity index UBI does not know, or one that is not in the equity indices segment."""


class EquityIndexFuturesError(InstrumentError):
    """An equity index futures contract UBI does not know, or one that is not in the equity index futures segment."""


class EquityIndexOptionError(InstrumentError):
    """An equity index option UBI does not know, or one that is not in the equity index options segment."""
