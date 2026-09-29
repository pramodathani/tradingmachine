"""Survey which kinds of instrument UBI can quote, catching UnifiedBrokerInterfaceError.

The program asks a share, a bond, a mutual fund scheme and a commodity for their last price. The share is quoted, while the other three raise ServiceUnavailableError because no broker that serves quotes carries them. One handler for the base class UnifiedBrokerInterfaceError catches each refusal, and the program prints a line per instrument.

Typical usage example:

  .venv/bin/python examples/unified_broker_interface/exceptions/service_unavailable_error/survey_quote_coverage.py
"""

from tradingmachine.assets import commodities
from tradingmachine.assets import equities
from tradingmachine.assets import fixed_income
from tradingmachine.assets import instruments
from tradingmachine.assets import mutual_funds
from tradingmachine.unified_broker_interface import exceptions


class QuoteCoverageSurvey:
    """A survey of which instruments UBI can give a last price for.

    Attributes:
        surveyed_instruments: The list of tradingmachine.assets.instruments.Instrument to ask.
    """

    def __init__(self):
        """Creates the survey with one instrument of each kind.

        Raises:
            tradingmachine.assets.exceptions.InstrumentError: UBI does not know one of the instruments.
            tradingmachine.unified_broker_interface.exceptions.UnifiedBrokerInterfaceError: UBI could not be reached or refused a lookup.
        """
        self.surveyed_instruments = [
            equities.Equity(exchange="nse", symbol="IDEA"),
            fixed_income.FixedIncome(exchange="nse", symbol="IN000126C010"),
            mutual_funds.MutualFund(exchange="nse", symbol="ABSLFTTIDG"),
            commodities.Commodity(exchange="mcx", symbol="GOLD"),
        ]

    def describe(self, instrument: instruments.Instrument) -> str:
        """Asks one instrument for its last price and describes the answer.

        Args:
            instrument: The tradingmachine.assets.instruments.Instrument to ask.

        Returns:
            A str line with the last price, or the reason there is none.

        Raises:
            Nothing.
        """
        label = f"{type(instrument).__name__} {instrument.symbol}"
        try:
            last_price = instrument.last_price
        except exceptions.UnifiedBrokerInterfaceError as error:
            return f"{label}: no quote, {type(error).__name__} ({error.status_code})"
        return f"{label}: {last_price}"

    def run(self) -> None:
        """Asks every instrument and prints one line for each.

        Returns:
            None.

        Raises:
            Nothing.
        """
        for instrument in self.surveyed_instruments:
            print(self.describe(instrument))


if __name__ == "__main__":
    QuoteCoverageSurvey().run()
