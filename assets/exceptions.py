"""Errors raised by the instrument classes in `assets.instruments`.

These describe problems with an instrument itself, such as one UBI does not know or an index used as something tradeable. Failures of the request to UBI stay as the classes in `ubi_client.exceptions`, chained onto these where one caused the other.

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
