"""Show what a commodity row in UBI is, and why it has no price of its own.

A commodity such as GOLD on the mcx is the exchange's reference record for an underlying rather than something that trades. The program builds it, prints its identity and the brokers that map it, and then shows that it has no quote and no candles, catching the ServiceUnavailableError the quote raises.

Typical usage example:

  .venv/bin/python examples/assets/commodities/commodity/underlying_records.py
"""

from tradingmachine.assets import commodities
from tradingmachine.unified_broker_interface import exceptions


class CommodityRecordReport:
    """A report on one commodity's reference record.

    Attributes:
        commodity: The tradingmachine.assets.commodities.Commodity the report describes.
    """

    def __init__(self, exchange: str = "mcx", symbol: str = "GOLD"):
        """Looks the commodity up in UBI.

        Args:
            exchange: The str exchange that publishes the commodity, `mcx`, `ncdex` or `nse`.
            symbol: The str symbol of the commodity, such as `GOLD`.

        Raises:
            tradingmachine.assets.exceptions.CommodityError: UBI has no such commodity.
        """
        self.commodity = commodities.Commodity(exchange=exchange, symbol=symbol)

    def run(self) -> None:
        """Prints the record and shows the missing quote and candles.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        commodity = self.commodity
        print(f"{commodity.symbol} on the {commodity.exchange}")
        print(f"Segment: {commodity.segment}, shape: {commodity.shape}")
        print(f"Instrument id: {commodity.instrument_id}")
        for mapping in commodity.carried_by:
            print(f"Mapped by {mapping['broker']} as {mapping['broker_token']}")
        try:
            print(f"Last price: {commodity.last_price}")
        except exceptions.ServiceUnavailableError as error:
            print(f"No quote: {error}")
        print(f"Candles for the last month: {commodity.prices(days=30)}")
        print("Trade it through CommodityFutures or CommodityOption instead.")


if __name__ == "__main__":
    CommodityRecordReport().run()
