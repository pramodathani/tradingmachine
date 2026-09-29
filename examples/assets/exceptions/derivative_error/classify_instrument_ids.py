"""Tell which of several instrument ids are contracts, catching InstrumentError.

The program collects the UBI ids of a share, a futures contract and an option, then builds a Derivative from each id. The share raises DerivativeError, which one handler for the base class InstrumentError catches, and the two contracts print their expiry dates.

Typical usage example:

  .venv/bin/python examples/assets/exceptions/derivative_error/classify_instrument_ids.py
"""

from tradingmachine.assets import equities
from tradingmachine.assets import exceptions
from tradingmachine.assets import instruments


class InstrumentIdClassifier:
    """A classifier of UBI instrument ids into contracts and other instruments.

    Attributes:
        instrument_ids: The dict of str label to str UBI instrument id to classify.
    """

    def __init__(self):
        """Creates the classifier with no ids yet.

        Raises:
            Nothing.
        """
        self.instrument_ids = {}

    def collect_instrument_ids(self) -> None:
        """Reads the ids of one share, the nearest NIFTY future and one NIFTY option from UBI.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        share = equities.Equity(exchange="nse", symbol="IDEA")
        self.instrument_ids["IDEA share"] = share.instrument_id
        futures_frame = equities.EquityIndexFutures.contracts(
            exchange="nse",
            underlying_symbol="NIFTY",
        )
        self.instrument_ids["NIFTY future"] = futures_frame.iloc[0]["instrument_id"]
        expiry_date = equities.EquityIndexOption.expiries(
            exchange="nse",
            underlying_symbol="NIFTY",
        )[0]
        chain = equities.EquityIndexOption.chain(
            exchange="nse",
            underlying_symbol="NIFTY",
            expiry_date=expiry_date,
        )
        middle_row = chain.iloc[len(chain) // 2]
        self.instrument_ids["NIFTY option"] = middle_row["instrument_id"]

    def run(self) -> None:
        """Builds a Derivative from every id and prints whether it is a contract.

        Returns:
            None.

        Raises:
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a request.
        """
        self.collect_instrument_ids()
        for label, instrument_id in self.instrument_ids.items():
            try:
                contract = instruments.Derivative(instrument_id=instrument_id)
            except exceptions.InstrumentError as error:
                print(f"{label}: not a contract ({type(error).__name__}: {error})")
                continue
            print(
                f"{label}: a contract of shape {contract.shape}, expiring {contract.expiry_date}"
            )


if __name__ == "__main__":
    InstrumentIdClassifier().run()
