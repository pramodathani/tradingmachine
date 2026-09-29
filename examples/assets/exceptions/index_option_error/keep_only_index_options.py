"""Keep only the index options among several options, catching InstrumentError.

The program builds an IndexOption at the middle strike of the soonest expiry of NIFTY, MCXBULLDEX and GOLDM options. The gold option raises IndexOptionError because gold is not an index, and one handler for the base class InstrumentError catches it along with any other instrument error.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/index_option_error/keep_only_index_options.py
"""

from tradingmachine.assets import commodities
from tradingmachine.assets import equities
from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments


class IndexOptionFilter:
    """A filter that keeps only options written on an index.

    Attributes:
        lookups: The list of (str exchange, str segment, str underlying symbol, datetime.date expiry, float strike) tuples to try.
    """

    def __init__(self):
        """Creates the filter with no lookups yet.

        Raises:
            Nothing.
        """
        self.lookups = []

    def add_middle_strike(
        self,
        family_class: type,
        exchange: str,
        segment: str,
        underlying_symbol: str,
    ) -> None:
        """Records a lookup at the middle strike of the soonest expiry of one underlying.

        Args:
            family_class: The option family class, such as equities.EquityIndexOption, whose discovery methods to read.
            exchange: The str exchange the options trade on.
            segment: The str UBI segment of the options.
            underlying_symbol: The str symbol the options are written on.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiry_date = family_class.expiries(exchange, underlying_symbol)[0]
        strike_prices = family_class.strikes(exchange, underlying_symbol, expiry_date)
        strike_price = strike_prices[len(strike_prices) // 2]
        self.lookups.append(
            (exchange, segment, underlying_symbol, expiry_date, strike_price)
        )

    def run(self) -> None:
        """Builds every lookup as an index option and prints which ones are kept.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        self.add_middle_strike(
            equities.EquityIndexOption,
            "nse",
            "equity_index_options",
            "NIFTY",
        )
        self.add_middle_strike(
            commodities.CommodityIndexOption,
            "mcx",
            "commodity_index_options",
            "MCXBULLDEX",
        )
        self.add_middle_strike(
            commodities.CommodityOption,
            "mcx",
            "commodity_options",
            "GOLDM",
        )
        for (
            exchange,
            segment,
            underlying_symbol,
            expiry_date,
            strike_price,
        ) in self.lookups:
            label = f"{underlying_symbol} {expiry_date} {strike_price} CE"
            try:
                option = instruments.IndexOption(
                    exchange=exchange,
                    segment=segment,
                    underlying_symbol=underlying_symbol,
                    expiry_date=expiry_date,
                    strike_price=strike_price,
                    option_type="CE",
                )
            except exceptions.InstrumentError as error:
                print(f"Dropped {label}: {type(error).__name__}: {error}")
                continue
            print(f"Kept {label}: lot size {option.lot_size}")


if __name__ == "__main__":
    IndexOptionFilter().run()
