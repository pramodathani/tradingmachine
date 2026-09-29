"""Ask the Option base class for an option chain, catch InstrumentError and use a family class instead.

The option discovery class methods read the segment a family class such as EquityIndexOption names. Called on the Option base class, which names none, `chain` raises OptionError. The program catches it through its base class InstrumentError, reads the chain through EquityIndexOption instead, and prints the strikes around the middle of it.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/option_error/read_a_chain_through_a_family_class.py
"""

import datetime

import pandas as pd

from tradingmachine.assets import equities
from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments


class OptionChainReader:
    """A reader of the NIFTY option chain for the soonest expiry.

    Attributes:
        exchange: The str exchange the options trade on.
        underlying_symbol: The str symbol of the index.
    """

    def __init__(self):
        """Creates the reader for NIFTY options.

        Raises:
            Nothing.
        """
        self.exchange = "nse"
        self.underlying_symbol = "NIFTY"

    def read_chain(self, expiry_date: datetime.date) -> pd.DataFrame | None:
        """Reads the chain through the Option base class, falling back to EquityIndexOption.

        Args:
            expiry_date: The datetime.date whose chain to read.

        Returns:
            A pandas.DataFrame of the chain, or None when nothing is listed.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused the request.
        """
        try:
            return instruments.Option.chain(
                exchange=self.exchange,
                underlying_symbol=self.underlying_symbol,
                expiry_date=expiry_date,
            )
        except exceptions.InstrumentError as error:
            print(f"{type(error).__name__}: {error}")
        return equities.EquityIndexOption.chain(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
            expiry_date=expiry_date,
        )

    def run(self) -> None:
        """Reads the soonest chain and prints six rows from its middle.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        expiry_date = equities.EquityIndexOption.expiries(
            exchange=self.exchange,
            underlying_symbol=self.underlying_symbol,
        )[0]
        chain = self.read_chain(expiry_date)
        if chain is None:
            print(f"No {self.underlying_symbol} option expires on {expiry_date}.")
            return
        middle = len(chain) // 2
        columns = [
            "strike_price",
            "option_type",
            "instrument_id",
        ]
        print(f"{len(chain)} options expire on {expiry_date}; six from the middle:")
        print(chain.iloc[middle - 3 : middle + 3][columns].to_string(index=False))


if __name__ == "__main__":
    OptionChainReader().run()
