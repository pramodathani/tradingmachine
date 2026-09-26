"""Read-only market data from UBI, looked up by instrument id.

`tradingmachine.assets.instruments.Instrument` reads UBI's details for an instrument when it is built, which is right for working with a few instruments. An application that shows thousands of instruments, and already knows their ids from UBI's instrument master, needs the same data without building an object per instrument. `InstrumentCatalogue` offers it: each method takes an instrument id and returns UBI's answer as it came, and nothing is read until a method is called.

Typical usage example:

  catalogue = InstrumentCatalogue(unified_broker_interface)
  print(catalogue.mapping_date)
  document = catalogue.prices_document(instrument_id, interval="day", days=365)
  with catalogue.open_master() as stream:
      for batch in stream.batches():
          ...
"""

import datetime

from tradingmachine.ubi_client import client
from tradingmachine.ubi_client import instrument_master_stream
from tradingmachine.ubi_client import prices_document

SEGMENTS_PATH = "/api/instruments/segments"

MASTER_PATH = "/api/instruments/master"

DETAILS_PATH = "/api/instruments/details"

ADDITIONAL_DETAILS_PATH = "/api/instruments/additional_details"

QUOTE_PATH = "/api/instruments/quote"

PRICES_PATH = "/api/instruments/prices"


class InstrumentCatalogue:
    """UBI's instrument data, read through one client.

    Attributes:
        unified_broker_interface: The client.UnifiedBrokerInterface every request goes through.
    """

    def __init__(self, unified_broker_interface: client.UnifiedBrokerInterface):
        """Initialises the catalogue over a client.

        Args:
            unified_broker_interface: The client.UnifiedBrokerInterface to send requests through.

        Raises:
            Nothing.
        """
        self.unified_broker_interface = unified_broker_interface

    @property
    def greeting(self) -> dict:
        """UBI's welcome message as a dict, read without an access token, which shows whether UBI is running."""
        return self.unified_broker_interface.greeting

    @property
    def segments(self) -> dict:
        """UBI's list of segments as a dict with `mapping_date`, `exchanges` and `segments`, read from UBI on every access."""
        return self.unified_broker_interface.get(SEGMENTS_PATH)

    @property
    def mapping_date(self) -> str | None:
        """The str date of UBI's current instrument catalogue, such as `2026-09-26`, or None when UBI does not report one; read on every access."""
        answer = self.segments
        if not isinstance(answer, dict):
            return None
        return answer.get("mapping_date")

    def details(self, instrument_id: str) -> dict:
        """Reads an instrument's identity, seen dates, lot size, tick size and the brokers that carry it.

        Args:
            instrument_id: The str UBI instrument id.

        Returns:
            The dict UBI returns from `/api/instruments/details`.

        Raises:
            NotFoundError: UBI has no instrument with that id.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.unified_broker_interface.get(
            DETAILS_PATH,
            params={
                "instrument_id": instrument_id,
            },
        )

    def additional_details(self, instrument_id: str) -> dict:
        """Reads the extra attributes each broker publishes about an instrument, such as its ISIN and display name.

        Args:
            instrument_id: The str UBI instrument id.

        Returns:
            The dict UBI returns from `/api/instruments/additional_details`, with `attribute_names` and one `carried_by` entry per broker.

        Raises:
            NotFoundError: UBI has no instrument with that id.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.unified_broker_interface.get(
            ADDITIONAL_DETAILS_PATH,
            params={
                "instrument_id": instrument_id,
            },
        )

    def quote(self, instrument_id: str) -> dict:
        """Reads an instrument's full unified quote with market depth.

        Args:
            instrument_id: The str UBI instrument id.

        Returns:
            The dict UBI returns from `/api/instruments/quote`, including `source`.

        Raises:
            NotFoundError: UBI has no instrument with that id.
            ServiceUnavailableError: UBI has no recent quote and no broker could supply one.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        return self.unified_broker_interface.get(
            QUOTE_PATH,
            params={
                "instrument_id": instrument_id,
            },
        )

    def prices_document(
        self,
        instrument_id: str,
        interval: str = "day",
        from_date: datetime.date | str | None = None,
        to_date: datetime.date | str | None = None,
        days: int | None = None,
        adjusted: bool = True,
    ) -> prices_document.PricesDocument:
        """Reads an instrument's candles for a range, with UBI's facts about them.

        Give either from_date and to_date, or days.

        Args:
            instrument_id: The str UBI instrument id.
            interval: The str candle interval, such as `day` or `5minute`.
            from_date: The first day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            to_date: The last day of the range as a datetime.date or a `YYYY-MM-DD` str, or None when days is given.
            days: The int number of days to count back from today, or None when from_date and to_date are given.
            adjusted: A bool that is True for prices adjusted for splits and bonuses.

        Returns:
            The prices_document.PricesDocument holding UBI's answer.

        Raises:
            BadRequestError: The range or interval is invalid, such as both days and from_date given.
            NotFoundError: UBI has no instrument with that id.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        parameters = {
            "instrument_id": instrument_id,
            "interval": interval,
        }
        if adjusted:
            parameters["adjusted"] = "true"
        else:
            parameters["adjusted"] = "false"
        if from_date is not None:
            parameters["from"] = from_date
        if to_date is not None:
            parameters["to"] = to_date
        if days is not None:
            parameters["days"] = days
        answer = self.unified_broker_interface.get(PRICES_PATH, params=parameters)
        if not isinstance(answer, dict):
            answer = {}
        return prices_document.PricesDocument(answer)

    def open_master(
        self,
        exchange: str = "all",
        segment: str = "all",
    ) -> instrument_master_stream.InstrumentMasterStream:
        """Opens UBI's instrument master for reading in batches.

        Args:
            exchange: The str exchange to list, such as `nse`, or `all`.
            segment: The str segment to list, such as `nse_equities`, or `all`; with exchange `all` only `all` and `uncategorised` are accepted.

        Returns:
            The open instrument_master_stream.InstrumentMasterStream, which the caller must close.

        Raises:
            BadRequestError: UBI refused the exchange or segment.
            IncompleteResponseError: UBI's answer has no mapping date.
            UnifiedBrokerInterfaceError: Any other failure reported by, or on the way to, UBI.
        """
        response = self.unified_broker_interface.stream_get(
            MASTER_PATH,
            params={
                "exchange": exchange,
                "segment": segment,
            },
        )
        return instrument_master_stream.InstrumentMasterStream(response)
