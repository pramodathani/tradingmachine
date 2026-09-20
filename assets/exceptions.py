"""Errors raised by the instrument classes in `assets.instruments`, `assets.equities`, `assets.fixed_income`, `assets.commodities`, `assets.currencies` and `assets.funds`.

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


class HoldingError(InstrumentError):
    """A holding that cannot be changed as asked, or one that is not held at all."""


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


class FixedIncomeError(InstrumentError):
    """A bond UBI does not know, or one that is not in the fixed income segment."""


class FixedIncomeFuturesError(InstrumentError):
    """A bond futures contract UBI does not know, or one that is not in the fixed income futures segment."""


class FixedIncomeOptionError(InstrumentError):
    """A bond option UBI does not know, or one that is not in the fixed income options segment."""


class FixedIncomeIndexError(InstrumentError):
    """A fixed income index UBI does not know, or one that is not in the fixed income indices segment."""


class FixedIncomeIndexFuturesError(InstrumentError):
    """A fixed income index futures contract UBI does not know, or one that is not in the fixed income index futures segment."""


class FixedIncomeIndexOptionError(InstrumentError):
    """A fixed income index option UBI does not know, which is true of every one of them today, or one that is not in the fixed income index options segment."""


class CommodityError(InstrumentError):
    """A commodity UBI does not know, or one that is not in the commodities segment."""


class CommodityFuturesError(InstrumentError):
    """A commodity futures contract UBI does not know, or one that is not in the commodity futures segment."""


class CommodityOptionError(InstrumentError):
    """A commodity option UBI does not know, or one that is not in the commodity options segment."""


class CommodityIndexError(InstrumentError):
    """A commodity index UBI does not know, or one that is not in the commodity indices segment."""


class CommodityIndexFuturesError(InstrumentError):
    """A commodity index futures contract UBI does not know, or one that is not in the commodity index futures segment."""


class CommodityIndexOptionError(InstrumentError):
    """A commodity index option UBI does not know, or one that is not in the commodity index options segment."""


class CurrencyError(InstrumentError):
    """A currency pair UBI does not know, or one that is not in the currencies segment."""


class CurrencyFuturesError(InstrumentError):
    """A currency futures contract UBI does not know, or one that is not in the currency futures segment."""


class CurrencyOptionError(InstrumentError):
    """A currency option UBI does not know, or one that is not in the currency options segment."""


class CurrencyIndexError(InstrumentError):
    """A currency index UBI does not know, which is true of every one of them today, or one that is not in the currency indices segment."""


class CurrencyIndexFuturesError(InstrumentError):
    """A currency index futures contract UBI does not know, which is true of every one of them today, or one that is not in the currency index futures segment."""


class CurrencyIndexOptionError(InstrumentError):
    """A currency index option UBI does not know, which is true of every one of them today, or one that is not in the currency index options segment."""


class ExchangeTradedFundError(InstrumentError):
    """An exchange traded fund UBI does not know, or one that is not in the exchange traded funds segment."""


class InvestmentTrustError(InstrumentError):
    """An investment trust UBI does not know, or one that is not in the investment trusts segment."""
